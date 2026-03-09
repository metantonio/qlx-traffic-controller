from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # App Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM Settings
    DEFAULT_PROVIDER: str = "ollama"
    DEFAULT_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # Services
    TELEGRAM_BOT_TOKEN: str = ""
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    ENCRYPTION_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), 
        env_file_encoding="utf-8"
    )

settings = Settings()
