"""GPU training script intended for Google Colab, not CPU-only Windows."""
import argparse
import json
import os
import hashlib
from pathlib import Path


def file_sha256(path):
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open('rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def validate_training_config(config):
    cfg = dict(config)
    cfg.setdefault('model', 'unsloth/Llama-3.2-3B-Instruct')
    cfg.setdefault('epochs', 3)
    cfg.setdefault('max_seq_length', 2048)
    cfg.setdefault('batch_size', 2)
    cfg.setdefault('gradient_accumulation_steps', 4)
    cfg.setdefault('learning_rate', 2e-4)
    cfg.setdefault('warmup_steps', 10)
    cfg.setdefault('seed', 3407)
    cfg.setdefault('smoke_test', False)

    if cfg['batch_size'] <= 0:
        raise ValueError('batch_size must be > 0')
    if cfg['gradient_accumulation_steps'] <= 0:
        raise ValueError('gradient_accumulation_steps must be > 0')
    if cfg['learning_rate'] <= 0:
        raise ValueError('learning_rate must be > 0')
    if cfg['max_seq_length'] < 256:
        raise ValueError('max_seq_length must be at least 256')
    if cfg.get('max_steps') is not None and cfg['max_steps'] <= 0:
        raise ValueError('max_steps must be > 0')
    if cfg['warmup_steps'] < 0:
        raise ValueError('warmup_steps must be >= 0')
    return cfg


def _require_training_dependencies():
    try:
        from datasets import load_dataset
        from trl import SFTConfig, SFTTrainer
        try:
            from unsloth import FastLanguageModel
        except ImportError as exc:
            raise RuntimeError(
                'Training dependencies are missing. Install the Colab GPU stack: '
                'pip install -U unsloth datasets trl peft transformers accelerate bitsandbytes'
            ) from exc
        return load_dataset, FastLanguageModel, SFTConfig, SFTTrainer
    except ImportError as exc:
        raise RuntimeError(
            'Training dependencies are missing. Install the Colab GPU stack: '
            'pip install -U unsloth datasets trl peft transformers accelerate bitsandbytes'
        ) from exc


def _load_dataset_files(train_path, validation_path):
    load_dataset, _, _, _ = _require_training_dependencies()
    ds = load_dataset('json', data_files={'train': train_path, 'validation': validation_path})
    for split in ('train', 'validation'):
        if 'messages' not in ds[split].column_names:
            raise ValueError(f'{split} file must contain a messages array in each row; run prepare_dataset.py first')
    return ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', required=True)
    ap.add_argument('--validation', required=True)
    ap.add_argument('--output', default='/content/mockmate-llama-adapter')
    ap.add_argument('--gguf-output', default='/content/mockmate-llama-gguf')
    ap.add_argument('--model', default='unsloth/Llama-3.2-3B-Instruct')
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--max-steps', type=int, default=None)
    ap.add_argument('--max-seq-length', type=int, default=2048)
    ap.add_argument('--batch-size', type=int, default=2)
    ap.add_argument('--grad-accum', type=int, default=4)
    ap.add_argument('--learning-rate', type=float, default=2e-4)
    ap.add_argument('--warmup-steps', type=int, default=10)
    ap.add_argument('--seed', type=int, default=3407)
    ap.add_argument('--eval-steps', type=int, default=50)
    ap.add_argument('--save-steps', type=int, default=50)
    ap.add_argument('--resume-from-checkpoint', default=None)
    ap.add_argument('--smoke-test', action='store_true')
    a = ap.parse_args()

    config = validate_training_config({
        'model': a.model,
        'epochs': a.epochs,
        'max_steps': a.max_steps,
        'max_seq_length': a.max_seq_length,
        'batch_size': a.batch_size,
        'gradient_accumulation_steps': a.grad_accum,
        'learning_rate': a.learning_rate,
        'warmup_steps': a.warmup_steps,
        'seed': a.seed,
        'smoke_test': a.smoke_test,
    })

    try:
        load_dataset, FastLanguageModel, SFTConfig, SFTTrainer = _require_training_dependencies()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    ds = _load_dataset_files(a.train, a.validation)
    train_count = len(ds['train'])
    val_count = len(ds['validation'])

    train_sha = file_sha256(a.train)
    val_sha = file_sha256(a.validation)

    effective_batch = config['batch_size'] * config['gradient_accumulation_steps']
    steps_per_epoch = max(1, train_count // effective_batch)

    if config['smoke_test']:
        total_steps = 15
        print("[SMOKE TEST MODE] Running 15 steps smoke test.")
    elif config['max_steps'] is not None:
        total_steps = config['max_steps']
    else:
        total_steps = steps_per_epoch * config['epochs']

    if total_steps < steps_per_epoch and not config['smoke_test']:
        print(f"\n[WARNING] total_steps ({total_steps}) is LESS than 1 full epoch ({steps_per_epoch} steps)!")
        print("          Recommended training duration is at least 3 full epochs for good fine-tuning quality.\n")

    print(f"Dataset Size: {train_count} train rows | {val_count} val rows")
    print(f"Training for {total_steps} total steps (~{total_steps / steps_per_epoch:.2f} epochs)")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config['model'],
        max_seq_length=config['max_seq_length'],
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
        lora_alpha=16,
        lora_dropout=0,
        bias='none',
        use_gradient_checkpointing='unsloth',
        random_state=config['seed'],
        use_rslora=False,
    )

    cfg = SFTConfig(
        output_dir=a.output,
        per_device_train_batch_size=config['batch_size'],
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=config['gradient_accumulation_steps'],
        warmup_steps=config['warmup_steps'],
        max_steps=total_steps,
        learning_rate=config['learning_rate'],
        logging_steps=max(1, min(10, total_steps)),
        optim='adamw_8bit',
        weight_decay=0.01,
        lr_scheduler_type='linear',
        seed=config['seed'],
        report_to='none',
        max_length=config['max_seq_length'],
        packing=False,
        eval_strategy='steps',
        eval_steps=max(1, min(a.eval_steps, total_steps)),
        save_strategy='steps',
        save_steps=max(1, min(a.save_steps, total_steps)),
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds['train'],
        eval_dataset=ds['validation'],
        args=cfg,
    )

    train_res = trainer.train(resume_from_checkpoint=a.resume_from_checkpoint)

    # Save adapter
    os.makedirs(a.output, exist_ok=True)
    model.save_pretrained(a.output)
    tokenizer.save_pretrained(a.output)
    print('Adapter saved to', a.output)

    # Export GGUF Q4_K_M
    os.makedirs(a.gguf_output, exist_ok=True)
    gguf_filename = "mockmate-llama-q4_k_m.gguf"
    gguf_path = os.path.join(a.gguf_output, gguf_filename)
    
    model.save_pretrained_gguf(a.gguf_output, tokenizer, quantization_method='q4_k_m')
    print('GGUF export saved to', a.gguf_output)

    gguf_sha = file_sha256(gguf_path)

    # Loss history
    log_history = trainer.state.log_history
    train_losses = [x['loss'] for x in log_history if 'loss' in x]
    eval_losses = [x['eval_loss'] for x in log_history if 'eval_loss' in x]

    train_run = {
        "config": config,
        "total_steps": total_steps,
        "epochs_trained": round(total_steps / steps_per_epoch, 2),
        "dataset": {
            "train_rows": train_count,
            "validation_rows": val_count,
            "train_sha256": train_sha,
            "validation_sha256": val_sha,
        },
        "loss_history": {
            "final_train_loss": train_losses[-1] if train_losses else None,
            "final_eval_loss": eval_losses[-1] if eval_losses else None,
            "all_train_losses": train_losses,
            "all_eval_losses": eval_losses,
        },
        "gguf": {
            "filename": gguf_filename,
            "path": gguf_path,
            "sha256": gguf_sha,
        }
    }

    train_run_path = os.path.join(a.output, "train_run.json")
    with open(train_run_path, 'w', encoding='utf-8') as f:
        json.dump(train_run, f, indent=2)

    print("\n=======================================================")
    print(" TRAINING COMPLETE & ARTIFACTS PACKAGED")
    print("=======================================================")
    print(f"GGUF Filename: {gguf_filename}")
    print(f"GGUF SHA256  : {gguf_sha}")
    print(f"Train Run JSON: {train_run_path}")
    print("\nTo register the fine-tuned model in Ollama locally, run:")
    print("  ollama create mockmate-llama-ft -f Modelfile")
    print("=======================================================\n")


if __name__ == '__main__':
    main()
