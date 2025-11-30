"""
NLP module for enhanced resume analysis.

This module provides advanced natural language processing capabilities including:
- PII detection using spaCy NER
- Semantic similarity analysis with SentenceTransformers
- Keyword extraction with TF-IDF
- Resume section parsing
"""

from backend.nlp.pii_detector import PIIDetector
from backend.nlp.semantic_analyzer import SemanticAnalyzer
from backend.nlp.keyword_extractor import KeywordExtractor
from backend.nlp.section_parser import SectionParser

__all__ = [
    'PIIDetector',
    'SemanticAnalyzer',
    'KeywordExtractor',
    'SectionParser'
]
