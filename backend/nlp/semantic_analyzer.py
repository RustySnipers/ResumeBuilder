"""
Semantic Analysis using SentenceTransformers.

This module provides semantic similarity analysis capabilities including:
- Resume-to-job-description similarity calculation
- Section-level similarity scores
- Synonym detection for technical terms
- Skills extraction using NLP
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """Semantic analyzer using SentenceTransformers for similarity calculation."""

    def __init__(self):
        """Initialize the semantic analyzer with models."""
        self.model = None
        self.nlp = None
        self.np = None
        
        try:
            import numpy as np
            self.np = np
        except ImportError:
            logger.warning("numpy not found. Semantic analysis functionality will be limited.")

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("sentence-transformers not found. Semantic analysis will be disabled.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}")
            self.model = None

        try:
            import spacy
            self.nlp = spacy.load('en_core_web_lg')
        except ImportError:
             logger.warning("spacy not found. NLP features will be disabled.")
        except OSError:
            logger.warning("spaCy model 'en_core_web_lg' not found.")
            self.nlp = None

        # Technical term synonyms (expandable)
        self.synonym_groups = {
            'machine_learning': ['ml', 'machine learning', 'deep learning', 'ai', 'artificial intelligence'],
            'python': ['python', 'python3', 'py'],
            'javascript': ['javascript', 'js', 'ecmascript'],
            'react': ['react', 'reactjs', 'react.js'],
            'cloud': ['cloud computing', 'cloud', 'aws', 'azure', 'gcp'],
            'database': ['database', 'db', 'sql', 'nosql', 'postgresql', 'mysql', 'mongodb'],
            'kubernetes': ['kubernetes', 'k8s'],
            'docker': ['docker', 'containerization', 'containers'],
            'cicd': ['ci/cd', 'cicd', 'continuous integration', 'continuous deployment'],
        }

    def calculate_similarity(self, resume: str, job_desc: str) -> float:
        """
        Calculate semantic similarity (0-1) between resume and job description.

        Args:
            resume: Resume text
            job_desc: Job description text

        Returns:
            Similarity score between 0 and 1
        """
        if not self.model:
            logger.error("SentenceTransformer model not available")
            return 0.0

        if not resume or not job_desc:
            return 0.0

        try:
            resume_embedding = self.model.encode(resume)
            jd_embedding = self.model.encode(job_desc)

            # Cosine similarity
            if self.np:
                similarity = self.np.dot(resume_embedding, jd_embedding) / (
                    self.np.linalg.norm(resume_embedding) * self.np.linalg.norm(jd_embedding)
                )
                return float(similarity)
            else:
                return 0.0
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    def calculate_section_similarity(
        self,
        resume: str,
        job_desc: str,
        sections: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Calculate similarity for each resume section against job description.

        Args:
            resume: Full resume text
            job_desc: Job description text
            sections: Dict mapping section name to section text

        Returns:
            Dict mapping section name to similarity score
        """
        if not self.model:
            logger.error("SentenceTransformer model not available")
            return {name: 0.0 for name in sections.keys()}

        jd_embedding = self.model.encode(job_desc)
        section_scores = {}

        for section_name, section_text in sections.items():
            if not section_text.strip():
                section_scores[section_name] = 0.0
                continue

            try:
                section_embedding = self.model.encode(section_text)
                if self.np:
                    similarity = self.np.dot(section_embedding, jd_embedding) / (
                        self.np.linalg.norm(section_embedding) * self.np.linalg.norm(jd_embedding)
                    )
                    section_scores[section_name] = float(similarity)
                else:
                    section_scores[section_name] = 0.0
            except Exception as e:
                logger.error(f"Section similarity calculation failed for {section_name}: {e}")
                section_scores[section_name] = 0.0

        return section_scores

    def detect_synonyms(self, resume_text: str, jd_keywords: List[str]) -> Dict[str, List[str]]:
        """
        Detect which JD keywords have synonyms in the resume.

        Args:
            resume_text: Resume text to search
            jd_keywords: Keywords from job description

        Returns:
            Dict mapping JD keyword to list of matching synonyms found in resume
        """
        resume_lower = resume_text.lower()
        matches = {}

        for jd_keyword in jd_keywords:
            jd_keyword_lower = jd_keyword.lower()

            # Check if JD keyword belongs to any synonym group
            for group_name, synonyms in self.synonym_groups.items():
                if jd_keyword_lower in synonyms:
                    # Check if any other synonym from this group appears in resume
                    found_synonyms = [
                        syn for syn in synonyms
                        if syn in resume_lower and syn != jd_keyword_lower
                    ]
                    if found_synonyms:
                        matches[jd_keyword] = found_synonyms
                    break

        return matches

    def extract_skills(self, text: str) -> List[str]:
        """
        Extract technical skills using NER and pattern matching.

        Args:
            text: Input text to analyze

        Returns:
            List of identified skills
        """
        if not self.nlp:
            logger.warning("spaCy model not available for skill extraction")
            return []

        try:
            doc = self.nlp(text)
            skills = []

            # Extract noun chunks (potential skills)
            for chunk in doc.noun_chunks:
                # Filter for technical-sounding terms (2-4 words, contains certain patterns)
                chunk_text = chunk.text.lower()
                if 2 <= len(chunk_text.split()) <= 4:
                    # Check if contains technical indicators
                    if any(term in chunk_text for term in [
                        'data', 'machine', 'software', 'web', 'cloud',
                        'api', 'framework', 'development', 'engineer'
                    ]):
                        skills.append(chunk.text)

            # Also extract entities tagged as PRODUCT or ORG (often frameworks/tools)
            for ent in doc.ents:
                if ent.label_ in ['PRODUCT', 'ORG'] and len(ent.text.split()) <= 3:
                    skills.append(ent.text)

            return list(set(skills))  # Remove duplicates
        except Exception as e:
            logger.error(f"Skill extraction failed: {e}")
            return []
