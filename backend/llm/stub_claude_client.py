"""Stub Claude client used in lite mode or when API keys are unavailable."""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional


class StubClaudeClient:
    """Return canned resume content without calling external services."""

    def __init__(
        self,
        *,
        model: str = "stub-claude-lite",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.is_stub = True
        self._usage = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_model": {},
            "cost_by_model": {},
            "average_cost_per_request": 0.0,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return a canned, ATS-friendly resume response."""

        content = self._canned_response(prompt)
        self._record_usage(prompt_tokens=len(prompt.split()), output_tokens=len(content.split()))

        return {
            "content": content,
            "model": self.model,
            "usage": {
                "input_tokens": len(prompt.split()),
                "output_tokens": len(content.split()),
            },
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
        """Stream the canned response in logical chunks."""

        content = self._canned_response(prompt)
        self._record_usage(prompt_tokens=len(prompt.split()), output_tokens=len(content.split()))

        for section in content.split("\n\n"):
            yield section + "\n"
            await asyncio.sleep(0)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return accumulated usage statistics."""

        return dict(self._usage)

    def reset_usage_stats(self) -> None:
        """Reset usage counters."""

        self._usage = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_model": {},
            "cost_by_model": {},
            "average_cost_per_request": 0.0,
        }

    def _record_usage(self, *, prompt_tokens: int, output_tokens: int) -> None:
        self._usage["total_requests"] += 1
        self._usage["total_input_tokens"] += prompt_tokens
        self._usage["total_output_tokens"] += output_tokens
        self._usage["total_tokens"] = (
            self._usage["total_input_tokens"] + self._usage["total_output_tokens"]
        )
        self._usage["requests_by_model"][self.model] = (
            self._usage["requests_by_model"].get(self.model, 0) + 1
        )
        self._usage["cost_by_model"][self.model] = 0.0
        if self._usage["total_requests"]:
            self._usage["average_cost_per_request"] = 0.0

    def _canned_response(self, prompt: str) -> str:
        return (
            "## OPTIMIZED RESUME\n"
            "Jane Doe — Senior Python Developer\n"
            "- Delivered scalable FastAPI services with async I/O and observability.\n"
            "- Improved ATS alignment by weaving role-specific keywords and metrics.\n"
            "- Highlighted cloud deployment with Docker, Kubernetes, and CI/CD.\n\n"
            "## CHANGES MADE\n"
            "- Added measurable impact for API throughput and reliability.\n"
            "- Surfaced cloud-native experience and security-minded defaults.\n"
            "- Tuned summary toward the target job description provided.\n\n"
            "## EXPECTED IMPROVEMENT\n"
            "This canned lite-mode response avoids external LLM calls while "
            "demonstrating the optimized resume structure."
        )
