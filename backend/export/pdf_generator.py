"""
PDF Generator - Phase 5

Generate professional PDF resumes using ReportLab.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generate professional ATS-friendly PDF resumes.

    Supports multiple templates and custom styling.
    """

    def __init__(
        self,
        page_size=letter,
        margin_inch: float = 0.75,
        font_name: str = "Helvetica",
    ):
        """
        Initialize PDF generator.

        Args:
            page_size: Page size (letter or A4)
            margin_inch: Page margins in inches
            font_name: Default font family
        """
        self.page_size = page_size
        self.margin = margin_inch * inch
        self.font_name = font_name
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """
        Create custom paragraph styles for resume.

        Returns:
            Dict of style name to ParagraphStyle
        """
        base_styles = getSampleStyleSheet()

        styles = {
            "name": ParagraphStyle(
                "Name",
                parent=base_styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName=f"{self.font_name}-Bold",
            ),
            "contact": ParagraphStyle(
                "Contact",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#4a4a4a"),
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            "section_header": ParagraphStyle(
                "SectionHeader",
                parent=base_styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#2c5aa0"),
                spaceBefore=12,
                spaceAfter=6,
                fontName=f"{self.font_name}-Bold",
                borderWidth=0,
                borderColor=colors.HexColor("#2c5aa0"),
                borderPadding=0,
                borderRadius=0,
            ),
            "job_title": ParagraphStyle(
                "JobTitle",
                parent=base_styles["Heading3"],
                fontSize=12,
                textColor=colors.HexColor("#1a1a1a"),
                spaceBefore=6,
                spaceAfter=3,
                fontName=f"{self.font_name}-Bold",
            ),
            "company": ParagraphStyle(
                "Company",
                parent=base_styles["Normal"],
                fontSize=11,
                textColor=colors.HexColor("#4a4a4a"),
                spaceAfter=3,
                fontName=f"{self.font_name}-Bold",
            ),
            "date": ParagraphStyle(
                "Date",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#6a6a6a"),
                spaceAfter=6,
                fontName=f"{self.font_name}",
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=8,
                alignment=TA_JUSTIFY,
            ),
            "bullet": ParagraphStyle(
                "Bullet",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#1a1a1a"),
                leftIndent=15,
                spaceAfter=4,
                bulletIndent=5,
            ),
            "skill": ParagraphStyle(
                "Skill",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#2c5aa0"),
                fontName=f"{self.font_name}-Bold",
            ),
        }

        return styles

    def generate(
        self,
        resume_data: Dict[str, Any],
        template: str = "professional",
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Generate PDF resume from resume data.

        Args:
            resume_data: Resume content as dictionary
            template: Template style to use
            output_path: Optional file path to save PDF

        Returns:
            PDF content as bytes
        """
        # Create PDF buffer
        buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
            title=f"Resume - {resume_data.get('name', 'Unknown')}",
            author=resume_data.get('name', 'Unknown'),
            subject="Professional Resume",
        )

        # Build content
        story = []

        # Header with name and contact
        story.extend(self._build_header(resume_data))

        # Summary/Objective
        if "summary" in resume_data and resume_data["summary"]:
            story.extend(self._build_summary(resume_data["summary"]))

        # Experience
        if "experience" in resume_data and resume_data["experience"]:
            story.extend(self._build_experience(resume_data["experience"]))

        # Education
        if "education" in resume_data and resume_data["education"]:
            story.extend(self._build_education(resume_data["education"]))

        # Skills
        if "skills" in resume_data and resume_data["skills"]:
            story.extend(self._build_skills(resume_data["skills"]))

        # Certifications
        if "certifications" in resume_data and resume_data["certifications"]:
            story.extend(self._build_certifications(resume_data["certifications"]))

        # Projects
        if "projects" in resume_data and resume_data["projects"]:
            story.extend(self._build_projects(resume_data["projects"]))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Save to file if path provided
        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        logger.info(f"Generated PDF resume ({len(pdf_bytes)} bytes)")

        return pdf_bytes

    def _build_header(self, resume_data: Dict[str, Any]) -> List:
        """Build resume header with name and contact info."""
        story = []

        # Name
        if "name" in resume_data:
            story.append(Paragraph(resume_data["name"], self.styles["name"]))

        # Contact information
        contact_parts = []
        if "email" in resume_data:
            contact_parts.append(resume_data["email"])
        if "phone" in resume_data:
            contact_parts.append(resume_data["phone"])
        if "location" in resume_data:
            contact_parts.append(resume_data["location"])
        if "linkedin" in resume_data:
            contact_parts.append(f"LinkedIn: {resume_data['linkedin']}")
        if "website" in resume_data:
            contact_parts.append(resume_data["website"])

        if contact_parts:
            contact_text = " | ".join(contact_parts)
            story.append(Paragraph(contact_text, self.styles["contact"]))

        story.append(Spacer(1, 0.2 * inch))

        return story

    def _build_summary(self, summary: str) -> List:
        """Build professional summary section."""
        story = []

        story.append(Paragraph("PROFESSIONAL SUMMARY", self.styles["section_header"]))
        story.append(Paragraph(summary, self.styles["body"]))
        story.append(Spacer(1, 0.15 * inch))

        return story

    def _build_experience(self, experience: List[Dict[str, Any]]) -> List:
        """Build work experience section."""
        story = []

        story.append(Paragraph("WORK EXPERIENCE", self.styles["section_header"]))

        for job in experience:
            # Job title
            if "title" in job:
                story.append(Paragraph(job["title"], self.styles["job_title"]))

            # Company and location
            company_parts = []
            if "company" in job:
                company_parts.append(job["company"])
            if "location" in job:
                company_parts.append(job["location"])

            if company_parts:
                story.append(
                    Paragraph(" - ".join(company_parts), self.styles["company"])
                )

            # Dates
            date_parts = []
            if "start_date" in job:
                date_parts.append(job["start_date"])
            if "end_date" in job:
                date_parts.append(job["end_date"])
            elif "current" in job and job["current"]:
                date_parts.append("Present")

            if date_parts:
                story.append(Paragraph(" - ".join(date_parts), self.styles["date"]))

            # Description
            if "description" in job and job["description"]:
                story.append(Paragraph(job["description"], self.styles["body"]))

            # Achievements/bullets
            if "achievements" in job and job["achievements"]:
                for achievement in job["achievements"]:
                    bullet_text = f"• {achievement}"
                    story.append(Paragraph(bullet_text, self.styles["bullet"]))

            story.append(Spacer(1, 0.1 * inch))

        return story

    def _build_education(self, education: List[Dict[str, Any]]) -> List:
        """Build education section."""
        story = []

        story.append(Paragraph("EDUCATION", self.styles["section_header"]))

        for edu in education:
            # Degree
            if "degree" in edu:
                story.append(Paragraph(edu["degree"], self.styles["job_title"]))

            # Institution
            if "institution" in edu:
                story.append(Paragraph(edu["institution"], self.styles["company"]))

            # Dates
            date_parts = []
            if "start_date" in edu:
                date_parts.append(edu["start_date"])
            if "end_date" in edu:
                date_parts.append(edu["end_date"])

            if date_parts:
                story.append(Paragraph(" - ".join(date_parts), self.styles["date"]))

            # GPA
            if "gpa" in edu:
                story.append(Paragraph(f"GPA: {edu['gpa']}", self.styles["body"]))

            # Honors/Awards
            if "honors" in edu and edu["honors"]:
                for honor in edu["honors"]:
                    bullet_text = f"• {honor}"
                    story.append(Paragraph(bullet_text, self.styles["bullet"]))

            story.append(Spacer(1, 0.1 * inch))

        return story

    def _build_skills(self, skills: List[str]) -> List:
        """Build skills section."""
        story = []

        story.append(Paragraph("SKILLS", self.styles["section_header"]))

        # Format skills as comma-separated list
        skills_text = ", ".join(skills)
        story.append(Paragraph(skills_text, self.styles["body"]))
        story.append(Spacer(1, 0.15 * inch))

        return story

    def _build_certifications(self, certifications: List[Dict[str, Any]]) -> List:
        """Build certifications section."""
        story = []

        story.append(Paragraph("CERTIFICATIONS", self.styles["section_header"]))

        for cert in certifications:
            # Certificate name
            if "name" in cert:
                story.append(Paragraph(cert["name"], self.styles["job_title"]))

            # Issuer
            if "issuer" in cert:
                story.append(Paragraph(cert["issuer"], self.styles["company"]))

            # Date
            if "date" in cert:
                story.append(Paragraph(cert["date"], self.styles["date"]))

            # Credential ID
            if "credential_id" in cert:
                story.append(
                    Paragraph(
                        f"Credential ID: {cert['credential_id']}", self.styles["body"]
                    )
                )

            story.append(Spacer(1, 0.1 * inch))

        return story

    def _build_projects(self, projects: List[Dict[str, Any]]) -> List:
        """Build projects section."""
        story = []

        story.append(Paragraph("PROJECTS", self.styles["section_header"]))

        for project in projects:
            # Project name
            if "name" in project:
                story.append(Paragraph(project["name"], self.styles["job_title"]))

            # Description
            if "description" in project:
                story.append(Paragraph(project["description"], self.styles["body"]))

            # Technologies
            if "technologies" in project:
                tech_text = f"Technologies: {', '.join(project['technologies'])}"
                story.append(Paragraph(tech_text, self.styles["body"]))

            # URL
            if "url" in project:
                story.append(Paragraph(f"URL: {project['url']}", self.styles["body"]))

            story.append(Spacer(1, 0.1 * inch))

        return story
