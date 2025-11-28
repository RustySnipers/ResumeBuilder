"""
AI-Powered ATS-Friendly Resume Builder - Backend API (Phase 1: Foundation)

This module implements the core FastAPI backend with mandatory PII redaction
and rudimentary gap analysis for resume optimization.

Technical Stack:
- Python 3.10+
- FastAPI for REST API
- Pydantic for data validation and serialization
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

    Phase 1 Implementation: Stub function with placeholder redaction logic.
    Future phases will implement comprehensive PII detection using:
    - Named Entity Recognition (NER) models
    - Regular expression patterns for emails, phones, SSNs, addresses
    - Integration with PII detection services

    Args:
        text: Raw text potentially containing PII

    Returns:
        Text with PII replaced by <PII_REDACTED> placeholders

    Examples:
        >>> redact_pii("Contact: john.doe@email.com, (555) 123-4567")
        "Contact: <PII_REDACTED>, <PII_REDACTED>"
    """
    if not text:
        return text

    # Phase 1: Basic pattern-based redaction
    redacted = text

    # Redact email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    redacted = re.sub(email_pattern, '<PII_REDACTED_EMAIL>', redacted)

    # Redact phone numbers (multiple formats)
    phone_patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890, 123-456-7890
        r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
    ]
    for pattern in phone_patterns:
        redacted = re.sub(pattern, '<PII_REDACTED_PHONE>', redacted)

    # Redact SSN-like patterns
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    redacted = re.sub(ssn_pattern, '<PII_REDACTED_SSN>', redacted)

    # Redact street addresses (basic pattern)
    address_pattern = r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b'
    redacted = re.sub(address_pattern, '<PII_REDACTED_ADDRESS>', redacted, flags=re.IGNORECASE)

    # Note: Future implementation will include:
    # - NER-based person name detection
    # - Geographic location redaction
    # - Credit card numbers
    # - Date of birth patterns
    # - Government ID numbers

    return redacted


def rudimentary_gap_analysis(resume: str, job_description: str) -> GapAnalysisResult:
    """
    Perform basic keyword gap analysis between resume and job description.

    This Phase 1 implementation uses simple tokenization and frequency analysis
    to identify high-value keywords from the job description that are missing
    from the resume.

    Args:
        resume: The resume text (should be PII-redacted)
        job_description: The job description text (should be PII-redacted)

    Returns:
        GapAnalysisResult containing missing keywords and suggestions

    Algorithm:
        1. Tokenize both texts into words
        2. Normalize to lowercase and filter common stop words
        3. Identify frequent keywords in job description (top candidates)
        4. Check which high-frequency keywords are absent from resume
        5. Generate actionable suggestions based on gaps
    """
    # Common stop words to filter out (basic set)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how'
    }

    # Tokenize and normalize
    def tokenize(text: str) -> List[str]:
        """Extract words, normalize to lowercase, filter stop words."""
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    resume_tokens = set(tokenize(resume))
    jd_tokens = tokenize(job_description)

    # Count frequency of tokens in job description
    jd_freq = Counter(jd_tokens)

    # Identify high-frequency keywords (top 20) from job description
    high_value_keywords = [word for word, count in jd_freq.most_common(30)]

    # Find missing keywords (present in JD but not in resume)
    missing = [kw for kw in high_value_keywords if kw not in resume_tokens]

    # Generate suggestions based on missing keywords
    suggestions = []

    if missing:
        # Group keywords by potential category (heuristic)
        technical_keywords = [kw for kw in missing if len(kw) > 4 and jd_freq[kw] >= 2]

        if technical_keywords[:5]:
            suggestions.append(
                f"Consider incorporating these key terms: {', '.join(technical_keywords[:5])}"
            )

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
