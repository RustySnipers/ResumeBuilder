"""
Response Validator - Phase 3.2

Validates and sanitizes LLM responses for safety and quality.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class ResponseValidator:
    """
    Validates LLM responses for quality and safety.

    Checks for:
    - Minimum length requirements
    - Harmful content patterns
    - Quality indicators
    - Format compliance
    """

    # Patterns that might indicate harmful or inappropriate content
    HARMFUL_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script injection
        r"javascript:",  # JavaScript protocol
        r"data:text/html",  # Data URL attacks
        r"onerror\s*=",  # Event handler injection
        r"onclick\s*=",  # Click handler injection
    ]

    # Patterns that indicate potential fabrication or hallucination
    FABRICATION_INDICATORS = [
        r"I cannot verify",
        r"I don't have access to",
        r"I apologize, but I cannot",
        r"I'm unable to",
        r"I don't actually have",
    ]

    def __init__(
        self,
        min_length: int = 100,
        max_length: int = 50000,
        check_harmful: bool = True,
        check_fabrication: bool = True,
    ):
        """
        Initialize response validator.

        Args:
            min_length: Minimum acceptable response length
            max_length: Maximum acceptable response length
            check_harmful: Whether to check for harmful content
            check_fabrication: Whether to check for fabrication indicators
        """
        self.min_length = min_length
        self.max_length = max_length
        self.check_harmful = check_harmful
        self.check_fabrication = check_fabrication

    def validate(self, response: str) -> Tuple[bool, List[str]]:
        """
        Validate LLM response.

        Args:
            response: LLM response text to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check length
        if len(response) < self.min_length:
            issues.append(
                f"Response too short ({len(response)} < {self.min_length} chars)"
            )

        if len(response) > self.max_length:
            issues.append(
                f"Response too long ({len(response)} > {self.max_length} chars)"
            )

        # Check for harmful content
        if self.check_harmful:
            harmful_found = self._check_harmful_content(response)
            if harmful_found:
                issues.extend(harmful_found)

        # Check for fabrication indicators
        if self.check_fabrication:
            fabrication_found = self._check_fabrication_indicators(response)
            if fabrication_found:
                issues.extend(fabrication_found)

        is_valid = len(issues) == 0

        if not is_valid:
            logger.warning(f"Response validation failed: {issues}")

        return is_valid, issues

    def _check_harmful_content(self, response: str) -> List[str]:
        """Check for potentially harmful content patterns."""
        issues = []

        for pattern in self.HARMFUL_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                issues.append(f"Harmful pattern detected: {pattern[:30]}...")

        return issues

    def _check_fabrication_indicators(self, response: str) -> List[str]:
        """Check for fabrication or inability indicators."""
        issues = []

        for pattern in self.FABRICATION_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Fabrication indicator: {pattern}")

        return issues

    def sanitize(self, response: str) -> str:
        """
        Sanitize response by removing potentially harmful content.

        Args:
            response: Raw LLM response

        Returns:
            Sanitized response
        """
        sanitized = response

        # Remove script tags
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL
        )

        # Remove event handlers
        sanitized = re.sub(
            r"\s*on\w+\s*=\s*[\"'][^\"']*[\"']",
            "",
            sanitized,
            flags=re.IGNORECASE
        )

        # Remove javascript: protocol
        sanitized = re.sub(
            r"javascript:",
            "",
            sanitized,
            flags=re.IGNORECASE
        )

        return sanitized

    def extract_structured_response(
        self, response: str, section_markers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Extract structured sections from LLM response.

        Args:
            response: LLM response with markdown sections
            section_markers: Dict of section names to markers (e.g., {"resume": "## OPTIMIZED RESUME"})

        Returns:
            Dictionary of section_name -> content
        """
        if section_markers is None:
            section_markers = {
                "resume": "## OPTIMIZED RESUME",
                "changes": "## CHANGES MADE",
                "improvement": "## EXPECTED IMPROVEMENT",
            }

        sections = {}

        for section_name, marker in section_markers.items():
            if marker in response:
                # Find start of section
                start_idx = response.find(marker)
                content_start = start_idx + len(marker)

                # Find next section marker or end of response
                next_marker_idx = len(response)
                for other_marker in section_markers.values():
                    if other_marker == marker:
                        continue
                    idx = response.find(other_marker, content_start)
                    if idx != -1 and idx < next_marker_idx:
                        next_marker_idx = idx

                # Extract content
                content = response[content_start:next_marker_idx].strip()
                sections[section_name] = content

        return sections

    def assess_quality(self, response: str) -> Dict[str, any]:
        """
        Assess response quality with scoring.

        Returns:
            Dictionary with quality metrics
        """
        metrics = {
            "length": len(response),
            "has_structure": bool(re.search(r"##\s+\w+", response)),
            "has_bullets": bool(re.search(r"^\s*[-*]\s+", response, re.MULTILINE)),
            "has_numbers": bool(re.search(r"\d+%|\d+\+", response)),
            "paragraph_count": len(re.findall(r"\n\s*\n", response)) + 1,
            "quality_score": 0.0,
        }

        # Calculate quality score (0-1)
        score = 0.0

        # Length score (0-0.3)
        if 500 <= metrics["length"] <= 5000:
            score += 0.3
        elif 200 <= metrics["length"] < 500:
            score += 0.15

        # Structure score (0-0.3)
        if metrics["has_structure"]:
            score += 0.3

        # Content score (0-0.4)
        if metrics["has_bullets"]:
            score += 0.2
        if metrics["has_numbers"]:
            score += 0.2

        metrics["quality_score"] = round(score, 2)

        return metrics
