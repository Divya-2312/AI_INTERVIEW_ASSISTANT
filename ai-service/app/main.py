from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routes.question_routes import router as question_router
from app.routes.evaluation_routes import router as evaluation_router
from app.config import settings

app = FastAPI(
    title="AI Interview Assistant - AI Engine Service",
    description="FastAPI AI microservice powering question generation, RAG context (BERT-derived sentence embeddings), and answer evaluation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CLIENT_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(question_router)
app.include_router(evaluation_router)

@app.get("/health")
def health_check():
    """
    Visible AI status panel. Check this before a demo/viva to confirm
    LLaMA and BERT are actually active rather than silently falling back.
    """
    from app.services.embedding_service import embedding_service
    from app.services.rag_service import rag_service
    from app.models.llama_provider import LlamaModel

    embedding_ok = embedding_service.using_bert
    llama_status = LlamaModel().check_connection()
    model_status = settings.get_model_status()

    is_verified = llama_status.get("is_fine_tuned_verified", False)
    base_used = llama_status.get("base_model_used_for_inference", False)
    reason = llama_status.get("verification_reason", "")

    all_active = embedding_ok and llama_status.get("status") == "connected" and is_verified

    model_identity = {
        "configured_model": settings.MODEL_NAME,
        "inference_model": settings.MODEL_NAME,
        "base_model": settings.BASE_MODEL_NAME,
        "base_model_ollama_name": settings.BASE_MODEL_OLLAMA_NAME,
        "fine_tuned_model": settings.FINE_TUNED_MODEL_NAME,
        "adapter_path": settings.FINE_TUNED_ADAPTER_PATH,
        "gguf_model_path": settings.GGUF_MODEL_PATH,
        "is_fine_tuned_verified": is_verified,
        "base_model_used_for_inference": base_used,
        "verification_reason": reason,
        "strict_ai_mode": True,
    }

    from app.services.code_executor import is_java_available
    java_runtime_available = is_java_available()

    return {
        "success": True,
        "message": "AI Interview Assistant AI service is running",
        "service": "FastAPI AI Engine",
        "port": settings.PORT,
        "strict_ai_mode": True,
        "javaRuntime": java_runtime_available,
        "is_fine_tuned_verified": is_verified,
        "base_model_used_for_inference": base_used,
        "model_identity": model_identity,
        "model_status": model_identity,
        "ai_status": {
            "embedding_engine": {
                "model": settings.EMBEDDING_MODEL,
                "type": "BERT-derived Sentence Transformer" if embedding_ok else "bag-of-words fallback (NOT semantic)",
                "active": embedding_ok,
            },
            "llama": {
                "model": settings.MODEL_NAME,
                "endpoint": settings.MODEL_ENDPOINT,
                "configured_model": settings.MODEL_NAME,
                "fine_tuned_model": settings.FINE_TUNED_MODEL_NAME,
                "is_fine_tuned_verified": is_verified,
                "base_model_used_for_inference": base_used,
                "verification_reason": reason,
                **llama_status,
            },
            "rag": {
                "active": len(rag_service.chunks) > 0,
                "chunks_loaded": len(rag_service.chunks),
                "semantic_retrieval": embedding_ok,
            },
        },
        "demo_ready": all_active,
        "note": "demo_ready=true requires verified distinct fine-tuned model AND active BERT embeddings.",
    }
if __name__ == "__main__":
    import uvicorn
    # reload=True (uvicorn's file-watcher) restarts the ENTIRE process --
    # dropping every in-flight request/socket -- on ANY file write under the
    # working directory. That includes Python's own __pycache__ bytecode
    # files, which get written the first time a module is imported: the
    # embedding model is loaded lazily on the first answer evaluation, so
    # "generate Q1 -> answer Q1 (first-ever embedding call writes .pyc) ->
    # generate Q2" is a textbook trigger -- the watcher sees the new
    # __pycache__ file mid-session and restarts the server right as Q2's
    # request is in flight, which looks exactly like "LLaMA disconnected".
    # Only enable this while actively editing code with no interview
    # running; never during a real/demo session.
    reload_enabled = os.getenv("AI_SERVICE_RELOAD", "false").lower() == "true"
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=reload_enabled)
