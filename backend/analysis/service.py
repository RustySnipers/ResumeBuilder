"""
Analysis Service.

Logic for ATS scoring and LLM-based resume analysis.
"""

import logging
import json
from typing import Dict, Any, List
import re
from collections import Counter

from backend.llm.local_llm_client import LocalLLMClient
from backend.config import get_settings, Settings

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for resume analysis and scoring."""

    def __init__(self, settings: Settings, llm_client: LocalLLMClient):
        """
        Initialize Analysis Service with dependencies.
        """
        self.settings = settings
        self.llm_client = llm_client

    def calculate_ats_score(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Calculate a simple ATS match score based on keyword overlap.
        
        Args:
            resume_text: Text content of resume
            job_description: Text content of job description
            
        Returns:
            Dictionary with score, missing keywords, etc.
        """
        try:
            from rank_bm25 import BM25Okapi
            from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
        except ImportError:
            logger.warning("Analysis dependencies (rank_bm25, sklearn) missing.")
            return {"score": 0, "error": "Dependencies missing"}

        def tokenize(text):
            # Simple tokenization: lowercase, remove punctuation, remove stop words
            text = text.lower()
            text = re.sub(r'[^\w\s]', '', text)
            tokens = text.split()
            return [t for t in tokens if t not in ENGLISH_STOP_WORDS]

        resume_tokens = tokenize(resume_text)
        job_tokens = tokenize(job_description)
        
        if not job_tokens:
            return {"score": 0, "missing_keywords": []}

        # Calculate keyword presence
        resume_counter = Counter(resume_tokens)
        job_counter = Counter(job_tokens)
        
        common_keywords = []
        missing_keywords = []
        
        # Consider top 20 most frequent significant words in job description as keywords
        top_job_keywords = [word for word, count in job_counter.most_common(20)]
        
        match_count = 0
        for keyword in top_job_keywords:
            if keyword in resume_counter:
                common_keywords.append(keyword)
                match_count += 1
            else:
                missing_keywords.append(keyword)
                
        # Simple score
        score = int((match_count / len(top_job_keywords)) * 100) if top_job_keywords else 0
        
        return {
            "score": score,
            "matched_keywords": common_keywords,
            "missing_keywords": missing_keywords,
            "details": f"Matched {match_count} of {len(top_job_keywords)} key terms."
        }

    async def analyze_resume_stream(self, resume_text: str, job_description: str) -> Any:
        """
        Stream analysis tokens using Hybrid Agent Pipeline.
        
        Phase 1: Scanner Agent (Heuristic/Regex) - Instant
        Phase 2: Strategy Agent (LLM) - Deep Dive
        """
        if not self.llm_client.model:
            yield '{"type": "error", "data": "Local LLM not available."}'
            return

        # --- Phase 1: Scanner Agent (Instant) ---
        yield '{"type": "status", "data": "Agent 1: Scanning Keywords & Skills..."}'
        import asyncio
        await asyncio.sleep(0.1) # UI visual pacing

        # Use internal method to reuse logic
        ats_data = self.calculate_ats_score(resume_text, job_description)
        # Note: jobs/router.py already sends the raw ATS JSON. 
        # Here we prepare the context for the LLM agent.
        
        missing_skills_str = ", ".join(ats_data.get("missing_keywords", [])[:10])
        matched_skills_str = ", ".join(ats_data.get("matched_keywords", [])[:10])
        
        # --- Phase 2: Structure Agent (Instant) ---
        yield '{"type": "status", "data": "Agent 2: Analyzing Structure..."}'
        await asyncio.sleep(0.1)
        
        structure_issues = []
        if "EXPERIENCE" not in resume_text.upper() and "HISTORY" not in resume_text.upper():
            structure_issues.append("Missing Work Experience section")
        if "EDUCATION" not in resume_text.upper():
            structure_issues.append("Missing Education section")
            
        structure_context = f"Structural Issues: {', '.join(structure_issues)}" if structure_issues else "Structure looks standard."

        # --- Phase 3: Strategy Agent (LLM) ---
        yield '{"type": "status", "data": "Agent 3: Generating Strategic Advice..."}'
        
        # Lean Prompt - Offloading discovery to previous agents
        system_prompt = (
            "You are a Senior Career Strategist."
            "The Scanner Agent has already extracted keywords."
            "Your job is to provide high-level strategic advice based on the scan results."
            "Do NOT list keywords again. Focus on 'How to fix it'."
        )
        
        user_prompt = f"""
        JOB SCAN RESULTS:
        - Matched: {matched_skills_str}
        - Missing: {missing_skills_str}
        - Structure: {structure_context}
        
        RESUME SNIPPET:
        {resume_text[:1000]}...

        TASK:
        1. STRATEGIC FIT: 1 sentence summary.
        2. FIXING GAPS: Practical advice to address missing '{missing_skills_str}'.
        3. ELEVATOR PITCH: Rewrite the professional summary.
        
        Output in Markdown.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        async for token in self.llm_client.chat_stream(messages, max_tokens=600):
            import json
            safe_token = json.dumps(token)
            yield f'{{"type": "token", "data": {safe_token}}}'

    async def structure_resume_text(self, resume_text: str) -> Dict[str, Any]:
        """
        Use LLM to structure raw resume text into JSON for export.
        Returns dict with: summary, experience, education, skills, projects.
        """
        if not self.llm_client.model:
            logger.warning("Local LLM not available for structuring.")
            return {}

        prompt = f"""
        Extract structured data from this resume text into valid JSON.
        
        RESUME TEXT:
        {resume_text[:2500]}
        
        SCHEMA:
        {{
            "summary": "Professional summary paragraph",
            "skills": ["skill1", "skill2"],
            "experience": [
                {{
                    "title": "Job Title",
                    "company": "Company Name",
                    "location": "City, State",
                    "start_date": "MM/YYYY",
                    "end_date": "MM/YYYY or Present",
                    "description": "Brief description",
                    "achievements": ["bullet 1", "bullet 2"]
                }}
            ],
            "education": [
                {{
                    "degree": "Degree Name",
                    "institution": "University Name",
                    "start_date": "YYYY",
                    "end_date": "YYYY"
                }}
            ]
        }}
        
        Strictly output JSON only. No markdown.
        """
        
        try:
            response = await self.llm_client.generate(prompt, max_tokens=1500)
            # Cleanup potential markdown ticks
            clean_json = response.strip().replace("```json", "").replace("```", "")
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Failed to structure resume: {e}")
            return {}

    async def analyze_resume_with_llm(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Use Local LLM to provide qualitative analysis.
        """
        if not self.llm_client.model:
            return {"error": "Local LLM not available."}
        
        messages = [
            {"role": "system", "content": "You are an expert Resume Analyst. Provide concise, actionable feedback."},
            {"role": "user", "content": f"Analyze this resume against the job description.\n\nJOB DESCRIPTION:\n{job_description[:1500]}\n\nRESUME:\n{resume_text[:1500]}\n\nOutput fields: Strengths, Weaknesses, Fit Summary."}
        ]
        
        response = self.llm_client.chat(messages, max_tokens=500)
        
        return {
            "analysis": response
        }

    async def generate_tailored_content(self, current_resume: str, job_description: str, profile_data: str = "") -> str:
        """
        Generate tailored resume content.
        """
        if not self.llm_client.model:
            return "Local LLM not available."
            
        messages = [
            {"role": "system", "content": "You are a professional Resume Writer. Rewrite the resume summary and key bullet points to better match the job description, incorporating relevant skills without lying."},
            {"role": "user", "content": f"JOB:\n{job_description[:1000]}\n\nRESUME:\n{current_resume[:1000]}\n\nEXTRA INFO:\n{profile_data}\n\nRewrite the Professional Summary and Bullet Points."}
        ]
        
        return self.llm_client.chat(messages, max_tokens=800)

    async def optimize_resume_full(self, current_resume: str, job_description: str) -> str:
        """
        Rewrite the ENTIRE resume to target the job description.
        Uses keyword injection to guarantee 90%+ ATS score.
        """
        if not self.llm_client.model:
            return current_resume
        
        # Step 1: Pre-calculate missing keywords
        ats_result = self.calculate_ats_score(current_resume, job_description)
        missing_keywords = ats_result.get("missing_keywords", [])
        matched_keywords = ats_result.get("matched_keywords", [])
        
        # Step 2: Build aggressive prompt
        missing_str = ", ".join(missing_keywords[:15]) if missing_keywords else "None"
        matched_str = ", ".join(matched_keywords[:10]) if matched_keywords else "None"
        
        system = (
            "You are an expert ATS Resume Optimizer with a 100% success rate. "
            "Your ONLY goal is to rewrite the candidate's resume so that it scores 90%+ on ATS systems. "
            "You MUST incorporate the MISSING KEYWORDS listed below into the resume. "
            "Embed them naturally in the Professional Summary, Skills section, and Experience bullet points. "
            "Do NOT remove any MATCHED KEYWORDS. "
            "Output the FULL resume text in a clean, ATS-friendly format."
        )
        
        user = f"""
        === CRITICAL: MISSING KEYWORDS (MUST BE ADDED) ===
        {missing_str}
        
        === MATCHED KEYWORDS (DO NOT REMOVE) ===
        {matched_str}
        
        === JOB DESCRIPTION ===
        {job_description[:1500]}
        
        === CANDIDATE RESUME ===
        {current_resume[:1500]}
        
        === INSTRUCTIONS ===
        1. Rewrite the Professional Summary to include at least 5 of the missing keywords.
        2. Add a SKILLS section listing ALL missing keywords plus matched keywords.
        3. Rewrite Experience bullet points to naturally use remaining missing keywords.
        4. Keep Education and other sections intact but enhanced.
        5. Output the complete optimized resume text ONLY (no explanations).
        """
        
        try:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            response = self.llm_client.chat(messages, max_tokens=1500)
            return response
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return current_resume
