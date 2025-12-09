"""
Resume Parsing Service.

Extracts text from PDF and DOCX files.
"""

import logging
import io
from fastapi import UploadFile
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentParserService:
    """Service for parsing uploaded resume files."""

    @staticmethod
    async def parse_resume(file: UploadFile) -> str:
        """
        Extract text from an uploaded resume file.
        
        Args:
            file: FastAPI UploadFile object
        
        Returns:
            Extracted text content
        """
        content_type = file.content_type
        filename = file.filename.lower()
        
        logger.info(f"Parsing file: {filename} ({content_type})")
        
        # Read file content into memory
        file_content = await file.read()
        file_obj = io.BytesIO(file_content)

        extracted_text = ""

        try:
            if "pdf" in content_type or filename.endswith(".pdf"):
                extracted_text = DocumentParserService._parse_pdf(file_obj)
            elif "word" in content_type or "officedocument" in content_type or filename.endswith(".docx"):
                extracted_text = DocumentParserService._parse_docx(file_obj)
            elif "text" in content_type or filename.endswith(".txt"):
                extracted_text = file_obj.read().decode("utf-8", errors="ignore")
            else:
                logger.warning(f"Unsupported file type: {content_type}")
                return ""
                
            # Basic cleanup
            return extracted_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to parse file: {e}")
            raise
        finally:
            await file.seek(0) # Reset file pointer if needed later

    @staticmethod
    def _parse_pdf(file_obj: io.BytesIO) -> str:
        """Parse PDF content."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_obj)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except ImportError:
            logger.error("pypdf not installed.")
            return "Error: PDF parsing library missing."

    @staticmethod
    def _parse_docx(file_obj: io.BytesIO) -> str:
        """Parse DOCX content."""
        try:
            import docx
            doc = docx.Document(file_obj)
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            logger.error("python-docx not installed.")
            return "Error: DOCX parsing library missing."
