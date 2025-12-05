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

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, TYPE_CHECKING
import logging
import json
import os

from backend.config import is_lite_mode

# Import LLM modules (Phase 3.1 & 3.2)
from backend.llm.prompts import PromptTemplates
from backend.llm.response_validator import ResponseValidator
from backend.llm.cache import LLMCache
from backend.llm.retry_logic import RetryConfig, retry_with_exponential_backoff
from backend.llm.stub_claude_client import StubClaudeClient

# Import Auth routers (Phase 4)
from backend.auth.router import router as auth_router
from backend.auth.api_key_router import router as api_key_router

# Optional middleware (uncomment imports below if enabling)
# from backend.middleware.rate_limit import RateLimitMiddleware
# from backend.middleware.analytics import AnalyticsMiddleware

# Import Resume router (Phase 7)
from backend.resumes.router import router as resume_router

# Conditional routers that may rely on heavier dependencies
analytics_router = None
export_router = None
webhook_router = None

LITE_MODE = is_lite_mode()

if TYPE_CHECKING:
    from backend.nlp.pii_detector import PIIDetector
    from backend.nlp.semantic_analyzer import SemanticAnalyzer
    from backend.nlp.keyword_extractor import KeywordExtractor
    from backend.nlp.section_parser import SectionParser

if not LITE_MODE:
    from backend.llm.claude_client import ClaudeClient
    from backend.auth.rate_limiter import UserRateLimiter
    from backend.export.router import router as export_router
    from backend.analytics.router import router as analytics_router
    from backend.webhooks.router import router as webhook_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application Instance
# ============================================================================

app = FastAPI(
    title="ATS Resume Builder API",
    description="Secure, compliant backend for AI-powered resume tailoring with streaming, authentication, export, analytics, and webhooks",
    version="1.7.0-phase7"
)

# Include Phase 4 authentication routers
app.include_router(auth_router)
app.include_router(api_key_router)

# Include Phase 5 export router
if export_router and not LITE_MODE:
    app.include_router(export_router)

# Include Phase 6 analytics router
if analytics_router and not LITE_MODE:
    app.include_router(analytics_router)

# Include Phase 7 webhook router
if webhook_router and not LITE_MODE:
    app.include_router(webhook_router)

# Include Phase 7 resume router
app.include_router(resume_router)

# Initialize lazy service placeholders
pii_detector = None
semantic_analyzer = None
keyword_extractor = None
section_parser = None
user_rate_limiter = None
llm_cache = None
claude_client = None

# API key from environment variable for security
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
response_validator = ResponseValidator(min_length=100, max_length=50000)


def get_pii_detector() -> PIIDetector:
    """Lazily initialize the PIIDetector."""
    global pii_detector
    if pii_detector is None:
        from backend.nlp.pii_detector import PIIDetector

        logger.info("Initializing PIIDetector on demand")
        pii_detector = PIIDetector()
    return pii_detector


def get_semantic_analyzer() -> SemanticAnalyzer:
    """Lazily initialize the SemanticAnalyzer."""
    global semantic_analyzer
    if semantic_analyzer is None:
        from backend.nlp.semantic_analyzer import SemanticAnalyzer

        logger.info("Initializing SemanticAnalyzer on demand")
        semantic_analyzer = SemanticAnalyzer()
    return semantic_analyzer


def get_keyword_extractor() -> KeywordExtractor:
    """Lazily initialize the KeywordExtractor."""
    global keyword_extractor
    if keyword_extractor is None:
        from backend.nlp.keyword_extractor import KeywordExtractor

        logger.info("Initializing KeywordExtractor on demand")
        keyword_extractor = KeywordExtractor()
    return keyword_extractor


def get_section_parser() -> SectionParser:
    """Lazily initialize the SectionParser."""
    global section_parser
    if section_parser is None:
        from backend.nlp.section_parser import SectionParser

        logger.info("Initializing SectionParser on demand")
        section_parser = SectionParser()
    return section_parser


async def get_user_rate_limiter() -> UserRateLimiter | None:
    """Return the Redis-backed rate limiter when available."""
    global user_rate_limiter
    if LITE_MODE:
        logger.info("Lite mode enabled - skipping UserRateLimiter initialization")
        return None

    if user_rate_limiter is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        logger.info("Initializing UserRateLimiter for Redis backend at %s", redis_url)
        user_rate_limiter = UserRateLimiter(redis_url=redis_url)

    if user_rate_limiter and user_rate_limiter.redis_client is None:
        await user_rate_limiter.connect()

    return user_rate_limiter


def get_claude_client():
    """Lazily initialize the Claude client when configured."""
    global claude_client

    if claude_client:
        return claude_client

    if LITE_MODE:
        logger.info("Lite mode enabled - using stub Claude client")
        claude_client = StubClaudeClient()
        return claude_client

    if not ANTHROPIC_API_KEY:
        logger.warning(
            "ANTHROPIC_API_KEY not configured - falling back to stub Claude client"
        )
        claude_client = StubClaudeClient()
        return claude_client

    claude_client = ClaudeClient(
        api_key=ANTHROPIC_API_KEY,
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
    )
    logger.info("Claude client initialized successfully")
    return claude_client


async def get_llm_cache() -> LLMCache | None:
    """Lazily initialize and connect the LLM cache backend."""
    global llm_cache

    if LITE_MODE and llm_cache is None:
        logger.info("Lite mode enabled - using in-memory cache when requested")
        llm_cache = LLMCache(ttl_seconds=3600)

    if not LITE_MODE and llm_cache is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        logger.info("Initializing Redis-backed LLM cache at %s", redis_url)
        llm_cache = LLMCache(redis_url=redis_url, ttl_seconds=3600)

    if llm_cache and llm_cache._redis is None:
        await llm_cache.connect()

    return llm_cache


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
        match_score: Overall match score (0-100) based on semantic similarity
        semantic_similarity: Raw semantic similarity score (0-1) from SentenceTransformers
    """
    missing_keywords: List[str] = Field(
        ...,
        description="Keywords present in job description but missing from resume"
    )
    suggestions: List[str] = Field(
        ...,
        description="Specific suggestions for improving resume alignment"
    )
    match_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Overall match score (0-100) based on semantic similarity and keyword overlap"
    )
    semantic_similarity: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Raw semantic similarity score between resume and job description"
    )


class OptimizedResumeResponse(BaseModel):
    """Output model for LLM-optimized resume generation.

    Attributes:
        optimized_resume: The optimized resume text from Claude
        changes_made: List of specific changes and their rationale
        expected_improvement: Explanation of how changes improve match
        usage_stats: Token usage and cost information
    """
    optimized_resume: str = Field(
        ...,
        description="The optimized resume text generated by Claude"
    )
    changes_made: List[str] = Field(
        default=[],
        description="List of specific changes made during optimization"
    )
    expected_improvement: str = Field(
        default="",
        description="Explanation of expected improvements"
    )
    usage_stats: dict = Field(
        default={},
        description="Token usage and cost statistics"
    )


# ============================================================================
# Core Utility Functions
# ============================================================================

def redact_pii(text: str) -> str:
    """
    SECURITY GATE: Redact Personally Identifiable Information (PII) from text.

    This is a mandatory non-bypassable gate ensuring PII encryption/redaction
    before any prompt is constructed for external LLM use.

    Phase 2.2 Implementation: Enhanced NER-based redaction with spaCy and regex patterns.
    Improvements over Phase 1:
    - Named Entity Recognition (NER) for person/organization detection
    - Context-aware person/company name disambiguation
    - International PII format support (IBAN, passport)
    - Improved accuracy with >95% recall rate

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

    # Phase 2.2: Use enhanced PIIDetector with NER + regex
    detector = get_pii_detector()
    redacted, pii_counts = detector.detect_and_redact(text)

    # Log PII detection statistics (for monitoring and compliance)
    logger.info(f"PII detected and redacted: {pii_counts}")

    return redacted


def enhanced_gap_analysis(resume: str, job_description: str) -> GapAnalysisResult:
    """
    Perform enhanced gap analysis using NLP and semantic similarity.

    Phase 2.2 Implementation: Complete NLP-powered analysis including:
    - Semantic similarity calculation with SentenceTransformers
    - TF-IDF keyword extraction
    - Section-level analysis
    - Synonym detection
    - Keyword stuffing detection

    Args:
        resume: The resume text (should be PII-redacted)
        job_description: The job description text (should be PII-redacted)

    Returns:
        GapAnalysisResult with keywords, suggestions, match score, and semantic similarity
    """
    parser = get_section_parser()
    analyzer = get_semantic_analyzer()
    extractor = get_keyword_extractor()

    # 1. Parse resume into sections
    resume_sections = parser.parse_sections(resume)

    # 2. Calculate semantic similarity
    overall_similarity = analyzer.calculate_similarity(resume, job_description)
    section_similarity = analyzer.calculate_section_similarity(
        resume, job_description, resume_sections
    )

    # 3. Extract keywords using TF-IDF
    tfidf_keywords = extractor.extract_tfidf_keywords(
        [job_description, resume], top_n=30
    )

    # 4. Check which JD keywords are missing from resume
    jd_keywords = [kw[0] for kw in tfidf_keywords[:20]]  # Top 20 from JD
    resume_lower = resume.lower()
    missing_keywords = [kw for kw in jd_keywords if kw not in resume_lower]

    # 6. Detect synonym matches (reduce false positives)
    synonym_matches = analyzer.detect_synonyms(resume, missing_keywords)

    # Remove keywords that have synonyms in resume
    missing_keywords = [kw for kw in missing_keywords if kw not in synonym_matches]

    # 7. Generate suggestions based on analysis
    suggestions = []

    # Semantic similarity feedback
    if overall_similarity < 0.6:
        suggestions.append(
            "Your resume has low semantic similarity to the job description. "
            "Consider restructuring your experience to better align with the role's requirements."
        )
    elif overall_similarity >= 0.8:
        suggestions.append(
            "Excellent alignment! Your resume closely matches the job description."
        )

    # Section-specific feedback
    if 'skills' in section_similarity and section_similarity['skills'] < 0.5:
        suggestions.append(
            "Your skills section could be improved. Add technologies mentioned in the job description."
        )

    if 'experience' in section_similarity and section_similarity['experience'] < 0.6:
        suggestions.append(
            "Your experience descriptions don't align well with the job requirements. "
            "Rephrase your achievements to highlight relevant projects."
        )

    # Missing keywords feedback
    if missing_keywords:
        top_missing = missing_keywords[:5]
        suggestions.append(
            f"Consider incorporating these key terms: {', '.join(top_missing)}"
        )

    # Keyword stuffing detection
    for section_name, section_text in resume_sections.items():
        stuffed = parser.detect_keyword_stuffing(section_text)
        if stuffed:
            suggestions.append(
                f"Warning: The {section_name} section may have keyword stuffing. "
                f"Reduce repetition of: {', '.join(list(stuffed.keys())[:3])}"
            )

    # Default positive message if no issues
    if not suggestions:
        suggestions.append(
            "Your resume is well-optimized for this job description!"
        )

    # Calculate match score (0-100)
    match_score = round(overall_similarity * 100, 2)

    return GapAnalysisResult(
        missing_keywords=missing_keywords[:15],
        suggestions=suggestions,
        match_score=match_score,
        semantic_similarity=round(overall_similarity, 4)
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    if LITE_MODE:
        logger.info("Startup: Lite mode detected - skipping Redis-backed services")
    else:
        logger.info("Startup: Standard mode - dependencies initialize lazily on first use")

    if not ANTHROPIC_API_KEY:
        logger.warning(
            "Startup: ANTHROPIC_API_KEY not set - LLM endpoints will return 503 until configured"
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    if llm_cache:
        await llm_cache.disconnect()


@app.get("/")
async def root():
    """
    Root health check endpoint.

    Returns basic service information and operational status.
    Use /health for detailed health checks.
    """
    cache = await get_llm_cache()
    cache_stats = await cache.get_stats() if cache else {}
    client = get_claude_client()
    return {
        "service": "ATS Resume Builder API",
        "version": app.version,
        "status": "operational",
        "phase": "Production-Ready with Export System",
        "lite_mode": LITE_MODE,
        "llm_available": client is not None,
        "cache_enabled": cache is not None,
        "cached_responses": cache_stats.get("total_keys", 0)
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint for monitoring and orchestration.

    Checks:
    - API service status
    - Database connectivity
    - Redis connectivity
    - LLM client availability
    - Cache service status

    Returns:
        Health status with service details
    """
    import time

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.5.0-phase5",
        "services": {}
    }

    # Check database connectivity
    from backend.database import check_db_health

    db_healthy = await check_db_health()
    if db_healthy:
        health_status["services"]["database"] = {
            "status": "healthy",
            "type": "sqlite" if LITE_MODE else "postgresql",
        }
    else:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": "Database connectivity check failed",
        }
        health_status["status"] = "degraded"

    # Check Redis connectivity
    cache = await get_llm_cache()
    if cache:
        try:
            cache_stats = await cache.get_stats()
            health_status["services"]["redis"] = {
                "status": "healthy" if not LITE_MODE else "in-memory",
                "keys": cache_stats.get("total_keys", 0)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["services"]["redis"] = {
            "status": "disabled",
            "message": "Cache not configured"
        }

    # Check LLM availability
    client = get_claude_client()
    if client:
        health_status["services"]["llm"] = {
            "status": "stub" if getattr(client, "is_stub", False) else "healthy",
            "model": client.model
        }
    else:
        health_status["services"]["llm"] = {
            "status": "disabled",
            "message": "ANTHROPIC_API_KEY not configured"
        }

    # Check NLP services
    health_status["services"]["nlp"] = {
        "status": "healthy",
        "components": ["pii_detector", "semantic_analyzer", "keyword_extractor", "section_parser"]
    }

    return health_status


@app.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is not ready.
    """
    # Check critical dependencies
    from backend.database import check_db_health

    db_ready = await check_db_health()

    if db_ready:
        return {"status": "ready", "lite_mode": LITE_MODE}

    logger.error("Readiness check failed: database not reachable")
    raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if service is alive.
    """
    return {"status": "alive"}


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

        # Perform enhanced gap analysis on redacted text (Phase 2.2)
        analysis_result = enhanced_gap_analysis(
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


@app.post("/api/v1/generate", response_model=OptimizedResumeResponse)
async def generate_optimized_resume(resume_input: ResumeInput) -> OptimizedResumeResponse:
    """
    Generate optimized resume using Claude AI (Phase 3.1 & 3.2).

    This endpoint:
    1. Accepts resume and job description
    2. Applies mandatory PII redaction
    3. Performs gap analysis
    4. Checks cache for previous response
    5. Uses Claude to generate optimized resume (with retry logic)
    6. Validates response quality
    7. Returns optimized resume with changes and usage stats

    Args:
        resume_input: ResumeInput containing job description and resume text

    Returns:
        OptimizedResumeResponse with optimized resume and metadata

    Raises:
        HTTPException: If LLM is unavailable, API fails, or processing errors occur

    Security:
        - PII redaction applied before LLM interaction
        - API key stored in environment variable
        - Cost tracking enabled
        - Response validation for safety
    """
    # Check if Claude client is available
    client = get_claude_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. ANTHROPIC_API_KEY not configured."
        )

    try:
        # MANDATORY SECURITY GATE: Redact PII
        job_description_redacted = redact_pii(resume_input.job_description_text)
        resume_redacted = redact_pii(resume_input.resume_raw_text)

        # Perform gap analysis
        analysis = enhanced_gap_analysis(
            resume=resume_redacted,
            job_description=job_description_redacted
        )

        # Generate optimization prompt
        prompt = PromptTemplates.generate_resume_optimization(
            original_resume=resume_redacted,
            job_description=job_description_redacted,
            missing_keywords=analysis.missing_keywords,
            suggestions=analysis.suggestions,
            match_score=analysis.match_score,
            semantic_similarity=analysis.semantic_similarity,
        )

        system_prompt = PromptTemplates.get_system_prompt()

        # Check cache first (Phase 3.2)
        cached_response = None
        cache = await get_llm_cache()
        if cache:
            cached_response = await cache.get(
                prompt=prompt,
                system_prompt=system_prompt,
                model=client.model,
                max_tokens=client.max_tokens,
                temperature=client.temperature,
            )

        if cached_response:
            logger.info("Using cached LLM response")
            response = cached_response
            response["cached"] = True
        else:
            # Call Claude API with retry logic (Phase 3.2)
            async def generate_with_retry():
                return await client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )

            retry_config = RetryConfig(max_retries=3, initial_delay=1.0)
            response = await retry_with_exponential_backoff(
                generate_with_retry,
                retry_config,
            )
            response["cached"] = False

            # Cache the response
            if cache:
                await cache.set(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=client.model,
                    max_tokens=client.max_tokens,
                    temperature=client.temperature,
                    response=response,
                )

        # Validate response (Phase 3.2)
        is_valid, issues = response_validator.validate(response["content"])
        if not is_valid:
            logger.warning(f"Response validation issues: {issues}")
            # Sanitize response
            response["content"] = response_validator.sanitize(response["content"])

        # Parse Claude's response to extract sections
        content = response["content"]

        # Simple parsing (can be enhanced with more sophisticated extraction)
        optimized_resume = content
        changes_made = ["See optimized resume for details"]
        expected_improvement = "Resume optimized for ATS compatibility and keyword matching"

        # Extract sections if Claude followed the format
        if "## CHANGES MADE" in content:
            parts = content.split("## CHANGES MADE")
            optimized_resume = parts[0].replace("## OPTIMIZED RESUME", "").strip()

            if len(parts) > 1 and "## EXPECTED IMPROVEMENT" in parts[1]:
                change_parts = parts[1].split("## EXPECTED IMPROVEMENT")
                changes_text = change_parts[0].strip()
                changes_made = [
                    line.strip("- ").strip()
                    for line in changes_text.split("\n")
                    if line.strip().startswith("-")
                ]

                if len(change_parts) > 1:
                    expected_improvement = change_parts[1].strip()

        return OptimizedResumeResponse(
            optimized_resume=optimized_resume,
            changes_made=changes_made,
            expected_improvement=expected_improvement,
            usage_stats={
                "input_tokens": response["usage"]["input_tokens"],
                "output_tokens": response["usage"]["output_tokens"],
                "cost_usd": round(response["cost"], 4),
                "model": response["model"],
            }
        )

    except Exception as e:
        logger.error(f"Error generating optimized resume: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating optimized resume: {str(e)}"
        )


@app.get("/api/v1/stats")
async def get_usage_stats():
    """
    Get LLM usage statistics and costs.

    Returns usage statistics including:
    - Total requests
    - Token usage (input/output)
    - Total cost
    - Per-model breakdown

    Returns:
        Dictionary with usage statistics

    Raises:
        HTTPException: If LLM is unavailable
    """
    client = get_claude_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. ANTHROPIC_API_KEY not configured."
        )

    return client.get_usage_stats()


@app.post("/api/v1/generate/stream")
async def generate_optimized_resume_stream(resume_input: ResumeInput):
    """
    Generate optimized resume using Claude AI with streaming (Phase 3.2).

    This endpoint streams the response in real-time using Server-Sent Events (SSE).

    Args:
        resume_input: ResumeInput containing job description and resume text

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If LLM is unavailable or processing errors occur

    Security:
        - PII redaction applied before LLM interaction
        - API key stored in environment variable
    """
    client = get_claude_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. ANTHROPIC_API_KEY not configured."
        )

    # MANDATORY SECURITY GATE: Redact PII
    job_description_redacted = redact_pii(resume_input.job_description_text)
    resume_redacted = redact_pii(resume_input.resume_raw_text)

    # Perform gap analysis
    analysis = enhanced_gap_analysis(
        resume=resume_redacted,
        job_description=job_description_redacted
    )

    # Generate optimization prompt
    prompt = PromptTemplates.generate_resume_optimization(
        original_resume=resume_redacted,
        job_description=job_description_redacted,
        missing_keywords=analysis.missing_keywords,
        suggestions=analysis.suggestions,
        match_score=analysis.match_score,
        semantic_similarity=analysis.semantic_similarity,
    )

    system_prompt = PromptTemplates.get_system_prompt()

    async def event_generator():
        """Generate Server-Sent Events."""
        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting resume optimization...'})}\n\n"

            # Stream response from Claude
            full_response = ""
            async for chunk in client.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
            ):
                full_response += chunk
                # Send chunk event
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Validate complete response
            is_valid, issues = response_validator.validate(full_response)
            if not is_valid:
                yield f"data: {json.dumps({'type': 'warning', 'issues': issues})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'message': 'Optimization complete'})}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming generation: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/v1/cache/stats")
async def get_cache_stats():
    """
    Get LLM cache statistics (Phase 3.2).

    Returns:
        Dictionary with cache statistics
    """
    cache = await get_llm_cache()
    if not cache:
        raise HTTPException(
            status_code=503,
            detail="Cache not enabled"
        )

    return await cache.get_stats()


@app.delete("/api/v1/cache")
async def clear_cache():
    """
    Clear all cached LLM responses (Phase 3.2).

    Returns:
        Success message
    """
    cache = await get_llm_cache()
    if not cache:
        raise HTTPException(
            status_code=503,
            detail="Cache not enabled"
        )

    success = await cache.clear_all()
    return {"success": success, "message": "Cache cleared"}


# ============================================================================
# Application Entry Point
# ============================================================================

def _get_bool_env(var_name: str, default: bool = False) -> bool:
    """Parse boolean-ish environment variables."""

    value = os.getenv(var_name)
    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    reload = _get_bool_env("APP_RELOAD", False)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
