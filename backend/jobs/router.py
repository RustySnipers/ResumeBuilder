"""
Job Analysis Router.

Endpoints for analyzing resumes against job descriptions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from backend.database import get_db as get_session
from backend.auth.guest import get_guest_user
from backend.models.user import User
from backend.repositories.resume_repository import ResumeRepository
from backend.analysis.service import AnalysisService
from backend.scraping.service import ScraperService
from backend.llm.dependencies import get_llm_client
from backend.llm.local_llm_client import LocalLLMClient
from backend.config import get_settings

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])

class JobAnalysisRequest(BaseModel):
    resume_id: str
    job_description: Optional[str] = None
    job_url: Optional[str] = None

class JobAnalysisResponse(BaseModel):
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    analysis: Optional[Dict[str, Any]] = None
    scraped_data: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    scraped_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class OptimizeRequest(BaseModel):
    resume_id: str
    job_description: str

class OptimizeResponse(BaseModel):
    new_resume_id: str
    message: str
    version: int

@router.post("/analyze", response_model=JobAnalysisResponse)
async def analyze_job_fit(
    request: JobAnalysisRequest,
    current_user: User = Depends(get_guest_user),
    session: AsyncSession = Depends(get_session),
    llm_client: LocalLLMClient = Depends(get_llm_client),
):
    """
    Analyze resume fit for a specific job.
    
    Accepts matched resume_id and either job_description text or job_url.
    Returns ATS score, keyword analysis, and LLM usage if available.
    """
    resume_repo = ResumeRepository(session)
    scraper_service = ScraperService()
    settings = get_settings()
    analysis_service = AnalysisService(settings, llm_client)
    
    # 1. Fetch Resume
    try:
        resume_uuid = uuid.UUID(request.resume_id)
        resume = await resume_repo.get_by_id(resume_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID")
        
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    # 2. Get Job Description
    job_text = request.job_description or ""
    scraped_data = None
    
    if request.job_url:
        scraped_result = await scraper_service.scrape_url(request.job_url)
        if scraped_result.get("content"):
            job_text = scraped_result["content"]
            scraped_data = {
                "title": scraped_result.get("title"),
                "url": request.job_url
            }
        elif scraped_result.get("error"):
            # If scraping failed, but we have text, continue with warning
            # If no text, fail
            if not job_text:
                raise HTTPException(status_code=400, detail=f"Failed to scrape URL: {scraped_result['error']}")
    
    if not job_text:
        raise HTTPException(status_code=400, detail="Job description or valid URL required")

    # 3. Perform Analysis
    # ATS Score
    ats_result = analysis_service.calculate_ats_score(resume.raw_text, job_text)
    
    # LLM Analysis
    llm_result = await analysis_service.analyze_resume_with_llm(resume.raw_text, job_text)
    
    return JobAnalysisResponse(
        ats_score=ats_result.get("score", 0),
        matched_keywords=ats_result.get("matched_keywords", []),
        missing_keywords=ats_result.get("missing_keywords", []),
        analysis=llm_result,
        scraped_data=scraped_data,
        error=ats_result.get("error")
    )

from fastapi.responses import StreamingResponse
import json
import asyncio

@router.post("/analyze/stream")
async def analyze_job_fit_stream(
    request: JobAnalysisRequest,
    current_user: User = Depends(get_guest_user),
    session: AsyncSession = Depends(get_session),
    llm_client: LocalLLMClient = Depends(get_llm_client),
):
    """
    Stream analysis of resume fit for a specific job.
    """
    resume_repo = ResumeRepository(session)
    scraper_service = ScraperService()
    settings = get_settings()
    analysis_service = AnalysisService(settings, llm_client)
    
    # 1. Fetch Resume
    try:
        resume_uuid = uuid.UUID(request.resume_id)
        resume = await resume_repo.get_by_id(resume_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID")
        
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    # Generator for SSE
    async def event_generator():
        # A. Status Update
        yield '{"type": "status", "data": "Checking Job Description..."}\n\n'
        await asyncio.sleep(0.1)

        # 2. Get Job Description
        job_text = request.job_description or ""
        
        if request.job_url:
            yield '{"type": "status", "data": "Scraping Job URL..."}\n\n'
            scraped_result = await scraper_service.scrape_url(request.job_url)
            if scraped_result.get("content"):
                job_text = scraped_result["content"]
            elif scraped_result.get("error") and not job_text:
                yield f'{{"type": "error", "data": "Scraping failed: {scraped_result["error"]}"}}\n\n'
                return

        if not job_text:
            yield '{"type": "error", "data": "No job description found."}\n\n'
            return

        # 3. ATS Score
        yield '{"type": "status", "data": "Calculating ATS Score..."}\n\n'
        ats_result = analysis_service.calculate_ats_score(resume.raw_text, job_text)
        
        # Send ATS Score First
        ats_data = json.dumps(ats_result)
        yield f'{{"type": "ats_result", "data": {ats_data}}}\n\n'
        await asyncio.sleep(0.5) # Let UI transition

        # 4. LLM Stream
        yield '{"type": "status", "data": "AI Analyst Thinking..."}\n\n'
        async for chunk in analysis_service.analyze_resume_stream(resume.raw_text, job_text):
            yield chunk + "\n\n"
            
        yield '{"type": "done", "data": "Analysis Complete"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    request: OptimizeRequest,
    current_user: User = Depends(get_guest_user),
    session: AsyncSession = Depends(get_session),
    llm_client: LocalLLMClient = Depends(get_llm_client),
):
    """
    Optimize resume content to match job description and SAVE as new version.
    """
    resume_repo = ResumeRepository(session)
    settings = get_settings()
    analysis_service = AnalysisService(settings, llm_client)
    
    # 1. Fetch Resume
    try:
        resume_uuid = uuid.UUID(request.resume_id)
        resume = await resume_repo.get_by_id(resume_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID")
        
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    # 2. Optimize Content (Rewriting)
    optimized_text = await analysis_service.optimize_resume_full(
        current_resume=resume.raw_text,
        job_description=request.job_description
    )
    
    # 3. Structure Content (for Export)
    parsed_json = await analysis_service.structure_resume_text(optimized_text)
    
    # 4. Save as New Version
    from backend.models.resume import Resume
    
    new_version_num = await resume_repo.get_latest_version(current_user.id, resume.title)
    # If title changed (e.g. "Optimized"), we might start at 1, but let's keep it simple.
    
    new_resume = Resume(
        user_id=current_user.id,
        title=f"Optimized for Job", # Or keep original title + V2
        raw_text=optimized_text,
        parsed_data=parsed_json,
        version=new_version_num + 1,
        redacted_text=optimized_text # Assume redacted for now or run detector
    )
    
    session.add(new_resume)
    await session.flush()
    await session.commit()
    
    return OptimizeResponse(
        new_resume_id=str(new_resume.id),
        message="Resume optimized and saved successfully.",
        version=new_resume.version
    )
