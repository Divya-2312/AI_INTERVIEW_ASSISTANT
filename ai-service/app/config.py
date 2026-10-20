import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    PORT: int = int(os.getenv("AI_SERVICE_PORT", 8000))
    BASE_MODEL_NAME: str = os.getenv("BASE_MODEL_NAME", "llama3.2:3b")
    BASE_MODEL_OLLAMA_NAME: str = os.getenv("BASE_MODEL_OLLAMA_NAME", "llama3.2:3b")
    FINE_TUNED_MODEL_NAME: str = os.getenv("FINE_TUNED_MODEL_NAME", "mockmate-llama-ft").strip()
    # Default model for all tasks is the base model (llama3.2:3b)
    MODEL_NAME: str = os.getenv("MODEL_NAME", os.getenv("BASE_MODEL_OLLAMA_NAME", "llama3.2:3b")).strip()
    FINE_TUNED_ADAPTER_PATH: str = os.getenv("FINE_TUNED_ADAPTER_PATH", "./models/mockmate-llama-adapter")
    GGUF_MODEL_PATH: str = os.getenv("GGUF_MODEL_PATH", "./models/mockmate-llama-gguf")
    MODEL_ENDPOINT: str = os.getenv("MODEL_ENDPOINT", "http://localhost:11434/api/generate")
    RAG_DATA_PATH: str = os.getenv("RAG_DATA_PATH", "./knowledge")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    FOLLOW_UP_PERCENTAGE: int = int(os.getenv("FOLLOW_UP_PERCENTAGE", 25))
    MAX_FOLLOW_UPS: int = int(os.getenv("MAX_FOLLOW_UPS", 3))

    USE_FT_HR: bool = _env_bool("USE_FT_HR", True)
    USE_FT_COMPLEXITY: bool = _env_bool("USE_FT_COMPLEXITY", True)

    EXPECTED_GGUF_FILENAME: str = os.getenv("EXPECTED_GGUF_FILENAME", "mockmate-llama-q4_k_m.gguf")
    EXPECTED_MODEL_SHA256: str = os.getenv("EXPECTED_MODEL_SHA256", "")

    STRICT_AI_MODE: bool = _env_bool("STRICT_AI_MODE", False)

    @classmethod
    def get_model_status(cls):
        return {
            "configured_model": cls.MODEL_NAME,
            "base_model": cls.BASE_MODEL_NAME,
            "base_model_ollama_name": cls.BASE_MODEL_OLLAMA_NAME,
            "fine_tuned_model": cls.FINE_TUNED_MODEL_NAME,
            "use_ft_hr": cls.USE_FT_HR,
            "use_ft_complexity": cls.USE_FT_COMPLEXITY,
            "adapter_path": cls.FINE_TUNED_ADAPTER_PATH,
            "gguf_model_path": cls.GGUF_MODEL_PATH,
            "expected_gguf_filename": cls.EXPECTED_GGUF_FILENAME,
            "strict_ai_mode": cls.STRICT_AI_MODE,
        }


settings = Settings()
