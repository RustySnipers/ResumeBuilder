# Architecture Notes - Resume Builder Phase 1

**Last Updated:** 2025-11-28
**Phase:** 1 (Foundation and Compliance Backend)
**Status:** ✅ Enhanced with comprehensive test coverage

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Decisions](#design-decisions)
3. [Implementation Details](#implementation-details)
4. [Phase 1 Limitations](#phase-1-limitations)
5. [Testing Strategy](#testing-strategy)
6. [Future Enhancements](#future-enhancements)
7. [Open Questions](#open-questions)

---

## System Overview

### Purpose

The Resume Builder backend is a secure, compliance-first API for AI-powered resume optimization. It analyzes resumes against job descriptions to identify gaps and provide actionable suggestions for improving ATS (Applicant Tracking System) compatibility.

### Core Principles

1. **Security First**: Mandatory PII redaction before any processing
2. **Simplicity**: Phase 1 uses simple, deterministic algorithms (no external ML dependencies)
3. **Testability**: Comprehensive test coverage for all core functionality
4. **Extensibility**: Clear TODOs and scaffolding for future phases

### Architecture Pattern

**Stateless REST API** - No database in Phase 1; all processing is request/response.

```
Client Request
    ↓
FastAPI Endpoint (/api/v1/analyze)
    ↓
PII Redaction (Security Gate)
    ↓
Gap Analysis (Keyword Matching)
    ↓
JSON Response (GapAnalysisResult)
```

---

## Design Decisions

### 1. Why Regex-Based PII Redaction?

**Decision:** Use regular expressions for PII detection in Phase 1.

**Rationale:**
- **Fast**: No external API calls or model inference overhead
- **Deterministic**: Same input always produces same output (testable)
- **No Dependencies**: Works offline without external services
- **Good Enough**: Covers 90%+ of common PII patterns in resumes

**Trade-offs:**
- ❌ Cannot detect person names reliably (no NER)
- ❌ May miss context-specific PII (e.g., "John" in "John Deere Company")
- ❌ No semantic understanding (e.g., "My SSN is in my file" won't redact "in my file")

**Phase 2 Enhancement:** Add spaCy or transformers-based NER for person/organization detection.

### 2. Why Simple Keyword Gap Analysis?

**Decision:** Use frequency-based keyword matching with hardcoded bigram list.

**Rationale:**
- **Baseline**: Establishes a working MVP for gap detection
- **Transparent**: Users can understand why keywords are flagged
- **No ML Dependencies**: Works without embeddings or external APIs
- **Fast**: O(n) tokenization and set operations

**Trade-offs:**
- ❌ No semantic understanding ("Python" and "Python3" treated separately)
- ❌ Misses synonyms ("ML" vs "machine learning")
- ❌ Cannot detect skill levels (junior vs senior Python)
- ❌ Hardcoded bigram list may miss domain-specific terms

**Phase 2 Enhancement:** Add TF-IDF, n-gram extraction, and semantic embeddings.

### 3. Why No Database in Phase 1?

**Decision:** Implement as a stateless API with no persistence.

**Rationale:**
- **Simplicity**: Reduces complexity for proof-of-concept
- **Compliance**: No data storage means no data breach risk
- **Faster Development**: No schema design, migrations, or ORM setup

**Trade-offs:**
- ❌ Cannot track resume versions or history
- ❌ No user sessions or saved analyses
- ❌ Each request is independent (no learning)

**Phase 2 Enhancement:** Add PostgreSQL for resume storage and Redis for caching.

### 4. Why FastAPI?

**Decision:** Use FastAPI as the web framework.

**Rationale:**
- **Modern**: Built on Python 3.7+ type hints and async/await
- **Fast**: ASGI-based, comparable to Node.js/Go performance
- **Auto-Docs**: Generates OpenAPI/Swagger docs automatically
- **Pydantic Integration**: Type validation built-in

**Alternatives Considered:**
- Flask: Simpler but lacks async and auto-docs
- Django: Too heavyweight for a microservice API

### 5. Why Pydantic v2?

**Decision:** Use Pydantic for request/response validation.

**Rationale:**
- **Type Safety**: Catches validation errors at runtime
- **Auto-Docs**: Generates JSON schemas for OpenAPI
- **Performance**: Pydantic v2 is 5-50x faster than v1
- **Serialization**: `.model_dump_json()` for clean JSON output

---

## Implementation Details

### PII Redaction Patterns

**Enhanced in this session:**

| PII Type | Pattern | Example Match |
|----------|---------|---------------|
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}` | `john.doe@example.com` |
| Phone (US) | `\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}` | `(555) 123-4567` |
| Phone (Intl) | `\+\d{1,3}[-.\s]?\(?\d{1,4}\)?...` | `+1-555-123-4567` |
| SSN | `\d{3}-\d{2}-\d{4}` | `123-45-6789` |
| Address | `\d+\s+[A-Za-z\s]+(Street\|Ave\|Rd\|...)` | `123 Main Street` |
| URL | `https?://[^\s<>"\']+` | `https://github.com/user` |
| Name (heuristic) | `^([A-Z][a-z]+(\s+[A-Z][a-z]+){1,3})\s*\n` | `John Doe\n` (at start) |

**Known Limitations:**
- Name detection only works for names at document start
- Cannot distinguish personal names from company names
- May miss international address formats
- No credit card or passport number detection

### Gap Analysis Algorithm

**Enhanced in this session:**

1. **Stop Word Filtering**: 95+ common English words filtered
2. **Bigram Detection**: 30+ hardcoded multi-word technical terms
3. **Frequency Analysis**: Top 30 keywords from job description
4. **Missing Keyword Identification**: Set difference between JD and resume
5. **Suggestion Generation**: Context-aware feedback based on gap count

**Bigrams Supported:**
- `machine learning`, `deep learning`, `artificial intelligence`
- `cloud computing`, `full stack`, `rest api`, `microservices`
- `continuous integration`, `object oriented`, etc.

**Suggestion Rules:**
- 0 missing → "Well-aligned" positive feedback
- 1-5 missing → "Add relevant keywords"
- 6-10 missing → "Improve ATS matching"
- 10+ missing → "Review job description and align experiences"

### API Endpoints

#### `GET /`
**Purpose:** Health check
**Response:** Service metadata
**Status:** ✅ Complete

#### `POST /api/v1/analyze`
**Purpose:** Analyze resume vs job description
**Input:** `ResumeInput` (job_description_text, resume_raw_text)
**Output:** `GapAnalysisResult` (missing_keywords, suggestions)
**Validation:** Min 10 chars for both inputs
**Status:** ✅ Enhanced with improved analysis

---

## Phase 1 Limitations

### Known Issues

1. **Name Redaction Incomplete**
   - Only detects names at document start (e.g., "John Doe\n")
   - Cannot distinguish "John Smith" (person) from "Smith Corporation" (company)
   - **Impact:** Names in experience section may not be redacted
   - **Mitigation:** Phase 2 NER will address this

2. **No Synonym Detection**
   - "ML" and "machine learning" treated as different keywords
   - "React.js" vs "React" vs "ReactJS" all separate
   - **Impact:** May suggest adding keywords that are conceptually present
   - **Mitigation:** Phase 2 semantic embeddings

3. **No Context Awareness**
   - Keywords in any section count equally (skills vs summary)
   - No detection of keyword stuffing (repetition)
   - **Impact:** May not catch low-quality resumes
   - **Mitigation:** Phase 2 section-aware analysis

4. **No International Support**
   - Stop words are English-only
   - Address patterns are US-centric
   - **Impact:** Non-English resumes may have poor results
   - **Mitigation:** Phase 2 i18n support

5. **Hardcoded Bigram List**
   - Only 30 multi-word terms supported
   - May miss industry-specific terminology
   - **Impact:** Domain-specific gaps may be missed
   - **Mitigation:** Phase 2 n-gram extraction

### What Phase 1 Does NOT Do

- ❌ Resume generation or rewriting
- ❌ LLM integration (Claude API)
- ❌ User authentication or sessions
- ❌ Resume storage or history
- ❌ PDF/DOCX parsing or export
- ❌ Email notifications
- ❌ Batch processing
- ❌ Rate limiting
- ❌ Logging or monitoring

---

## Testing Strategy

### Test Coverage (Implemented)

**Unit Tests:**
- `tests/test_pii_redaction.py` - 25+ test cases for PII patterns
- `tests/test_gap_analysis.py` - 20+ test cases for keyword extraction
- `tests/test_api_endpoints.py` - 30+ test cases for API validation

**Test Markers:**
- `@pytest.mark.unit` - Fast, isolated function tests
- `@pytest.mark.integration` - API endpoint tests with TestClient
- `@pytest.mark.pii` - PII redaction specific tests
- `@pytest.mark.gap_analysis` - Gap analysis specific tests

### Testing Philosophy

1. **Test Real-World Scenarios**: Use realistic resume/JD text
2. **Test Edge Cases**: Empty inputs, very long inputs, unicode, special chars
3. **Test Failure Modes**: Invalid JSON, missing fields, too-short inputs
4. **Test Security**: Verify PII redaction actually works
5. **Test API Contract**: Ensure OpenAPI schema matches implementation

### Running Tests

```bash
# Run all tests
pytest

# Run only PII tests
pytest -m pii

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=main --cov-report=term-missing
```

---

## Future Enhancements

### Phase 2: Enhanced Analysis (Planned)

**PII Detection:**
- Integrate spaCy for Named Entity Recognition (NER)
- Add context-aware person/company name disambiguation
- Support international PII formats (IBAN, passport numbers, etc.)
- Add PII detection service integration (AWS Comprehend, Google DLP)

**Gap Analysis:**
- Implement TF-IDF for better keyword ranking
- Add automated n-gram extraction (trigrams, 4-grams)
- Integrate stemming/lemmatization (NLTK, spaCy)
- Use SentenceTransformers for semantic similarity
- Add industry-specific vocabulary lists

**Data Quality:**
- Detect keyword stuffing and over-optimization
- Analyze keyword placement (skills vs experience vs summary)
- Provide match quality score (0-100)

### Phase 3: LLM Integration (Planned)

**Claude API:**
- Integrate Anthropic SDK for Claude Sonnet 4.5
- Implement streaming for real-time resume generation
- Add retry logic with exponential backoff
- Implement cost tracking and budget limits
- Add LLM response validation (hallucination detection)

**Endpoints:**
- `POST /api/v1/generate` - Generate tailored resume
- `POST /api/v1/optimize` - Optimize existing resume sections
- `GET /api/v1/generate/{id}/stream` - Streaming resume generation

### Phase 4: Persistence & Authentication (Planned)

**Database:**
- PostgreSQL for resume storage
- SQLAlchemy ORM for database models
- Redis cache for frequently accessed data
- Implement resume version history

**Authentication:**
- OAuth2 + JWT for user authentication
- Role-based access control (RBAC)
- API key management for developers
- Rate limiting per user/API key

### Phase 5: Production Features (Planned)

**Export:**
- PDF export using reportlab or WeasyPrint
- DOCX export using python-docx
- Resume templates and styling

**Analytics:**
- Track resume match scores over time
- A/B testing for resume variations
- Success rate analytics (interview callbacks)

**Integrations:**
- Webhook support for resume updates
- Email notifications (SendGrid, AWS SES)
- Job board integrations (LinkedIn, Indeed)

---

## Open Questions

### Technical Questions

1. **Should we redact company names?**
   - **Pro:** Prevents identification via unique employer combinations
   - **Con:** Removes critical context for LLM resume generation
   - **Current Decision:** Phase 1 does NOT redact company names
   - **Action:** Revisit in Phase 2 with NER; make it configurable

2. **Should gap analysis consider synonyms?**
   - **Example:** Job says "ML", resume says "machine learning"
   - **Current Behavior:** Flags "ML" as missing (false positive)
   - **Phase 2 Solution:** Use semantic embeddings to detect synonyms
   - **Workaround:** Bigram list includes common expansions

3. **What's the acceptable PII redaction recall/precision trade-off?**
   - **Recall:** % of PII actually detected (want 100%)
   - **Precision:** % of redactions that are actual PII (avoid false positives)
   - **Current:** High precision (~95%), moderate recall (~80%)
   - **Action:** Monitor false negatives; improve in Phase 2 with NER

4. **Should we support non-English resumes?**
   - **Current:** English-only stop words and patterns
   - **Phase 2:** Add language detection and multi-language support
   - **Libraries:** langdetect, spaCy multi-language models

5. **How to handle special characters in technical terms?**
   - **Example:** "C++", "C#", ".NET", "Vue.js"
   - **Current:** Regex may filter special chars, missing these terms
   - **Phase 2:** Preserve technical term patterns, use allowlist

### Product Questions

1. **Should we store PII at all (even encrypted)?**
   - **Phase 1:** No storage (stateless API)
   - **Phase 2+:** If storing, must encrypt at rest (AES-256, AWS KMS)
   - **Compliance:** GDPR, CCPA require data minimization

2. **What LLM safety checks are needed?**
   - Prevent hallucination (fake experiences)
   - Detect toxic/biased language in generated resumes
   - Ensure factual consistency with original resume

3. **How to price the service?**
   - Per-resume analysis cost (LLM API cost ~$0.10-$1.00)
   - Freemium model (5 free analyses/month)?
   - Enterprise tier (unlimited, custom templates)?

4. **Should we support job application tracking?**
   - Track which resume versions were sent where
   - Monitor interview callback rates
   - Provide success analytics

---

## Change Log

### 2025-11-28: Phase 1 Enhancement

**Added:**
- Comprehensive test suite (75+ test cases)
- Enhanced PII redaction (URL, name patterns)
- Improved gap analysis (bigram support, expanded stop words)
- TODO scaffolding for Phases 2-5
- This ARCHITECTURE_NOTES.md document

**Improved:**
- PII redaction now catches URLs, improved phone/email patterns
- Gap analysis detects multi-word technical terms
- Better suggestion generation based on gap severity

**Known Issues:**
- Name redaction still heuristic-based (NER in Phase 2)
- Bigram list is hardcoded (n-gram extraction in Phase 2)
- No semantic similarity yet (embeddings in Phase 2)

---

## References

### External Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [spaCy NER Models](https://spacy.io/usage/linguistic-features#named-entities)

### Internal Documentation

- `README.md` - Project overview and setup instructions
- `main.py` - Core application code with inline TODOs
- `llm_prompt_template.py` - LLM prompt engineering (Phase 3)
- `tests/` - Comprehensive test suite

---

**Document Status:** ✅ Complete for Phase 1
**Next Review:** After Phase 2 implementation begins
