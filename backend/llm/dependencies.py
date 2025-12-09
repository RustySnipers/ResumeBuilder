"""
LLM Dependencies.

Provides singleton access to LocalLLMClient to prevent reloading model on every request.
"""
from typing import Optional
from functools import lru_cache
from backend.config import get_settings
from backend.llm.local_llm_client import LocalLLMClient

# Global singleton
_llm_client_instance: Optional[LocalLLMClient] = None

def get_llm_client() -> LocalLLMClient:
    """
    Get or create the singleton LocalLLMClient.
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        settings = get_settings()
        _llm_client_instance = LocalLLMClient(settings)
    return _llm_client_instance
