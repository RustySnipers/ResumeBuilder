"""
Keyword Extraction using TF-IDF and NLP techniques.

This module provides advanced keyword extraction capabilities including:
- TF-IDF based keyword ranking
- N-gram extraction (bigrams, trigrams, 4-grams)
- Stemming/lemmatization with NLTK
- Industry-specific vocabulary matching
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import re
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Advanced keyword extractor using TF-IDF and NLP techniques."""

    def __init__(self):
        """Initialize the keyword extractor with NLTK components."""
        try:
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            logger.warning("NLTK data not found. Some features may not work correctly.")
            self.lemmatizer = None
            self.stop_words = set()

        # Industry vocabularies
        self.industry_vocab = {
            'tech': [
                'python', 'java', 'javascript', 'react', 'angular', 'vue', 'django', 'flask',
                'fastapi', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'machine learning',
                'deep learning', 'tensorflow', 'pytorch', 'sql', 'nosql', 'mongodb', 'postgresql',
                'redis', 'git', 'ci/cd', 'devops', 'microservices', 'rest api', 'graphql',
                'typescript', 'node.js', 'spring boot', 'golang', 'rust', 'c++', 'scala',
                'spark', 'hadoop', 'kafka', 'elasticsearch', 'jenkins', 'terraform', 'ansible'
            ],
            'healthcare': [
                'hipaa', 'ehr', 'emr', 'clinical', 'patient care', 'medical records',
                'healthcare compliance', 'nursing', 'diagnosis', 'treatment', 'pharmacy',
                'medical coding', 'icd-10', 'cpt', 'healthcare it', 'telemedicine'
            ],
            'finance': [
                'financial analysis', 'risk management', 'portfolio', 'trading', 'investment',
                'accounting', 'gaap', 'sox', 'audit', 'financial modeling', 'valuation',
                'derivatives', 'equity research', 'fixed income', 'compliance', 'fintech',
                'blockchain', 'cryptocurrency', 'regulatory compliance', 'basel iii'
            ],
        }

    def extract_tfidf_keywords(
        self,
        documents: List[str],
        top_n: int = 30
    ) -> List[Tuple[str, float]]:
        """
        Extract top keywords using TF-IDF.

        Args:
            documents: List of documents (e.g., [job_desc, resume])
            top_n: Number of top keywords to return

        Returns:
            List of (keyword, score) tuples sorted by score
        """
        if not documents or all(not doc.strip() for doc in documents):
            return []

        try:
            # Preprocess
            processed_docs = [self._preprocess(doc) for doc in documents]

            # TF-IDF
            vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 3),  # Unigrams to trigrams
                stop_words='english',
                min_df=1
            )

            tfidf_matrix = vectorizer.fit_transform(processed_docs)
            feature_names = vectorizer.get_feature_names_out()

            # Get scores for first document (job description typically)
            scores = tfidf_matrix[0].toarray()[0]

            # Create keyword-score pairs
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)

            return keyword_scores[:top_n]
        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}")
            return []

    def extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """
        Extract n-grams from text.

        Args:
            text: Input text
            n: N-gram size (2=bigrams, 3=trigrams, etc.)

        Returns:
            List of n-grams
        """
        tokens = self._tokenize(text)
        ngrams = []

        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.append(ngram)

        return ngrams

    def extract_industry_keywords(self, text: str, industry: str = 'tech') -> List[str]:
        """
        Extract keywords specific to an industry.

        Args:
            text: Input text
            industry: Industry type ('tech', 'healthcare', 'finance')

        Returns:
            List of industry-specific keywords found
        """
        text_lower = text.lower()
        vocab = self.industry_vocab.get(industry, [])

        found_keywords = [kw for kw in vocab if kw in text_lower]
        return found_keywords

    def _preprocess(self, text: str) -> str:
        """
        Preprocess text: lowercase, remove special chars, lemmatize.

        Args:
            text: Input text

        Returns:
            Preprocessed text
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove special characters but keep spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)

        # Tokenize and lemmatize (if available)
        if self.lemmatizer:
            tokens = text.split()
            lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]
            return ' '.join(lemmatized)
        else:
            return text

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words, removing stop words.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        return [w for w in words if w not in self.stop_words]
