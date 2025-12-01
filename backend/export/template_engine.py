"""
Template Engine - Phase 5

Template rendering and management for resume generation.
"""

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Jinja2-based template engine for resume rendering.

    Supports multiple templates and custom styling.
    """

    def __init__(self, templates_dir: str = None):
        """
        Initialize template engine.

        Args:
            templates_dir: Directory containing templates
        """
        if templates_dir is None:
            # Default to backend/templates directory
            base_dir = Path(__file__).parent.parent
            templates_dir = str(base_dir / "templates")

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['format_phone'] = self._format_phone

    def render(
        self, template_name: str, resume_data: Dict[str, Any]
    ) -> str:
        """
        Render resume using specified template.

        Args:
            template_name: Name of template file
            resume_data: Resume content

        Returns:
            Rendered HTML string
        """
        try:
            template = self.env.get_template(f"resumes/{template_name}.html")
            html = template.render(resume=resume_data)
            logger.info(f"Rendered template: {template_name}")
            return html
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise

    def list_templates(self) -> List[Dict[str, str]]:
        """
        List available resume templates.

        Returns:
            List of template metadata
        """
        templates = [
            {
                "id": "modern",
                "name": "Modern Professional",
                "description": "Clean, modern design with accent colors",
                "category": "modern",
                "preview_url": "/static/previews/modern.png",
            },
            {
                "id": "classic",
                "name": "Classic Professional",
                "description": "Traditional, conservative layout",
                "category": "classic",
                "preview_url": "/static/previews/classic.png",
            },
            {
                "id": "professional",
                "name": "Professional",
                "description": "Balanced, professional appearance",
                "category": "professional",
                "preview_url": "/static/previews/professional.png",
            },
            {
                "id": "minimal",
                "name": "Minimal",
                "description": "Minimalist design with maximum readability",
                "category": "minimal",
                "preview_url": "/static/previews/minimal.png",
            },
        ]

        return templates

    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        Get template metadata.

        Args:
            template_id: Template identifier

        Returns:
            Template metadata dict
        """
        templates = {t["id"]: t for t in self.list_templates()}

        if template_id not in templates:
            raise ValueError(f"Template not found: {template_id}")

        return templates[template_id]

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format date for display."""
        if not date_str:
            return ""

        # Handle common date formats
        # This is a simple implementation - enhance as needed
        return date_str

    @staticmethod
    def _format_phone(phone: str) -> str:
        """Format phone number for display."""
        if not phone:
            return ""

        # Remove non-numeric characters
        digits = ''.join(c for c in phone if c.isdigit())

        # Format as (XXX) XXX-XXXX for US numbers
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

        return phone  # Return original if can't format
