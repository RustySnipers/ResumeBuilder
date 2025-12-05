"""Lite-mode friendly Claude client replacement."""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional


class DummyClaudeClient:
    """Return canned responses when the real Claude client is unavailable."""

    def __init__(self, *, model: str = "dummy-claude-lite", max_tokens: int = 1024, temperature: float = 0.2):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._usage = {
            "requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        self._usage["requests"] += 1
        content = self._canned_response(prompt)
        return {
            "content": content,
            "model": self.model,
            "usage": {"input_tokens": 0, "output_tokens": len(content.split())},
            "cost": 0.0,
            "finish_reason": "lite_mode_stub",
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        self._usage["requests"] += 1
        content = self._canned_response(prompt)
        # Stream one sentence at a time
        for sentence in content.split(". "):
            yield sentence + ("." if not sentence.endswith(".") else "")
            await asyncio.sleep(0)

    def get_usage_stats(self) -> Dict[str, Any]:
        return self._usage

    def reset_usage_stats(self) -> None:
        self._usage = {
            "requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
        }

    def _canned_response(self, prompt: str) -> str:
        return (
            "Lite mode stub response. This environment does not contact external LLMs. "
            "The request was received and processed locally for offline testing."
        )
