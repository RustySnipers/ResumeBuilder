"""
Markdown Generator - Phase 5

Generate simple Markdown resumes.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generate Markdown formatted resumes."""

    def generate(self, resume_data: Dict[str, Any], template: str = "standard") -> str:
        """
        Generate Markdown content from resume data.

        Args:
            resume_data: Resume content as dictionary
            template: Ignored for markdown (standard format)

        Returns:
            Markdown string
        """
        md = []

        # Header
        name = resume_data.get("name", "Unknown Name")
        md.append(f"# {name}")
        
        contact_parts = []
        if "email" in resume_data: contact_parts.append(f"Email: {resume_data['email']}")
        if "phone" in resume_data: contact_parts.append(f"Phone: {resume_data['phone']}")
        if "location" in resume_data: contact_parts.append(f"Location: {resume_data['location']}")
        if "linkedin" in resume_data: contact_parts.append(f"[LinkedIn]({resume_data['linkedin']})")
        
        if contact_parts:
            md.append(" | ".join(contact_parts))
        
        md.append("\n---\n")

        # Summary
        if "summary" in resume_data and resume_data["summary"]:
            md.append("## Professional Summary")
            md.append(resume_data["summary"])
            md.append("")

        # Experience
        if "experience" in resume_data and resume_data["experience"]:
            md.append("## Work Experience")
            for job in resume_data["experience"]:
                title = job.get("title", "Job Title")
                company = job.get("company", "Company")
                start = job.get("start_date", "")
                end = job.get("end_date", "")
                
                md.append(f"### {title} | {company}")
                if start or end:
                    md.append(f"*{start} - {end}*")
                
                if "description" in job:
                    md.append(job["description"])
                
                if "achievements" in job:
                    for bullet in job["achievements"]:
                        md.append(f"- {bullet}")
                md.append("")

        # Education
        if "education" in resume_data and resume_data["education"]:
            md.append("## Education")
            for edu in resume_data["education"]:
                degree = edu.get("degree", "Degree")
                school = edu.get("institution", "University")
                start = edu.get("start_date", "")
                end = edu.get("end_date", "")
                
                md.append(f"### {degree}")
                md.append(f"**{school}** | *{start} - {end}*")
                if "gpa" in edu:
                    md.append(f"GPA: {edu['gpa']}")
                md.append("")

        # Skills
        if "skills" in resume_data and resume_data["skills"]:
            md.append("## Skills")
            md.append(", ".join(resume_data["skills"]))
            md.append("")

        # Projects
        if "projects" in resume_data and resume_data["projects"]:
            md.append("## Projects")
            for proj in resume_data["projects"]:
                name = proj.get("name", "Project")
                md.append(f"### {name}")
                if "technologies" in proj:
                    md.append(f"*Stack: {', '.join(proj['technologies'])}*")
                if "description" in proj:
                    md.append(proj["description"])
                md.append("")

        content = "\n".join(md)
        logger.info(f"Generated Markdown resume ({len(content)} chars)")
        return content
