"""
LLM Prompt Template for Resume Tailoring (Phase 3 Integration)

This module contains the structured prompt template for instructing
Claude Sonnet/Opus to perform ATS-friendly resume tailoring.

The prompt follows best practices in prompt engineering:
- Clear instruction and role definition
- Comprehensive context (job description, resume, gap analysis)
- Explicit output format constraints
- Safety guardrails against hallucination
"""

# ============================================================================
# LLM Prompt Template for Resume Tailoring
# ============================================================================

RESUME_TAILORING_PROMPT_TEMPLATE = """You are an expert resume writer with deep knowledge of Applicant Tracking Systems (ATS) and professional resume formatting. Your task is to transform the original resume below to better match the job description, while keeping it professional, truthful, and ATS-friendly.

====================
JOB DESCRIPTION
====================
{JOB_DESCRIPTION_REDACTED}

====================
ORIGINAL RESUME
====================
{RESUME_TEXT_REDACTED}

====================
GAP ANALYSIS
====================
Our system has identified the following gaps between the resume and job description:

{GAP_ANALYSIS_JSON}

====================
INSTRUCTIONS
====================

Your task is to create an optimized version of the resume that:

1. **Alignment**: Better aligns with the job description by incorporating relevant keywords and phrases naturally
2. **ATS Optimization**: Ensures the resume is ATS-friendly and will pass automated screening systems
3. **Truthfulness**: Maintains complete factual accuracy - all experiences, dates, and achievements must remain truthful
4. **Professional Quality**: Uses strong action verbs, quantifiable achievements, and clear, concise language

====================
CRITICAL CONSTRAINTS
====================

**TRUTHFULNESS AND ACCURACY:**
- DO NOT fabricate any new experience, job titles, dates, employers, or achievements
- DO NOT add skills or technologies the candidate has not actually used
- ONLY rephrase, reorganize, or emphasize existing content from the original resume
- If you are unsure about any factual information or need clarification, clearly state "I don't know" or "[CLARIFICATION NEEDED]" rather than making assumptions
- Retain all original time periods, company names, and job titles exactly as provided

**OUTPUT FORMAT (ATS-FRIENDLY):**
- Use a clean, simple format with clear section headers
- Required sections: Professional Summary (or Objective), Experience, Education, Skills
- Optional sections (if present in original): Certifications, Projects, Awards
- Use bullet points for experience descriptions and achievements
- DO NOT use tables, text boxes, headers/footers, images, or complex graphics
- DO NOT use fancy fonts, colors, or special characters that may confuse ATS systems
- Use standard section names that ATS systems recognize
- Use simple, consistent formatting throughout

**KEYWORD OPTIMIZATION:**
- Naturally incorporate missing keywords from the gap analysis where truthful and relevant
- Match terminology from the job description (e.g., if JD says "customer success," use that instead of "client support")
- Ensure technical skills mentioned in the job description appear in the Skills section (only if candidate actually has them)
- Use industry-standard terms and avoid obscure jargon

**EXPERIENCE DESCRIPTIONS:**
- Begin each bullet point with strong action verbs (e.g., "Developed," "Implemented," "Led," "Optimized")
- Quantify achievements where possible (e.g., "Increased sales by 25%," "Managed team of 5")
- Focus on results and impact, not just responsibilities
- Highlight experiences most relevant to the target job description

====================
OUTPUT REQUIREMENTS
====================

Provide the tailored resume in clean, ATS-friendly format with:
- Clear section headers in ALL CAPS or Title Case
- Consistent bullet point style (using - or • )
- No special formatting codes or HTML
- Simple, readable structure
- All original factual information preserved

If you identify any gaps that cannot be addressed without fabricating information, include a brief note at the end: "RECOMMENDATIONS FOR CANDIDATE: [specific truthful actions they could take to strengthen their application]"

Begin your response with the tailored resume now:
"""


# ============================================================================
# Helper Function for Prompt Construction
# ============================================================================

def construct_resume_tailoring_prompt(
    job_description_redacted: str,
    resume_text_redacted: str,
    gap_analysis_json: str
) -> str:
    """
    Construct the full LLM prompt for resume tailoring.

    This function will be used in Phase 3 when integrating with
    Claude Sonnet/Opus API for actual resume generation.

    Args:
        job_description_redacted: PII-redacted job description text
        resume_text_redacted: PII-redacted original resume text
        gap_analysis_json: JSON string containing gap analysis results
                          (from GapAnalysisResult.model_dump_json())

    Returns:
        Complete prompt string ready for LLM API call

    Example:
        >>> from main import GapAnalysisResult
        >>> gap_result = GapAnalysisResult(
        ...     missing_keywords=["python", "fastapi"],
        ...     suggestions=["Add Python to skills section"]
        ... )
        >>> prompt = construct_resume_tailoring_prompt(
        ...     job_description_redacted="...",
        ...     resume_text_redacted="...",
        ...     gap_analysis_json=gap_result.model_dump_json(indent=2)
        ... )
        >>> # Send prompt to Claude API
    """
    return RESUME_TAILORING_PROMPT_TEMPLATE.format(
        JOB_DESCRIPTION_REDACTED=job_description_redacted,
        RESUME_TEXT_REDACTED=resume_text_redacted,
        GAP_ANALYSIS_JSON=gap_analysis_json
    )


# ============================================================================
# Usage Example (for Phase 3 Integration)
# ============================================================================

if __name__ == "__main__":
    # Example demonstrating how this will be used in Phase 3
    from main import GapAnalysisResult
    import json

    # Simulated data (in production, this comes from the API)
    example_jd_redacted = """
    We are seeking a Senior Python Developer with expertise in FastAPI
    and cloud technologies. Requirements include:
    - 5+ years Python development
    - Experience with FastAPI, SQLAlchemy
    - AWS or Azure cloud experience
    - Strong API design skills
    """

    example_resume_redacted = """
    John Doe
    <PII_REDACTED_EMAIL> | <PII_REDACTED_PHONE>

    EXPERIENCE
    Software Engineer | Tech Corp | 2020-Present
    - Developed web applications using Django
    - Worked with PostgreSQL databases
    - Deployed applications to cloud infrastructure

    EDUCATION
    BS Computer Science | University Name | 2019

    SKILLS
    Python, Django, PostgreSQL, Git
    """

    example_gap = GapAnalysisResult(
        missing_keywords=["fastapi", "sqlalchemy", "aws", "azure", "api"],
        suggestions=[
            "Consider incorporating these key terms: fastapi, sqlalchemy, aws, azure, api",
            "Ensure your skills section includes technologies mentioned in the job description"
        ]
    )

    # Construct the prompt
    prompt = construct_resume_tailoring_prompt(
        job_description_redacted=example_jd_redacted,
        resume_text_redacted=example_resume_redacted,
        gap_analysis_json=example_gap.model_dump_json(indent=2)
    )

    print("=" * 80)
    print("CONSTRUCTED PROMPT FOR CLAUDE API (Phase 3)")
    print("=" * 80)
    print(prompt)
    print("\n" + "=" * 80)
    print("Next Step: Send this prompt to Claude Sonnet API and receive tailored resume")
    print("=" * 80)
