"""
Prompt Templates - Phase 3.1

Engineered prompts for resume optimization using Claude.
"""

from typing import Dict, List, Optional


class PromptTemplates:
    """
    Prompt engineering templates for resume optimization.

    Templates use Claude's best practices:
    - Clear instructions and context
    - Structured output formatting
    - Examples for consistency
    - Explicit constraints
    """

    @staticmethod
    def get_system_prompt() -> str:
        """
        Get system prompt for resume optimization.

        Returns:
            System prompt establishing Claude's role and constraints
        """
        return """You are an expert ATS (Applicant Tracking System) resume optimization specialist with deep knowledge of:
- Resume best practices and formatting
- ATS keyword optimization
- Industry-specific terminology
- Achievement-focused writing
- Quantifiable metrics and impact statements

Your role is to optimize resumes for maximum ATS compatibility and human appeal while:
1. Maintaining truthfulness - never fabricate experiences or skills
2. Preserving the candidate's authentic voice
3. Ensuring ATS-friendly formatting (no tables, minimal special characters)
4. Highlighting quantifiable achievements with metrics
5. Tailoring content to match job description requirements

Always output in clean, professional English with proper grammar and formatting."""

    @staticmethod
    def generate_resume_optimization(
        original_resume: str,
        job_description: str,
        missing_keywords: List[str],
        suggestions: List[str],
        match_score: float,
        semantic_similarity: float,
    ) -> str:
        """
        Generate prompt for resume optimization.

        Args:
            original_resume: Original resume text
            job_description: Target job description
            missing_keywords: Keywords missing from resume
            suggestions: Improvement suggestions from analysis
            match_score: Match score (0-100)
            semantic_similarity: Semantic similarity (0-1)

        Returns:
            Formatted prompt for Claude
        """
        return f"""I need you to optimize the following resume for the target job description.

# ORIGINAL RESUME
{original_resume}

# TARGET JOB DESCRIPTION
{job_description}

# ANALYSIS RESULTS
- Current Match Score: {match_score:.1f}%
- Semantic Similarity: {semantic_similarity:.2f}
- Missing Keywords: {', '.join(missing_keywords)}

# IMPROVEMENT SUGGESTIONS
{chr(10).join(f'- {s}' for s in suggestions)}

# OPTIMIZATION TASK
Please optimize this resume to better match the job description while:

1. **Incorporating Missing Keywords**: Naturally integrate these keywords where truthful and relevant:
   {', '.join(missing_keywords)}

2. **Highlighting Relevant Experience**: Emphasize experiences and skills that align with job requirements

3. **Quantifying Achievements**: Add or enhance metrics (percentages, numbers, timeframes) where possible

4. **ATS Optimization**: Ensure formatting is ATS-friendly (no tables, clear sections, standard fonts)

5. **Maintaining Authenticity**: Do NOT fabricate experiences, skills, or achievements

# OUTPUT FORMAT
Provide the optimized resume in the following structure:

## OPTIMIZED RESUME
[Full optimized resume text with clear sections]

## CHANGES MADE
[Bulleted list of specific changes and their rationale]

## EXPECTED IMPROVEMENT
[Brief explanation of how these changes improve ATS match and human appeal]

Begin with the optimized resume:"""

    @staticmethod
    def generate_cover_letter(
        resume: str,
        job_description: str,
        company_name: str,
        position_title: str,
    ) -> str:
        """
        Generate prompt for cover letter creation.

        Args:
            resume: Resume text
            job_description: Job description
            company_name: Company name
            position_title: Position title

        Returns:
            Formatted prompt for Claude
        """
        return f"""Generate a compelling cover letter for the following job application.

# RESUME
{resume}

# JOB DETAILS
Company: {company_name}
Position: {position_title}

Job Description:
{job_description}

# COVER LETTER REQUIREMENTS
Create a professional cover letter that:

1. **Opening**: Strong hook that shows genuine interest and alignment
2. **Body**: 2-3 paragraphs highlighting:
   - Relevant experience from resume that matches job requirements
   - Specific achievements with quantifiable impact
   - Skills that address the company's needs
3. **Closing**: Clear call to action expressing enthusiasm
4. **Length**: Keep to 3-4 short paragraphs (under 300 words)
5. **Tone**: Professional yet personable, confident but not arrogant

# OUTPUT FORMAT
Provide the cover letter in standard business format:

[Cover letter text]

Begin:"""

    @staticmethod
    def analyze_job_description(job_description: str) -> str:
        """
        Generate prompt for job description analysis.

        Args:
            job_description: Job description text

        Returns:
            Formatted prompt for Claude
        """
        return f"""Analyze the following job description and extract key information.

# JOB DESCRIPTION
{job_description}

# ANALYSIS TASK
Please analyze this job description and provide:

1. **Required Skills**: List of must-have technical and soft skills
2. **Preferred Skills**: Nice-to-have skills mentioned
3. **Key Responsibilities**: Main duties and expectations
4. **Required Experience**: Years and type of experience required
5. **Education Requirements**: Degree or certification requirements
6. **Important Keywords**: Keywords likely used for ATS filtering
7. **Company Culture Indicators**: Insights about work environment and values
8. **Red Flags**: Any concerning aspects (unrealistic expectations, vague requirements)

# OUTPUT FORMAT
Provide structured analysis in the following format:

## Required Skills
- [skill 1]
- [skill 2]

## Preferred Skills
- [skill 1]

## Key Responsibilities
- [responsibility 1]

## Required Experience
[experience description]

## Education Requirements
[education requirements]

## Important Keywords
[comma-separated keywords]

## Company Culture Indicators
[culture insights]

## Red Flags
[any concerns or none]

Begin analysis:"""

    @staticmethod
    def tailor_bullet_points(
        experience_bullets: List[str],
        job_requirements: List[str],
    ) -> str:
        """
        Generate prompt for tailoring experience bullets.

        Args:
            experience_bullets: Current bullet points
            job_requirements: Job requirements to match

        Returns:
            Formatted prompt for Claude
        """
        bullets_text = '\n'.join(f'- {b}' for b in experience_bullets)
        requirements_text = '\n'.join(f'- {r}' for r in job_requirements)

        return f"""Optimize these resume bullet points to better match the job requirements.

# CURRENT BULLET POINTS
{bullets_text}

# JOB REQUIREMENTS
{requirements_text}

# OPTIMIZATION TASK
Rewrite each bullet point to:

1. **Match Requirements**: Align language with job requirements
2. **Use Action Verbs**: Start with strong action verbs (Led, Developed, Implemented, etc.)
3. **Quantify Impact**: Add metrics where possible (percentages, numbers, timeframes)
4. **Highlight Results**: Focus on achievements and outcomes, not just duties
5. **Incorporate Keywords**: Naturally include relevant keywords from requirements

# OUTPUT FORMAT
For each bullet point, provide:

Original: [original bullet]
Optimized: [optimized bullet]
Rationale: [brief explanation of changes]

Begin:"""

    @staticmethod
    def extract_achievements(experience_text: str) -> str:
        """
        Generate prompt for extracting achievements from experience.

        Args:
            experience_text: Raw experience description

        Returns:
            Formatted prompt for Claude
        """
        return f"""Extract and enhance achievements from this experience description.

# EXPERIENCE DESCRIPTION
{experience_text}

# TASK
Identify and rewrite achievements as strong bullet points that:

1. **Start with Action Verbs**: Led, Developed, Implemented, Achieved, etc.
2. **Quantify Results**: Include specific metrics, percentages, or numbers
3. **Show Impact**: Demonstrate business value and outcomes
4. **Are Concise**: 1-2 lines maximum per bullet
5. **Follow STAR Format**: Situation, Task, Action, Result (implicitly)

# OUTPUT FORMAT
Provide 3-5 achievement bullets in this format:

- [Action verb] [what you did] resulting in [quantifiable outcome]
- [Action verb] [what you did] resulting in [quantifiable outcome]

If metrics aren't available, focus on scope, scale, or qualitative impact.

Begin:"""

    @staticmethod
    def validate_resume_quality(resume: str) -> str:
        """
        Generate prompt for resume quality validation.

        Args:
            resume: Resume text to validate

        Returns:
            Formatted prompt for Claude
        """
        return f"""Review this resume for quality and ATS compatibility.

# RESUME
{resume}

# VALIDATION TASK
Evaluate the resume on these criteria:

1. **ATS Compatibility** (0-10):
   - Clean formatting (no tables, images)
   - Standard section headings
   - Keyword optimization
   - File format considerations

2. **Content Quality** (0-10):
   - Achievement-focused bullets
   - Quantifiable metrics
   - Relevant keywords
   - Clear value proposition

3. **Writing Quality** (0-10):
   - Grammar and spelling
   - Consistency
   - Conciseness
   - Professional tone

4. **Structure** (0-10):
   - Logical flow
   - Appropriate length
   - Clear sections
   - Visual hierarchy

# OUTPUT FORMAT
Provide structured feedback:

## Scores
- ATS Compatibility: [score]/10
- Content Quality: [score]/10
- Writing Quality: [score]/10
- Structure: [score]/10
- Overall: [average]/10

## Strengths
- [strength 1]
- [strength 2]

## Areas for Improvement
- [improvement 1]
- [improvement 2]

## Specific Recommendations
1. [actionable recommendation]
2. [actionable recommendation]

Begin evaluation:"""
