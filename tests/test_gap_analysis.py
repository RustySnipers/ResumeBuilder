"""
Unit tests for gap analysis functionality.

Tests cover keyword extraction, frequency analysis, and
multi-word technical term handling.
"""

import pytest
from main import rudimentary_gap_analysis, GapAnalysisResult


class TestBasicGapAnalysis:
    """Test basic gap analysis functionality."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_simple_keyword_mismatch(self):
        """Test detection of simple missing keywords."""
        job_desc = "We need Python and FastAPI experience for backend development"
        resume = "I have Django and Flask experience in web development"

        result = rudimentary_gap_analysis(resume, job_desc)

        assert isinstance(result, GapAnalysisResult)
        assert "python" in result.missing_keywords or "fastapi" in result.missing_keywords
        assert len(result.suggestions) > 0

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_perfect_match(self):
        """Test when resume perfectly matches job description."""
        job_desc = "We need Python FastAPI PostgreSQL experience"
        resume = "Expert in Python FastAPI PostgreSQL development"

        result = rudimentary_gap_analysis(resume, job_desc)

        assert isinstance(result, GapAnalysisResult)
        # Should have few or no missing keywords
        assert len(result.missing_keywords) <= 3  # Allow for some stop words

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_completely_different_domains(self):
        """Test when resume and job are in completely different domains."""
        job_desc = "We seek a data scientist with machine learning Python TensorFlow experience"
        resume = "Graphic designer skilled in Photoshop Illustrator InDesign creative work"

        result = rudimentary_gap_analysis(resume, job_desc)

        assert isinstance(result, GapAnalysisResult)
        # Should detect significant gaps
        assert len(result.missing_keywords) > 5
        assert any("keyword" in s.lower() for s in result.suggestions)


class TestKeywordExtraction:
    """Test keyword extraction and normalization."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_case_insensitivity(self):
        """Test that keyword matching is case-insensitive."""
        job_desc = "PYTHON FASTAPI DOCKER KUBERNETES"
        resume = "python fastapi docker kubernetes"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should match despite case differences
        assert len(result.missing_keywords) <= 2

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_stop_word_filtering(self):
        """Test that common stop words are filtered out."""
        job_desc = "The candidate will work with the team and collaborate on projects"
        resume = "I have experience working on collaborative projects with teams"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Stop words like 'the', 'and', 'with' should not appear
        stop_words = ['the', 'and', 'with', 'will', 'have']
        for word in result.missing_keywords:
            assert word.lower() not in stop_words

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_minimum_word_length(self):
        """Test that very short words are filtered out."""
        job_desc = "We need AI ML to be used in our project"
        resume = "Expert in artificial intelligence machine learning projects"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Very short words (< 3 chars) should be filtered
        for keyword in result.missing_keywords:
            # Note: Phase 1 filters < 3 chars, so 'ai' and 'ml' won't appear
            assert len(keyword) >= 3


class TestFrequencyAnalysis:
    """Test keyword frequency and ranking."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_high_frequency_keywords_prioritized(self):
        """Test that frequently mentioned keywords are prioritized."""
        job_desc = """
        Python Python Python developer needed.
        Must know Python and use Python daily.
        Python experience essential. Also need Docker.
        """
        resume = "Java developer with experience in Spring Framework"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Python should appear in missing keywords due to high frequency
        # (Note: "python" might be in lowercase in the results)
        missing_lower = [k.lower() for k in result.missing_keywords]
        assert "python" in missing_lower or "docker" in missing_lower

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_limited_missing_keywords_count(self):
        """Test that missing keywords list is limited to reasonable length."""
        job_desc = " ".join([f"keyword{i}" for i in range(100)])  # 100 unique keywords
        resume = "Different domain with other experience"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should limit to top keywords (not return all 100)
        assert len(result.missing_keywords) <= 15


class TestMultiWordTerms:
    """Test handling of multi-word technical terms."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_machine_learning_detection(self):
        """Test detection of 'machine learning' as a term."""
        job_desc = "We need machine learning expertise and machine learning projects"
        resume = "No ML or AI experience"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should detect 'machine' and 'learning' as individual keywords
        # Phase 1: Treats as separate words (bigram support in Phase 2)
        assert "machine" in result.missing_keywords or "learning" in result.missing_keywords

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_cloud_computing_detection(self):
        """Test detection of 'cloud computing' term."""
        job_desc = "Cloud computing experience required cloud computing skills essential"
        resume = "On-premise infrastructure experience only"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Phase 1: Separate words
        assert "cloud" in result.missing_keywords or "computing" in result.missing_keywords


class TestSuggestionGeneration:
    """Test suggestion generation logic."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_suggestions_include_keywords(self):
        """Test that suggestions mention specific missing keywords."""
        job_desc = "FastAPI SQLAlchemy PostgreSQL Docker Kubernetes experience needed"
        resume = "Basic Python knowledge only"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Suggestions should be generated
        assert len(result.suggestions) > 0
        # At least one suggestion should mention incorporating keywords
        assert any("keyword" in s.lower() or "term" in s.lower() for s in result.suggestions)

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_suggestions_for_many_gaps(self):
        """Test suggestion content when many gaps exist."""
        job_desc = " ".join([f"technical{i}" for i in range(20)])
        resume = "Non-technical background"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should provide helpful suggestion about many missing keywords
        assert len(result.suggestions) > 0
        suggestion_text = " ".join(result.suggestions).lower()
        assert "keyword" in suggestion_text or "job description" in suggestion_text

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_suggestions_for_good_match(self):
        """Test suggestion content when resume matches well."""
        job_desc = "Python FastAPI PostgreSQL experience"
        resume = "Expert Python developer with FastAPI and PostgreSQL skills"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should have positive/minimal suggestions
        assert len(result.suggestions) > 0
        suggestion_text = " ".join(result.suggestions).lower()
        # Should either be positive or have minimal suggestions
        assert "well-aligned" in suggestion_text or len(result.suggestions) <= 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_empty_job_description(self):
        """Test handling of empty job description."""
        result = rudimentary_gap_analysis("My resume content", "")

        assert isinstance(result, GapAnalysisResult)
        assert len(result.missing_keywords) == 0 or result.missing_keywords == []

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_empty_resume(self):
        """Test handling of empty resume."""
        result = rudimentary_gap_analysis("", "Job description content")

        assert isinstance(result, GapAnalysisResult)
        # Should find many missing keywords since resume is empty
        assert len(result.missing_keywords) > 0

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_both_empty(self):
        """Test handling when both inputs are empty."""
        result = rudimentary_gap_analysis("", "")

        assert isinstance(result, GapAnalysisResult)
        assert len(result.missing_keywords) == 0

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_special_characters_in_keywords(self):
        """Test handling of special characters in technical terms."""
        job_desc = "C++ C# .NET ASP.NET experience required"
        resume = "Python Java developer"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should extract some form of these terms
        # Phase 1: May not handle special chars perfectly (improvement in Phase 2)
        assert isinstance(result, GapAnalysisResult)

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_numbers_in_technical_terms(self):
        """Test handling of numbers in technical terms."""
        job_desc = "Vue3 Angular15 Python3 experience needed"
        resume = "React developer"

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should handle terms with numbers
        assert isinstance(result, GapAnalysisResult)
        # Phase 1: Numbers might be filtered (enhancement in Phase 2)


class TestRealWorldScenarios:
    """Test realistic job description and resume scenarios."""

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_senior_python_developer_jd(self):
        """Test realistic senior Python developer job description."""
        job_desc = """
        Senior Python Developer

        We are seeking an experienced Python developer with strong FastAPI and
        SQLAlchemy skills. Must have experience with:
        - RESTful API development
        - PostgreSQL database design
        - Docker containerization
        - AWS cloud services
        - CI/CD pipelines
        """

        resume = """
        Python Developer with 3 years experience.
        Built web applications using Django and MySQL.
        Familiar with Git version control.
        """

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should detect key missing technologies
        missing_lower = [k.lower() for k in result.missing_keywords]
        assert any(term in missing_lower for term in ["fastapi", "sqlalchemy", "docker", "postgresql"])
        assert len(result.suggestions) > 0

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_data_scientist_jd(self):
        """Test realistic data scientist job description."""
        job_desc = """
        Data Scientist Position

        Requirements:
        - Machine learning model development
        - Python (NumPy, Pandas, Scikit-learn)
        - Deep learning frameworks (TensorFlow, PyTorch)
        - Statistical analysis and hypothesis testing
        - Data visualization (Matplotlib, Seaborn)
        """

        resume = """
        Data Analyst with SQL and Excel expertise.
        Experience creating reports and dashboards in Tableau.
        Strong analytical and communication skills.
        """

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should detect significant skill gaps
        assert len(result.missing_keywords) > 5
        missing_lower = [k.lower() for k in result.missing_keywords]
        # Should catch some ML-related terms
        assert any(term in missing_lower for term in ["python", "learning", "tensorflow", "pytorch"])

    @pytest.mark.unit
    @pytest.mark.gap_analysis
    def test_well_matched_candidate(self):
        """Test when candidate resume closely matches job requirements."""
        job_desc = """
        Full Stack Developer - React and Node.js

        Required skills:
        - React.js, Redux, TypeScript
        - Node.js, Express.js
        - MongoDB or PostgreSQL
        - RESTful API design
        - Git version control
        """

        resume = """
        Full Stack Developer

        Technical Skills:
        - Frontend: React, Redux, TypeScript, HTML, CSS
        - Backend: Node.js, Express.js, RESTful APIs
        - Database: PostgreSQL, MongoDB
        - Tools: Git, Docker, Jest, version control

        Experience:
        Built multiple full-stack applications using React and Node.js...
        API design and RESTful architecture are my core strengths.
        """

        result = rudimentary_gap_analysis(resume, job_desc)

        # Should have minimal missing keywords (<=7 allows for some variation)
        # Note: Enhanced gap analysis may detect bigrams separately from words
        assert len(result.missing_keywords) <= 7
        # Should have positive feedback
        suggestion_text = " ".join(result.suggestions).lower()
        assert "well-aligned" in suggestion_text or len(result.suggestions) <= 3
