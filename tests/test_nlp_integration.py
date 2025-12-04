"""
Comprehensive integration tests for NLP modules.

Tests cover:
- PII detection with spaCy NER
- Semantic similarity calculation
- Keyword extraction with TF-IDF
- Section parsing and analysis
"""

import pytest
from backend.nlp.pii_detector import PIIDetector
from backend.nlp.semantic_analyzer import SemanticAnalyzer
from backend.nlp.keyword_extractor import KeywordExtractor
from backend.nlp.section_parser import SectionParser


@pytest.fixture
def sample_resume():
    return """
John Doe
john.doe@email.com | (555) 123-4567

PROFESSIONAL SUMMARY
Experienced Python developer with 5 years of machine learning expertise.

EXPERIENCE
Senior Software Engineer | Tech Corp | 2020-Present
- Built ML models using Python and TensorFlow
- Deployed models to AWS cloud infrastructure
- Led team of 3 engineers

EDUCATION
BS Computer Science | MIT | 2019

SKILLS
Python, TensorFlow, PyTorch, AWS, Docker, Kubernetes
"""


@pytest.fixture
def sample_job_desc():
    return """
Senior ML Engineer

We seek an experienced ML engineer with:
- 5+ years Python and machine learning
- Deep learning frameworks (PyTorch, TensorFlow)
- Cloud deployment (AWS, GCP)
- Docker and Kubernetes
- Team leadership experience
"""


class TestPIIDetector:
    """Test suite for PII detection."""

    def test_detects_email(self):
        detector = PIIDetector()
        text = "Contact: john@example.com"
        redacted, counts = detector.detect_and_redact(text)
        assert '<PII_REDACTED_EMAIL>' in redacted
        assert 'john@example.com' not in redacted
        assert counts['emails'] == 1

    def test_detects_phone(self):
        detector = PIIDetector()
        text = "Call me at (555) 123-4567"
        redacted, counts = detector.detect_and_redact(text)
        assert '<PII_REDACTED_PHONE>' in redacted
        assert '(555) 123-4567' not in redacted
        assert counts['phones'] == 1

    def test_detects_person_name_with_ner(self, sample_resume):
        detector = PIIDetector()
        redacted, counts = detector.detect_and_redact(sample_resume)
        # John Doe should be detected and redacted
        assert counts['person_names'] >= 1 or '<PII_REDACTED_NAME>' in redacted

    def test_preserves_organization_names(self, sample_resume):
        detector = PIIDetector()
        redacted, counts = detector.detect_and_redact(sample_resume)
        # Tech Corp, MIT should be preserved for context
        assert 'Tech Corp' in redacted or 'MIT' in redacted

    def test_handles_empty_text(self):
        detector = PIIDetector()
        redacted, counts = detector.detect_and_redact("")
        assert redacted == ""
        assert counts == {}

    def test_detects_url(self):
        detector = PIIDetector()
        text = "Portfolio: https://github.com/user"
        redacted, counts = detector.detect_and_redact(text)
        assert '<PII_REDACTED_URL>' in redacted
        assert 'https://github.com/user' not in redacted

    def test_detects_address(self):
        detector = PIIDetector()
        text = "Lives at 123 Main Street"
        redacted, counts = detector.detect_and_redact(text)
        assert '<PII_REDACTED_ADDRESS>' in redacted
        assert '123 Main Street' not in redacted

    def test_detects_ssn(self):
        detector = PIIDetector()
        text = "SSN: 123-45-6789"
        redacted, counts = detector.detect_and_redact(text)
        assert '<PII_REDACTED_SSN>' in redacted
        assert '123-45-6789' not in redacted


class TestSemanticAnalyzer:
    """Test suite for semantic similarity analysis."""

    def test_calculates_similarity(self, sample_resume, sample_job_desc):
        analyzer = SemanticAnalyzer()
        similarity = analyzer.calculate_similarity(sample_resume, sample_job_desc)
        assert 0.0 <= similarity <= 1.0
        # Should be decent match given overlapping keywords
        assert similarity > 0.5

    def test_similarity_identical_texts(self):
        analyzer = SemanticAnalyzer()
        text = "Python developer with machine learning experience"
        similarity = analyzer.calculate_similarity(text, text)
        assert similarity > 0.99  # Should be nearly 1.0

    def test_similarity_different_texts(self):
        analyzer = SemanticAnalyzer()
        text1 = "Python machine learning engineer"
        text2 = "Chef with culinary expertise"
        similarity = analyzer.calculate_similarity(text1, text2)
        assert similarity < 0.3  # Should be low

    def test_detects_synonyms(self):
        analyzer = SemanticAnalyzer()
        resume = "I have machine learning experience with Python"
        synonyms = analyzer.detect_synonyms(resume, ['ml', 'ai'])
        # 'machine learning' is a synonym of 'ml' and 'ai'
        assert 'ml' in synonyms or 'ai' in synonyms

    def test_section_similarity(self, sample_resume, sample_job_desc):
        analyzer = SemanticAnalyzer()
        parser = SectionParser()
        sections = parser.parse_sections(sample_resume)

        section_scores = analyzer.calculate_section_similarity(
            sample_resume, sample_job_desc, sections
        )

        assert isinstance(section_scores, dict)
        # Should have scores for detected sections
        assert len(section_scores) > 0
        # All scores should be between 0 and 1
        for score in section_scores.values():
            assert 0.0 <= score <= 1.0


class TestKeywordExtractor:
    """Test suite for keyword extraction."""

    def test_extracts_tfidf_keywords(self, sample_job_desc, sample_resume):
        extractor = KeywordExtractor()
        keywords = extractor.extract_tfidf_keywords([sample_job_desc, sample_resume], top_n=10)
        assert len(keywords) > 0
        # Each keyword should be (term, score) tuple
        assert all(isinstance(kw, tuple) and len(kw) == 2 for kw in keywords)
        # Scores should be non-negative
        assert all(score >= 0 for _, score in keywords)

    def test_extracts_industry_keywords(self, sample_job_desc):
        extractor = KeywordExtractor()
        tech_keywords = extractor.extract_industry_keywords(sample_job_desc, 'tech')
        # Should find some tech keywords
        assert len(tech_keywords) > 0
        # Should include common tech terms
        assert any(kw in tech_keywords for kw in ['python', 'aws', 'docker', 'kubernetes'])

    def test_extracts_ngrams(self):
        extractor = KeywordExtractor()
        text = "machine learning and deep learning are important"
        bigrams = extractor.extract_ngrams(text, n=2)
        assert len(bigrams) > 0
        # Should contain some expected bigrams
        assert any('machine' in bg and 'learning' in bg for bg in bigrams)


class TestSectionParser:
    """Test suite for section parsing."""

    def test_parses_sections(self, sample_resume):
        parser = SectionParser()
        sections = parser.parse_sections(sample_resume)
        # Should identify multiple sections
        assert len(sections) > 1
        # Common sections should be present
        assert any(section in sections for section in ['summary', 'experience', 'education', 'skills'])

    def test_analyzes_keyword_density(self):
        parser = SectionParser()
        text = "Python is great. Python is powerful. I love Python programming and Python development."
        density = parser.analyze_keyword_density(text, ['python', 'java'])
        assert density['python'] > 0.2  # High density for Python
        assert density['java'] == 0.0  # No Java mentions

    def test_detects_keyword_stuffing(self):
        parser = SectionParser()
        # Text with excessive keyword repetition
        stuffed_text = "Python " * 20 + "developer"
        stuffed = parser.detect_keyword_stuffing(stuffed_text, threshold=0.05)
        assert 'python' in stuffed
        assert stuffed['python']

    def test_no_keyword_stuffing_normal_text(self):
        parser = SectionParser()
        normal_text = "I am a Python developer with experience in web development using Django and Flask frameworks."
        stuffed = parser.detect_keyword_stuffing(normal_text, threshold=0.05)
        # Should not detect stuffing in normal text
        assert len(stuffed) == 0


class TestIntegration:
    """Integration tests combining multiple NLP components."""

    def test_full_analysis_pipeline(self, sample_resume, sample_job_desc):
        """Test complete analysis workflow."""
        # 1. PII Detection
        pii_detector = PIIDetector()
        resume_redacted, _ = pii_detector.detect_and_redact(sample_resume)
        jd_redacted, _ = pii_detector.detect_and_redact(sample_job_desc)

        # 2. Section Parsing
        parser = SectionParser()
        sections = parser.parse_sections(resume_redacted)

        # 3. Semantic Analysis
        analyzer = SemanticAnalyzer()
        similarity = analyzer.calculate_similarity(resume_redacted, jd_redacted)

        # 4. Keyword Extraction
        extractor = KeywordExtractor()
        keywords = extractor.extract_tfidf_keywords([jd_redacted, resume_redacted], top_n=15)

        # Assertions
        assert similarity > 0
        assert len(sections) > 0
        assert len(keywords) > 0

        # Workflow should preserve data integrity
        assert isinstance(resume_redacted, str)
        assert isinstance(sections, dict)
        assert isinstance(keywords, list)
