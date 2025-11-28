# AI-Powered ATS-Friendly Resume Builder

**Phase 1: Foundation and Compliance Backend**

A secure, compliant FastAPI backend for AI-powered resume optimization with mandatory PII redaction and intelligent gap analysis.

## Overview

This project implements the foundational backend infrastructure for an AI-powered resume builder that helps job seekers optimize their resumes for Applicant Tracking Systems (ATS) while maintaining strict security and compliance standards.

### Key Features (Phase 1)

- **PII Security Gate**: Non-bypassable PII redaction before any LLM processing
- **Gap Analysis**: Intelligent keyword matching between job descriptions and resumes
- **REST API**: Clean FastAPI endpoints with Pydantic validation
- **LLM-Ready**: Structured prompt templates for Claude Sonnet/Opus integration (Phase 3)

## Technical Stack

- **Python**: 3.10+
- **Framework**: FastAPI
- **Validation**: Pydantic v2
- **Server**: Uvicorn (ASGI)
- **Target LLM**: Claude Sonnet 4.5 / Opus (Phase 3)

## Project Structure

```
ResumeBuilder/
├── main.py                    # Core FastAPI application
├── llm_prompt_template.py     # LLM prompt construction (Phase 3)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ResumeBuilder
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Server

Start the FastAPI development server with auto-reload:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Health Check

**GET** `/`

Returns service status and version information.

**Response**:
```json
{
  "service": "ATS Resume Builder API",
  "version": "1.0.0-phase1",
  "status": "operational",
  "phase": "Foundation and Compliance Backend"
}
```

### Resume Analysis

**POST** `/api/v1/analyze`

Analyzes a resume against a job description with mandatory PII redaction.

**Request Body**:
```json
{
  "job_description_text": "We are seeking a Senior Python Developer...",
  "resume_raw_text": "John Doe\nSoftware Engineer\n..."
}
```

**Response**:
```json
{
  "missing_keywords": [
    "fastapi",
    "sqlalchemy",
    "kubernetes",
    "docker"
  ],
  "suggestions": [
    "Consider incorporating these key terms: fastapi, sqlalchemy, kubernetes",
    "Ensure your skills section includes technologies mentioned in the job description"
  ]
}
```

## Usage Examples

### Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description_text": "We need a Python developer with FastAPI experience",
    "resume_raw_text": "Software Engineer with Django experience..."
  }'
```

### Using Python

```python
import requests

url = "http://localhost:8000/api/v1/analyze"
payload = {
    "job_description_text": "We are seeking a Senior Python Developer with FastAPI...",
    "resume_raw_text": "John Doe\njohn@email.com\n\nExperience:\nSoftware Engineer..."
}

response = requests.post(url, json=payload)
result = response.json()

print("Missing Keywords:", result["missing_keywords"])
print("Suggestions:", result["suggestions"])
```

## Security & Compliance

### PII Redaction

All input text passes through the `redact_pii()` security gate, which redacts:
- Email addresses
- Phone numbers (multiple formats)
- Social Security Numbers
- Street addresses

**Phase 1 Note**: Current implementation uses regex-based pattern matching. Future phases will integrate:
- Named Entity Recognition (NER) models
- Advanced PII detection services
- Encryption for sensitive data at rest

### Data Flow

```
User Input → PII Redaction → Gap Analysis → Response
                ↓
          (Future: LLM Processing)
```

No PII reaches downstream LLM processing in future phases.

## LLM Prompt Template (Phase 3)

The `llm_prompt_template.py` module provides a production-ready prompt template for Claude Sonnet/Opus integration.

### Key Prompt Engineering Features

- **Clear Instructions**: Explicit role and task definition
- **Comprehensive Context**: Job description, resume, gap analysis
- **Output Constraints**: ATS-friendly formatting rules
- **Safety Guards**: Anti-hallucination measures, truthfulness enforcement

### Example Usage

```python
from llm_prompt_template import construct_resume_tailoring_prompt
from main import GapAnalysisResult

gap_result = GapAnalysisResult(
    missing_keywords=["python", "fastapi"],
    suggestions=["Add Python frameworks to skills"]
)

prompt = construct_resume_tailoring_prompt(
    job_description_redacted="Senior Python Developer...",
    resume_text_redacted="Software Engineer with 5 years...",
    gap_analysis_json=gap_result.model_dump_json(indent=2)
)

# Send prompt to Claude API (Phase 3)
```

## Development Roadmap

### Phase 1 (Current): Foundation ✅
- FastAPI backend with Pydantic models
- PII redaction security gate
- Rudimentary gap analysis
- LLM prompt template

### Phase 2 (Planned): Enhanced Analysis
- Advanced NLP for keyword extraction
- Semantic similarity scoring
- Industry-specific resume templates
- Improved PII detection (NER models)

### Phase 3 (Planned): LLM Integration
- Claude Sonnet/Opus API integration
- Resume generation with AI
- Multi-version resume outputs
- A/B testing for resume optimization

### Phase 4 (Planned): Production Features
- User authentication and authorization
- Resume version history
- Export to PDF/DOCX formats
- Analytics dashboard

## Testing

Run the example in `llm_prompt_template.py` to see the prompt construction:

```bash
python llm_prompt_template.py
```

## Contributing

This is a Phase 1 proof-of-concept. Future contributions should focus on:
- Enhanced PII detection algorithms
- More sophisticated gap analysis
- Integration with Claude API
- Comprehensive test coverage

## License

[Specify your license here]

## Contact

[Specify contact information or support channels]

---

**Phase 1 Status**: ✅ Complete - Foundation and Compliance Backend Operational
