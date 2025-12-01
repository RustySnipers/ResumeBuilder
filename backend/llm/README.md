# LLM Integration - Phase 3.1

## Overview

This module provides integration with Anthropic's Claude API for AI-powered resume optimization. It includes async client wrappers, prompt engineering templates, streaming support, rate limiting, and comprehensive cost tracking.

## Architecture

### Components

#### ClaudeClient (`claude_client.py`)
Async wrapper for Anthropic Claude API with advanced features:
- **Async API Calls**: Non-blocking LLM requests using `AsyncAnthropic`
- **Streaming Support**: Real-time text generation with `generate_stream()`
- **Rate Limiting**: Token bucket algorithm prevents API quota exhaustion
- **Cost Tracking**: Automatic tracking of token usage and costs
- **Batch Processing**: Concurrent requests with `batch_generate()`
- **Error Handling**: Robust retry logic and error reporting

#### PromptTemplates (`prompts.py`)
Engineered prompts for resume optimization:
- **Resume Optimization**: Tailors resumes to job descriptions
- **Cover Letter Generation**: Creates personalized cover letters
- **Job Description Analysis**: Extracts requirements and keywords
- **Bullet Point Tailoring**: Optimizes experience descriptions
- **Achievement Extraction**: Transforms duties into achievements
- **Quality Validation**: Evaluates resume quality and ATS compatibility

#### CostTracker (`cost_tracker.py`)
Tracks LLM usage and costs:
- **Request Logging**: Records every API call with timestamp
- **Token Accounting**: Tracks input/output tokens separately
- **Cost Calculation**: Real-time cost estimation based on model pricing
- **Statistics**: Per-model breakdown and averages
- **Export**: Detailed reporting for budget management

### Rate Limiting

The `RateLimiter` class implements a token bucket algorithm:
- Default: 50 requests per minute (configurable)
- Automatic token refill based on elapsed time
- Async blocking when rate limit is reached
- Thread-safe with asyncio locks

**Example:**
```python
limiter = RateLimiter(max_requests_per_minute=50)
await limiter.acquire()  # Blocks if rate limit exceeded
```

### Cost Tracking

Automatic cost tracking for all API calls:

**Current Pricing (per million tokens):**
| Model | Input | Output |
|-------|--------|---------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| claude-opus-4-20250514 | $15.00 | $75.00 |
| claude-3-5-sonnet-20241022 | $3.00 | $15.00 |

**Usage Statistics:**
```python
stats = claude_client.get_usage_stats()
# Returns:
# {
#   "total_requests": 10,
#   "total_input_tokens": 15000,
#   "total_output_tokens": 8000,
#   "total_cost": 0.165,
#   "average_cost_per_request": 0.0165,
#   "requests_by_model": {...},
#   "cost_by_model": {...}
# }
```

## Usage

### Basic Setup

```python
from backend.llm.claude_client import ClaudeClient
from backend.llm.prompts import PromptTemplates

# Initialize client (API key from environment)
client = ClaudeClient(
    api_key="your-api-key",
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    temperature=1.0,
)
```

### Resume Optimization

```python
# Get system prompt
system_prompt = PromptTemplates.get_system_prompt()

# Generate optimization prompt
prompt = PromptTemplates.generate_resume_optimization(
    original_resume="...",
    job_description="...",
    missing_keywords=["Python", "Django", "REST API"],
    suggestions=["Add metrics", "Highlight achievements"],
    match_score=75.5,
    semantic_similarity=0.78,
)

# Generate optimized resume
response = await client.generate(
    prompt=prompt,
    system_prompt=system_prompt,
)

print(response["content"])  # Optimized resume
print(f"Cost: ${response['cost']:.4f}")
print(f"Tokens: {response['usage']['input_tokens']} in, {response['usage']['output_tokens']} out")
```

### Streaming Generation

```python
# Stream response in real-time
async for chunk in client.generate_stream(
    prompt=prompt,
    system_prompt=system_prompt,
):
    print(chunk, end="", flush=True)
```

### Batch Processing

```python
# Generate multiple resumes concurrently
prompts = [
    PromptTemplates.generate_resume_optimization(...),
    PromptTemplates.generate_resume_optimization(...),
    PromptTemplates.generate_resume_optimization(...),
]

results = await client.batch_generate(
    prompts=prompts,
    max_concurrent=3,  # Concurrent requests
)

for result in results:
    print(result["content"])
```

### Cost Management

```python
# Get current usage stats
stats = client.get_usage_stats()
print(f"Total cost: ${stats['total_cost']:.2f}")
print(f"Total requests: {stats['total_requests']}")

# Reset statistics (e.g., at start of billing period)
client.reset_usage_stats()

# Export detailed report
report = client.cost_tracker.export_stats()
# Includes full request history with timestamps
```

## API Integration

### Endpoints

#### `POST /api/v1/generate`
Generate optimized resume using Claude AI.

**Request:**
```json
{
  "resume_raw_text": "Software Engineer with 5 years...",
  "job_description_text": "Looking for Senior Python Developer..."
}
```

**Response:**
```json
{
  "optimized_resume": "OPTIMIZED RESUME\n\nSoftware Engineer...",
  "changes_made": [
    "Added Python-specific achievements",
    "Incorporated missing keywords: Django, FastAPI",
    "Quantified impact metrics"
  ],
  "expected_improvement": "Resume now better aligned with job requirements...",
  "usage_stats": {
    "input_tokens": 2500,
    "output_tokens": 1200,
    "cost_usd": 0.0255,
    "model": "claude-sonnet-4-20250514"
  }
}
```

#### `GET /api/v1/stats`
Get LLM usage statistics and costs.

**Response:**
```json
{
  "total_requests": 25,
  "total_input_tokens": 50000,
  "total_output_tokens": 25000,
  "total_tokens": 75000,
  "total_cost": 0.525,
  "average_cost_per_request": 0.021,
  "requests_by_model": {
    "claude-sonnet-4-20250514": 25
  },
  "cost_by_model": {
    "claude-sonnet-4-20250514": 0.525
  }
}
```

## Security

### PII Protection
All resume and job description text passes through mandatory PII redaction **before** being sent to Claude:

```python
# Automatic PII redaction in API endpoints
job_description_redacted = redact_pii(resume_input.job_description_text)
resume_redacted = redact_pii(resume_input.resume_raw_text)

# Then send redacted text to LLM
response = await claude_client.generate(prompt=...)
```

### API Key Management
- API key stored in environment variable: `ANTHROPIC_API_KEY`
- Never hardcoded in source code
- Client gracefully degrades if key is missing

```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    logger.warning("LLM endpoints unavailable - API key not set")
```

### Rate Limiting
- Prevents API quota exhaustion
- Configurable per-minute limits
- Automatic throttling when limits approached

## Testing

Comprehensive test suite in `tests/test_llm.py`:
- Rate limiter behavior (token acquisition, refilling, blocking)
- Cost tracker (request logging, statistics, export)
- Claude client (mocked API calls, cost calculation, batch processing)
- Prompt templates (all template types, realistic data)
- Integration tests (end-to-end workflows)

**Run tests:**
```bash
pytest tests/test_llm.py -v
```

## Prompt Engineering Best Practices

### System Prompt
- Establishes Claude's role and expertise
- Sets clear constraints (truthfulness, formatting)
- Defines output requirements

### Optimization Prompts
- Provide full context (resume + job description + analysis)
- Include explicit instructions and examples
- Request structured output for parsing
- Emphasize constraints (no fabrication, ATS-friendly)

### Prompt Structure
```
1. Context (original resume, job description)
2. Analysis (match score, missing keywords, suggestions)
3. Task (specific optimization instructions)
4. Output Format (structured sections)
5. Constraints (authenticity, formatting)
```

## Performance Considerations

### Latency
- Average response time: 2-5 seconds for 1000 token output
- Streaming reduces perceived latency for long responses
- Batch processing for multiple requests

### Cost Optimization
- Use Sonnet-4 for most tasks ($0.018/1K output tokens)
- Reserve Opus-4 for complex tasks ($0.075/1K output tokens)
- Monitor costs with built-in tracker
- Set budget alerts

### Throughput
- Rate limiter prevents quota exhaustion
- Batch processing for bulk operations
- Connection pooling in async client

## Future Enhancements

- [ ] Add caching for similar prompts (Redis)
- [ ] Implement prompt versioning and A/B testing
- [ ] Add fine-tuning for domain-specific optimization
- [ ] Create prompt templates for more use cases (LinkedIn, GitHub profiles)
- [ ] Implement prompt compression techniques
- [ ] Add multi-model support (GPT-4, Gemini)
- [ ] Enhanced response parsing with structured outputs
- [ ] Webhook notifications for long-running jobs

## Phase 3.1 Deliverables

✅ **ClaudeClient**: Async API wrapper with streaming
✅ **RateLimiter**: Token bucket rate limiting
✅ **CostTracker**: Comprehensive usage tracking
✅ **PromptTemplates**: 6 engineered prompt templates
✅ **API Integration**: `/api/v1/generate` and `/api/v1/stats` endpoints
✅ **Test Suite**: 30+ tests covering all components
✅ **Documentation**: Complete usage guide and examples
✅ **Security**: PII redaction + environment-based API keys
✅ **Cost Management**: Real-time tracking and reporting

**Quality Gates:**
- ✅ Async/await throughout
- ✅ Type hints on all methods
- ✅ Comprehensive error handling
- ✅ Rate limiting (50 req/min default)
- ✅ Cost tracking with per-model breakdown
- ✅ PII security gates enforced
- ✅ Streaming support for UX
- ✅ Test coverage >80%

---

**Version:** 1.2.0-phase3.1
**Last Updated:** 2025-11-30
**Status:** Production Ready
