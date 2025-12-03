"""Analytics Schemas

Pydantic schemas for analytics API endpoints.
"""
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ActivityTimelineResponse(BaseModel):
    """Activity timeline response"""
    user_id: UUID
    days: int
    timeline: Dict[str, List[Dict]] = Field(
        description="Timeline with dates as keys and activity counts as values"
    )


class MatchScoreTrendPoint(BaseModel):
    """Match score trend data point"""
    date: str
    avg_match_score: float
    max_match_score: float
    min_match_score: float
    count: int


class MatchScoreTrendsResponse(BaseModel):
    """Match score trends response"""
    user_id: UUID
    days: int
    trends: List[Dict] = Field(description="Match score trend data")


class TemplateUsageStat(BaseModel):
    """Template usage statistics"""
    template_name: str
    total_exports: int
    successful_exports: int
    success_rate: float


class TemplateUsageResponse(BaseModel):
    """Template usage response"""
    user_id: UUID
    days: int
    templates: List[Dict] = Field(description="Template usage statistics")


class ExportTrendPoint(BaseModel):
    """Export trend data point"""
    date: str
    total_exports: int
    cached_exports: int
    cache_rate: float
    avg_generation_time_ms: int
    total_size_mb: float


class ExportTrendsResponse(BaseModel):
    """Export trends response"""
    user_id: UUID
    days: int
    trends: List[Dict] = Field(description="Export trend data")


class SuccessRateResponse(BaseModel):
    """Success rate response"""
    user_id: UUID
    days: int
    total: int = Field(description="Total number of analyses")
    successful: int = Field(description="Number of successful analyses (match score >= 70%)")
    success_rate: float = Field(description="Success rate (0-1)")


class KeywordStats(BaseModel):
    """Keyword match statistics"""
    avg_total_keywords: float
    avg_matched_keywords: float
    avg_missing_keywords: float
    avg_match_rate: float


class LLMUsageStats(BaseModel):
    """LLM usage statistics"""
    total_analyses: int
    llm_analyses: int
    cached_analyses: int
    total_cost: float
    total_tokens: int
    cache_rate: float
    avg_cost: float


class PerformanceStats(BaseModel):
    """Performance statistics"""
    avg_time_ms: int
    min_time_ms: int
    max_time_ms: int


class AnalysisStats(BaseModel):
    """Analysis statistics"""
    success_rate: Dict
    keyword_stats: Dict
    llm_usage: Dict
    performance: Dict


class CacheEffectiveness(BaseModel):
    """Cache effectiveness statistics"""
    total_exports: int
    cached_exports: int
    cache_hit_rate: float
    avg_cached_time_ms: int
    avg_uncached_time_ms: int
    time_savings_ms: int


class ExportStats(BaseModel):
    """Export statistics"""
    template_usage: List[Dict]
    format_usage: Dict[str, int]
    cache_effectiveness: Dict


class DashboardResponse(BaseModel):
    """Dashboard statistics response"""
    period_days: int = Field(description="Number of days aggregated")
    activity_counts: Dict[str, int] = Field(description="Activity counts by type")
    analysis: Dict = Field(description="Analysis statistics")
    exports: Dict = Field(description="Export statistics")


class UserSummaryResponse(BaseModel):
    """User summary response from daily metrics"""
    user_id: UUID
    days: int
    total_activities: int
    total_analyses: int
    avg_match_score: float
    total_exports: int
    total_llm_cost: float
    success_rate: float
    export_cache_rate: float
    llm_cache_rate: float
