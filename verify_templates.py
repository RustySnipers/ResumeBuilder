import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.export.docx_generator import DOCXGenerator
from datetime import datetime

# Sample Resume Data
SAMPLE_RESUME = {
    "name": "Alex Coder",
    "email": "alex@example.com",
    "phone": "555-0123",
    "location": "San Francisco, CA",
    "linkedin": "linkedin.com/in/alexcoder",
    "website": "alexcoder.dev",
    "summary": "Senior Software Engineer with 5+ years of experience in Python and React. Passionate about building scalable AI tools.",
    "experience": [
        {
            "title": "Senior Engineer",
            "company": "Tech Corp",
            "location": "Remote",
            "start_date": "2021",
            "current": True,
            "description": "Leading the AI team.",
            "achievements": [
                "Built a resume builder using Local LLMs.",
                "Improved system performance by 40%."
            ]
        },
        {
            "title": "Software Engineer",
            "company": "Startup Inc",
            "location": "San Francisco",
            "start_date": "2018",
            "end_date": "2021",
            "description": "Full stack development.",
            "achievements": [
                "Deployed 15 features to production.",
                "Mentored 2 junior engineers."
            ]
        }
    ],
    "education": [
        {
            "degree": "BS Computer Science",
            "institution": "University of Tech",
            "start_date": "2014",
            "end_date": "2018",
            "gpa": "3.8"
        }
    ],
    "skills": ["Python", "React", "Docker", "AWS", "FastAPI"],
    "projects": [
        {
            "name": "Local AI Assistant",
            "description": "A local LLM wrapper in Python.",
            "technologies": ["Python", "LlamaCpp"],
            "url": "github.com/project"
        }
    ]
}

def test_templates():
    generator = DOCXGenerator()
    
    # Test Standard ATS
    print("Generating Standard ATS...")
    standard_bytes = generator.generate(SAMPLE_RESUME, template="standard_ats")
    with open("verify_standard_ats.docx", "wb") as f:
        f.write(standard_bytes)
    print(f"Saved verify_standard_ats.docx ({len(standard_bytes)} bytes)")

    # Test Modern ATS
    print("Generating Modern ATS...")
    modern_bytes = generator.generate(SAMPLE_RESUME, template="modern_ats")
    with open("verify_modern_ats.docx", "wb") as f:
        f.write(modern_bytes)
    print(f"Saved verify_modern_ats.docx ({len(modern_bytes)} bytes)")

if __name__ == "__main__":
    test_templates()
