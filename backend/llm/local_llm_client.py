"""
Local LLM Client using llama-cpp-python.

This client provides an interface for text generation and chat using local GGUF models.
It handles automatic downloading of models from HuggingFace if not present.
"""

import os
import logging
from typing import List, Dict, Optional, Generator, Any
from pathlib import Path

try:
    from llama_cpp import Llama
    from huggingface_hub import hf_hub_download
except ImportError:
    Llama = None
    hf_hub_download = None

from backend.config import Settings

logger = logging.getLogger(__name__)

# Default model settings (can be overridden by env vars)
DEFAULT_REPO_ID = "bartowski/Llama-3.2-3B-Instruct-GGUF"
DEFAULT_FILENAME = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
# A smaller fallback model if hardware is very constrained, or a better one if available
# For now, we use a standard quantization of a popular chat model.

class LocalLLMClient:
    """Client for running local LLMs via llama-cpp-python."""

    def __init__(self, settings: Settings):
        """
        Initialize the Local LLM client.
        
        Args:
            settings: Application settings
        """
        if Llama is None:
            logger.warning("llama-cpp-python not installed. Local LLM features disabled.")
            self.model = None
            return

        self.model_path = self._get_model_path(settings)
        self.context_size = int(os.getenv("LOCAL_LLM_CONTEXT_SIZE", "2048"))
        self.n_gpu_layers = int(os.getenv("LOCAL_LLM_GPU_LAYERS", "0")) # Default to 0 (CPU)
        
        self.model = None
        self._load_model()

    def _get_model_path(self, settings: Settings) -> str:
        """Get the path to the model file, downloading if necessary."""
        
        # Check if specific path provided in env
        custom_path = os.getenv("LOCAL_LLM_PATH")
        if custom_path and os.path.exists(custom_path):
            return custom_path

        # Use HuggingFace Hub to manage/download model
        # We store models in a centralized cache directory
        cache_dir = os.path.join(str(Path.home()), ".cache", "resume-builder", "models")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Optimize: Check if file exists locally to avoid HF Hub checks (slow/hanging)
        repo_id = os.getenv("LOCAL_LLM_REPO_ID", DEFAULT_REPO_ID)
        filename = os.getenv("LOCAL_LLM_FILENAME", DEFAULT_FILENAME)
        local_file_path = os.path.join(cache_dir, filename)
        
        if os.path.exists(local_file_path):
            logger.info(f"Refusing to download. Using existing local model: {local_file_path}")
            return local_file_path
        
        try:
            logger.info(f"Checking for local model: {repo_id}/{filename}...")
            model_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=cache_dir,
                local_dir=cache_dir, # Force local dir to make finding it easier? Or just let HF handle it
                local_dir_use_symlinks=False 
            )
            logger.info(f"Model found/downloaded at: {model_path}")
            return model_path
        except Exception as e:
            logger.error(f"Failed to download/locate model: {e}")
            raise

    def _load_model(self):
        """Load the model into memory."""
        if not self.model_path:
            return

        try:
            logger.info(f"Loading Local LLM from {self.model_path}...")
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,
                n_gpu_layers=self.n_gpu_layers,
                verbose=True
            )
            logger.info("Local LLM loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Local LLM: {e}")
            self.model = None

    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: Input text
            max_tokens: Max tokens to generate
            temperature: Creativity (0.0 - 1.0)
            
        Returns:
            Generated text string
        """
        if not self.model:
            return "Error: Local LLM not loaded."

        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["User:", "\n\n"], # Basic stop sequences
                echo=False
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"Error generating text: {str(e)}"

    async def chat_stream(self, messages: List[Dict[str, str]], max_tokens: int = 1000, temperature: float = 0.7) -> Generator[str, None, None]:
        """
        Stream chat completion (OpenAI compatible format).
        
        Yields:
            Token strings
        """
        if not self.model:
            yield "Error: Local LLM not loaded."
            return

        try:
            # Create streaming completion
            stream = self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            for chunk in stream:
                if "choices" in chunk:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                        
        except Exception as e:
            logger.error(f"Chat stream failed: {e}")
            yield f"Error during chat: {str(e)}"

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Chat completion (OpenAI compatible format).
        """
        if not self.model:
            return "Error: Local LLM not loaded."

        try:
            response = self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            return f"Error during chat: {str(e)}"
