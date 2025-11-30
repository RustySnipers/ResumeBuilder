# Repository Layer - Phase 2.3

## Overview

This directory contains the repository pattern implementation for the ResumeBuilder application. The repository pattern provides a clean abstraction layer between the application logic and data access, following async SQLAlchemy best practices.

## Architecture

### Base Repository

`BaseRepository[T]` provides generic CRUD operations for all models:
- `create(**kwargs)` - Create a new entity
- `get_by_id(id)` - Retrieve entity by UUID
- `get_all(limit, offset)` - Retrieve all entities with pagination
- `update(id, **kwargs)` - Update entity by ID
- `delete(id)` - Delete entity by ID
- `exists(id)` - Check if entity exists

All operations are fully async using AsyncSession.

### Specific Repositories

#### UserRepository
- `get_by_email(email)` - Find user by email address
- `email_exists(email)` - Check if email is already registered
- `get_active_users(limit, offset)` - Retrieve only active users

#### ResumeRepository
- `get_by_user(user_id, limit, offset)` - Get all resumes for a user
- `get_latest_version(user_id, title)` - Get highest version number for a resume title
- `get_by_title(user_id, title)` - Search resumes by title
- `count_by_user(user_id)` - Count total resumes for a user

#### JobDescriptionRepository
- `get_by_user(user_id, limit, offset)` - Get all job descriptions for a user
- `search_by_company(user_id, company_name)` - Case-insensitive company search
- `search_by_position(user_id, position_title)` - Case-insensitive position search
- `count_by_user(user_id)` - Count total job descriptions for a user

#### AnalysisRepository
- `get_by_user(user_id, limit, offset)` - Get all analyses for a user
- `get_by_resume_and_jd(resume_id, job_description_id)` - Find specific analysis
- `get_recent_analyses(user_id, days, limit)` - Get analyses within N days
- `get_by_resume(resume_id, limit, offset)` - Get all analyses for a resume
- `get_high_match_analyses(user_id, min_match_score, limit)` - Filter by match score

#### GeneratedResumeRepository
- `get_by_user(user_id, limit, offset)` - Get all generated resumes for a user
- `get_by_analysis(analysis_id, limit, offset)` - Get resumes for specific analysis
- `get_by_model(user_id, model_name, limit)` - Filter by LLM model used
- `count_by_user(user_id)` - Count total generated resumes
- `get_latest_by_analysis(analysis_id)` - Get most recent generated resume

### Unit of Work Pattern

`UnitOfWork` manages transactions across multiple repositories:

```python
async with UnitOfWork(session) as uow:
    # Create user
    user = await uow.users.create(
        email="user@example.com",
        hashed_password="...",
        is_active=True
    )

    # Create resume for that user
    resume = await uow.resumes.create(
        user_id=user.id,
        title="Software Engineer Resume",
        raw_text="...",
        version=1
    )

    # Commit transaction
    await uow.commit()
```

Benefits:
- Atomic transactions across multiple repositories
- Lazy-loaded repositories (only instantiated when accessed)
- Automatic rollback on exceptions
- Clean separation of concerns

## Usage Example

### Direct Repository Usage

```python
from backend.database import get_db
from backend.repositories.user_repository import UserRepository

async def create_user_example():
    async for session in get_db():
        repo = UserRepository(session)
        user = await repo.create(
            email="newuser@example.com",
            hashed_password="hashed_pw",
            is_active=True
        )
        return user
```

### Unit of Work Usage

```python
from backend.database import get_db
from backend.repositories.unit_of_work import UnitOfWork

async def complex_operation():
    async for session in get_db():
        async with UnitOfWork(session) as uow:
            # Multiple repository operations
            user = await uow.users.create(...)
            resume = await uow.resumes.create(user_id=user.id, ...)
            jd = await uow.job_descriptions.create(user_id=user.id, ...)
            analysis = await uow.analyses.create(
                user_id=user.id,
                resume_id=resume.id,
                job_description_id=jd.id,
                ...
            )

            # All committed atomically
            await uow.commit()
```

## Testing

Comprehensive test suite in `tests/test_repositories.py` covers:
- All CRUD operations for each repository
- User-specific query methods
- Transaction management with Unit of Work
- Error handling and rollback scenarios
- Pagination and filtering

Run tests:
```bash
pytest tests/test_repositories.py -v
```

## Database Schema

All repositories work with async SQLAlchemy models:
- `User` - User accounts with authentication
- `Resume` - Resume versions with PII redaction
- `JobDescription` - Job postings for targeting
- `Analysis` - Gap analysis results with semantic scores
- `GeneratedResume` - LLM-optimized resume versions

See `backend/models/` for model definitions and relationships.

## Performance Considerations

### N+1 Query Prevention
- Use `selectinload()` or `joinedload()` for eager loading relationships
- Batch operations when processing multiple entities
- Leverage database indexes on foreign keys and timestamps

### Connection Pooling
- Configured in `backend/database.py`
- Pool size: 20 connections
- Max overflow: 10 connections
- Automatic connection recycling

### Pagination
- All list methods support `limit` and `offset` parameters
- Default limits prevent unbounded queries
- Use for large result sets in production

## Future Enhancements

- [ ] Add caching layer (Redis) for frequently accessed data
- [ ] Implement soft delete pattern for audit trails
- [ ] Add bulk insert/update operations for batch processing
- [ ] Create materialized views for complex analytics queries
- [ ] Add read replicas support for read-heavy workloads

## Phase 2.3 Deliverables

✅ BaseRepository with generic CRUD operations
✅ 5 specific repositories (User, Resume, JobDescription, Analysis, GeneratedResume)
✅ Unit of Work pattern for transaction management
✅ Comprehensive test suite with 30+ test cases
✅ Async/await throughout for non-blocking I/O
✅ Type hints and documentation for all methods
✅ Alembic migrations for database schema

**Quality Gates:**
- ✅ 100% repository method coverage planned
- ✅ N+1 query prevention strategy documented
- ✅ Transaction management with rollback support
- ✅ Proper foreign key constraints and cascades
