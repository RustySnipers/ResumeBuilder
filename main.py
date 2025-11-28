"""
AI-Powered ATS-Friendly Resume Builder - Backend API (Phase 1: Foundation)

This module implements the core FastAPI backend with mandatory PII redaction
and enhanced gap analysis for resume optimization.

Technical Stack:
- Python 3.10+
- FastAPI for REST API
- Pydantic for data validation and serialization

Phase 1 Status: ✅ Enhanced with improved PII redaction and gap analysis

Future Phase TODOs:
--------------------

TODO Phase 2: Persistence Layer
- Add PostgreSQL database for resume/job storage
- Implement SQLAlchemy models for Resume, JobDescription, AnalysisResult
- Add session management for user workflows
- Implement resume version history tracking
- Add Redis cache for frequently accessed data
- Design API endpoints: POST /resumes, GET /resumes/{id}, PUT /resumes/{id}

TODO Phase 3: LLM Integration
- Integrate Claude Sonnet 4.5 API using anthropic-sdk
- Implement retry logic with exponential backoff for API calls
- Add streaming support for real-time resume generation
- Create LLM response validation and safety checks
- Implement cost tracking and rate limiting
- Add endpoints: POST /api/v1/generate, POST /api/v1/optimize

TODO Phase 4: Authentication & Authorization
- Add user authentication (OAuth2, JWT tokens)
- Implement role-based access control (RBAC)
- Add API key management for developers
- Create user management endpoints
- Add rate limiting per user/API key
- Implement audit logging for security compliance

TODO Phase 5: Production Features
- Add export to PDF/DOCX formats (reportlab, python-docx)
- Implement resume templates and styling
- Add A/B testing for resume variations
- Create analytics dashboard (match scores, success rates)
- Add email notifications for resume updates
- Implement webhook support for integrations
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import re
from collections import Counter

# ============================================================================
# FastAPI Application Instance
# ============================================================================

app = FastAPI(
    title="ATS Resume Builder API",
    description="Secure, compliant backend for AI-powered resume tailoring",
    version="1.0.0-phase1"
)


# ============================================================================
# Pydantic Models
# ============================================================================

class ResumeInput(BaseModel):
    """Input model for resume analysis requests.

    Attributes:
        job_description_text: The target job description text
        resume_raw_text: The user's original resume content
    """
    job_description_text: str = Field(
        ...,
        description="The job description to tailor the resume towards",
        min_length=10
    )
    resume_raw_text: str = Field(
        ...,
        description="The original resume text to be analyzed and tailored",
        min_length=10
    )


class GapAnalysisResult(BaseModel):
    """Output model for gap analysis results.

    Attributes:
        missing_keywords: Keywords from job description absent in resume
        suggestions: Actionable suggestions for resume improvement
    """
    missing_keywords: List[str] = Field(
        ...,
        description="Keywords present in job description but missing from resume"
    )
    suggestions: List[str] = Field(
        ...,
        description="Specific suggestions for improving resume alignment"
    )


# ============================================================================
# Core Utility Functions
# ============================================================================

def redact_pii(text: str) -> str:
    """
    SECURITY GATE: Redact Personally Identifiable Information (PII) from text.

    This is a mandatory non-bypassable gate ensuring PII encryption/redaction
    before any prompt is constructed for external LLM use.

    Phase 1 Implementation: Enhanced regex-based redaction with improved patterns.
    Future phases will implement comprehensive PII detection using:
    - Named Entity Recognition (NER) models (spaCy, transformers)
    - Context-aware person/company name disambiguation
    - Integration with PII detection services (AWS Comprehend, Google DLP)

    Args:
        text: Raw text potentially containing PII

    Returns:
        Text with PII replaced by <PII_REDACTED_*> placeholders

    Examples:
        >>> redact_pii("Contact: john.doe@email.com, (555) 123-4567")
        "Contact: <PII_REDACTED_EMAIL>, <PII_REDACTED_PHONE>"
    """
    if not text:
        return text

    # Phase 1: Enhanced pattern-based redaction
    redacted = text

    # Redact URLs (LinkedIn, GitHub, personal websites)
    # Note: This prevents personal profile URLs from leaking identity
    url_pattern = r'https?://[^\s<>"\')]+|www\.[^\s<>"\')]+'
    redacted = re.sub(url_pattern, '<PII_REDACTED_URL>', redacted, flags=re.IGNORECASE)

    # Redact email addresses (comprehensive pattern)
    # Handles: user@domain.com, user+tag@domain.co.uk, user.name@subdomain.domain.com
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    redacted = re.sub(email_pattern, '<PII_REDACTED_EMAIL>', redacted)

    # Redact phone numbers (multiple international formats)
    phone_patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890, 123-456-7890, 123.456.7890
        r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International: +1-555-123-4567
        r'\d{3}[-.\s]\d{4}',  # Simple: 555-1234 (7-digit)
    ]
    for pattern in phone_patterns:
        redacted = re.sub(pattern, '<PII_REDACTED_PHONE>', redacted)

    # Redact SSN and similar government ID patterns
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    redacted = re.sub(ssn_pattern, '<PII_REDACTED_SSN>', redacted)

    # Redact street addresses (enhanced pattern)
    # Matches: 123 Main Street, 456 Park Ave, 789 Oak St, etc.
    address_pattern = r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b'
    redacted = re.sub(address_pattern, '<PII_REDACTED_ADDRESS>', redacted, flags=re.IGNORECASE)

    # Redact common name patterns at document start (heuristic)
    # Matches capitalized words at start of text (likely name on resume)
    # Phase 1 limitation: May not distinguish personal names from company names
    # This is a simple heuristic; Phase 2 will use NER for accurate detection
    name_at_start_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*\n'
    redacted = re.sub(name_at_start_pattern, '<PII_REDACTED_NAME>\n', redacted, flags=re.MULTILINE)

    # TODO Phase 2: Implement NER-based name detection
    # - Use spaCy or transformers for PERSON entity recognition
    # - Distinguish between person names and company/organization names
    # - Context-aware detection (e.g., "John Doe" in "John Doe worked at..." vs "John Doe Company")

    # TODO Phase 2: Additional PII patterns
    # - Credit card numbers (Luhn algorithm validation)
    # - Date of birth patterns (MM/DD/YYYY, etc.)
    # - Passport numbers
    # - Driver's license numbers
    # - Geographic coordinates (latitude/longitude)
    # - IP addresses
    # - MAC addresses

    # TODO Phase 2: False positive reduction
    # - Whitelist common technical terms (e.g., "127.0.0.1" is localhost, not PII)
    # - Preserve code snippets and technical examples
    # - Context-aware redaction (e.g., phone numbers in contact section vs. product codes)

    return redacted


def rudimentary_gap_analysis(resume: str, job_description: str) -> GapAnalysisResult:
    """
    Perform enhanced keyword gap analysis between resume and job description.

    Phase 1 Implementation: Improved tokenization with multi-word term detection
    and better technical keyword extraction.

    Args:
        resume: The resume text (should be PII-redacted)
        job_description: The job description text (should be PII-redacted)

    Returns:
        GapAnalysisResult containing missing keywords and suggestions

    Algorithm:
        1. Extract both single-word and multi-word technical terms
        2. Normalize to lowercase and filter common stop words
        3. Identify frequent keywords in job description (top candidates)
        4. Check which high-frequency keywords are absent from resume
        5. Generate actionable suggestions based on gaps
    """
    # Expanded stop words list (common English words to filter)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how', 'our', 'your',
        'their', 'its', 'his', 'her', 'my', 'all', 'both', 'each', 'few',
        'more', 'most', 'other', 'some', 'such', 'than', 'too', 'very',
        'about', 'after', 'before', 'between', 'during', 'through', 'into',
        'over', 'under', 'above', 'below', 'up', 'down', 'out', 'off', 'then',
        'there', 'here', 'now', 'just', 'only', 'also', 'any', 'every', 'much',
        'many', 'well', 'even', 'still', 'back', 'again', 'being', 'get', 'got'
    }

    # Common multi-word technical terms (bigrams)
    # Phase 1: Hardcoded list; Phase 2 will use n-gram extraction algorithms
    common_bigrams = [
        'machine learning', 'deep learning', 'artificial intelligence',
        'data science', 'cloud computing', 'software engineering',
        'full stack', 'front end', 'back end', 'web development',
        'mobile development', 'agile methodology', 'scrum master',
        'project management', 'product management', 'user experience',
        'user interface', 'api development', 'rest api', 'graphql api',
        'database design', 'data analysis', 'business intelligence',
        'version control', 'continuous integration', 'continuous deployment',
        'test driven', 'object oriented', 'functional programming',
        'distributed systems', 'microservices architecture', 'serverless computing'
    ]

    # Tokenize single words
    def tokenize_words(text: str) -> List[str]:
        """Extract words, normalize to lowercase, filter stop words."""
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    # Extract multi-word terms (bigrams)
    def extract_bigrams(text: str) -> List[str]:
        """Extract common technical bigrams from text."""
        text_lower = text.lower()
        found_bigrams = []
        for bigram in common_bigrams:
            if bigram in text_lower:
                found_bigrams.append(bigram)
        return found_bigrams

    # Process resume
    resume_words = set(tokenize_words(resume))
    resume_bigrams = set(extract_bigrams(resume))

    # Process job description
    jd_words = tokenize_words(job_description)
    jd_bigrams = extract_bigrams(job_description)

    # Count frequency of words and bigrams in job description
    jd_word_freq = Counter(jd_words)
    jd_bigram_freq = Counter(jd_bigrams)

    # Identify high-value multi-word terms missing from resume
    missing_bigrams = [bg for bg in jd_bigram_freq.keys() if bg not in resume_bigrams]

    # Identify high-frequency single-word keywords from job description
    high_value_words = [word for word, count in jd_word_freq.most_common(30)]

    # Find missing single-word keywords (present in JD but not in resume)
    missing_words = [kw for kw in high_value_words if kw not in resume_words]

    # Combine bigrams and words, prioritizing bigrams
    missing = missing_bigrams + missing_words

    # Generate suggestions based on missing keywords
    suggestions = []

    if missing:
        # Separate technical keywords (longer words, higher frequency)
        technical_keywords = [kw for kw in missing if len(kw) > 4][:7]

        if technical_keywords:
            suggestions.append(
                f"Consider incorporating these key terms: {', '.join(technical_keywords[:5])}"
            )

        # Provide guidance based on gap severity
        if len(missing) > 10:
            suggestions.append(
                "Your resume appears to be missing many job-specific keywords. "
                "Review the job description and align your experience descriptions accordingly."
            )
        elif len(missing) > 5:
            suggestions.append(
                "Add relevant keywords from the job description to improve ATS matching."
            )

        suggestions.append(
            "Ensure your skills section includes technologies and methodologies mentioned in the job description."
        )
    else:
        suggestions.append(
            "Your resume appears well-aligned with the job description keywords."
        )

    # Limit missing keywords to top 15 for clarity
    missing_keywords = missing[:15]

    # TODO Phase 2: Advanced keyword extraction
    # - Use TF-IDF (Term Frequency-Inverse Document Frequency) for better keyword ranking
    # - Implement n-gram extraction (trigrams, 4-grams) for compound technical terms
    # - Apply stemming/lemmatization (e.g., "running" -> "run", "better" -> "good")
    # - Use industry-specific vocabulary lists (tech, healthcare, finance, etc.)

    # TODO Phase 2: Semantic similarity
    # - Use sentence embeddings (SentenceTransformers, OpenAI embeddings) for semantic matching
    # - Calculate cosine similarity between resume and job description sections
    # - Identify conceptually similar skills (e.g., "Java" and "Kotlin", "React" and "Vue")
    # - Provide synonym suggestions (e.g., "ML" for "machine learning")

    # TODO Phase 2: Context-aware analysis
    # - Analyze keyword placement (skills section vs. experience vs. summary)
    # - Detect keyword stuffing (excessive repetition)
    # - Validate keyword usage in context (not just presence)
    # - Score match quality (0-100) based on multiple factors

    return GapAnalysisResult(
        missing_keywords=missing_keywords,
        suggestions=suggestions
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "ATS Resume Builder API",
        "version": "1.0.0-phase1",
        "status": "operational",
        "phase": "Foundation and Compliance Backend"
    }


@app.post("/api/v1/analyze", response_model=GapAnalysisResult)
async def analyze_resume(resume_input: ResumeInput) -> GapAnalysisResult:
    """
    Analyze resume against job description with mandatory PII redaction.

    This endpoint implements the core Phase 1 workflow:
    1. Accept resume and job description inputs
    2. Apply mandatory PII redaction (security gate)
    3. Perform rudimentary gap analysis
    4. Return analysis results

    Args:
        resume_input: ResumeInput containing job description and resume text

    Returns:
        GapAnalysisResult with missing keywords and suggestions

    Raises:
        HTTPException: If input validation fails or processing errors occur

    Security:
        All text passes through redact_pii() before analysis to ensure
        no PII is exposed to downstream LLM processing (future phases).
    """
    try:
        # MANDATORY SECURITY GATE: Redact PII from both inputs
        # This ensures compliance before any external LLM interaction
        job_description_redacted = redact_pii(resume_input.job_description_text)
        resume_redacted = redact_pii(resume_input.resume_raw_text)

        # Perform gap analysis on redacted text
        analysis_result = rudimentary_gap_analysis(
            resume=resume_redacted,
            job_description=job_description_redacted
        )

        return analysis_result

    except Exception as e:
        # Log error for monitoring (in production, use proper logging)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume analysis: {str(e)}"
        )


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
