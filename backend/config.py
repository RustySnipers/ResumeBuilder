import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application Settings."""
    
    # LLM Settings
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-opus-20240229"

    # Local LLM Settings
    LOCAL_LLM_ENABLED: bool = False
    LOCAL_LLM_PATH: Optional[str] = None
    LOCAL_LLM_REPO_ID: str = "TheBloke/Llama-2-7B-Chat-GGUF"
    LOCAL_LLM_FILENAME: str = "llama-2-7b-chat.Q4_K_M.gguf"
    LOCAL_LLM_CONTEXT_SIZE: int = 2048
    LOCAL_LLM_GPU_LAYERS: int = 0
    
    class Config:
        env_file = ".env"
        extra = "ignore" 

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def is_lite_mode() -> bool:
    """Return True when Lite Mode is enabled via the ``LITE_MODE`` flag."""
    value = os.getenv("LITE_MODE", "false")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
