"""
Resume Section Parsing and Analysis.

This module provides resume section parsing capabilities including:
- Automatic section detection and extraction
- Keyword placement and density analysis per section
- Keyword stuffing detection
"""

from typing import Dict, List
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class SectionParser:
    """Resume section parser for analyzing document structure and keyword distribution."""

    def __init__(self):
        """Initialize the section parser with common section headers."""
        # Common section headers (case-insensitive matching)
        self.section_headers = {
            'summary': ['summary', 'professional summary', 'profile', 'objective', 'about', 'about me'],
            'experience': ['experience', 'work experience', 'employment', 'work history', 'professional experience', 'employment history'],
            'education': ['education', 'academic background', 'qualifications', 'academic qualifications'],
            'skills': ['skills', 'technical skills', 'competencies', 'expertise', 'core competencies'],
            'projects': ['projects', 'portfolio', 'personal projects'],
            'certifications': ['certifications', 'certificates', 'licenses', 'professional certifications'],
            'awards': ['awards', 'honors', 'achievements', 'accomplishments'],
            'publications': ['publications', 'research', 'papers'],
        }

    def parse_sections(self, resume_text: str) -> Dict[str, str]:
        """
        Parse resume into sections.

        Args:
            resume_text: Full resume text

        Returns:
            Dict mapping section name to section content
        """
        if not resume_text:
            return {}

        sections = {}
        lines = resume_text.split('\n')

        current_section = 'header'  # Default section
        current_content = []

        for line in lines:
            line_stripped = line.strip()

            if not line_stripped:
                continue

            # Check if line is a section header
            detected_section = self._detect_section_header(line_stripped)

            if detected_section:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)

                # Start new section
                current_section = detected_section
                current_content = []
            else:
                current_content.append(line_stripped)

        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def analyze_keyword_density(self, section_text: str, keywords: List[str]) -> Dict[str, float]:
        """
        Calculate keyword density for each keyword in section.

        Args:
            section_text: Text to analyze
            keywords: List of keywords to search for

        Returns:
            Dict mapping keyword to density (occurrences / total_words)
        """
        if not section_text:
            return {kw: 0.0 for kw in keywords}

        words = section_text.lower().split()
        total_words = len(words)

        if total_words == 0:
            return {kw: 0.0 for kw in keywords}

        density = {}
        for keyword in keywords:
            count = section_text.lower().count(keyword.lower())
            density[keyword] = count / total_words

        return density

    def detect_keyword_stuffing(self, section_text: str, threshold: float = 0.05) -> Dict[str, bool]:
        """
        Detect keyword stuffing (excessive keyword repetition).

        Args:
            section_text: Text to analyze
            threshold: Density threshold (default 5% = stuffing)

        Returns:
            Dict mapping keyword to boolean (True if stuffed)
        """
        if not section_text:
            return {}

        words = section_text.lower().split()
        word_counts = Counter(words)
        total_words = len(words)

        if total_words == 0:
            return {}

        stuffed_keywords = {}
        for word, count in word_counts.items():
            if len(word) > 3:  # Ignore short words
                density = count / total_words
                stuffed_keywords[word] = density > threshold

        # Filter to only stuffed keywords
        return {k: v for k, v in stuffed_keywords.items() if v}

    def _detect_section_header(self, line: str) -> str:
        """
        Detect if a line is a section header.

        Args:
            line: Line to analyze

        Returns:
            Section name if detected, None otherwise
        """
        line_lower = line.lower()

        # Check if line is all caps or title case (common for headers)
        if not (line.isupper() or line.istitle()):
            # Also check if it's a short line that might be a header
            if len(line.split()) > 5:
                return None

        # Check against known headers
        for section_name, headers in self.section_headers.items():
            for header in headers:
                if header in line_lower:
                    return section_name

        return None
