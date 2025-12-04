"""Webhook Schemas

Pydantic schemas for webhook API endpoints.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    """Schema for creating a webhook"""
    url: str = Field(..., description="Webhook URL", max_length=2000)
    events: List[str] = Field(..., description="List of event types to subscribe to", min_items=1)
    description: Optional[str] = Field(None, description="Optional description", max_length=500)
    timeout_seconds: int = Field(30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook"""
    url: Optional[str] = Field(None, description="Webhook URL", max_length=2000)
    events: Optional[List[str]] = Field(None, description="List of event types", min_items=1)
    description: Optional[str] = Field(None, description="Description", max_length=500)
    is_active: Optional[bool] = Field(None, description="Active status")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300, description="Timeout in seconds")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Max retry attempts")


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    id: UUID
    user_id: UUID
    url: str
    description: Optional[str]
    events: List[str]
    secret: str = Field(..., description="HMAC secret for signature verification")
    is_active: bool
    timeout_seconds: int
    max_retries: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Schema for webhook list response"""
    webhooks: List[WebhookResponse]
    total: int


class WebhookEventResponse(BaseModel):
    """Schema for webhook event response"""
    id: UUID
    webhook_id: UUID
    event_type: str
    event_id: UUID
    payload: Dict[str, Any]
    status: str
    attempt_count: int
    max_attempts: int
    http_status: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    response_time_ms: Optional[int]
    next_retry_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookEventListResponse(BaseModel):
    """Schema for webhook event list response"""
    events: List[WebhookEventResponse]
    total: int


class WebhookStatisticsResponse(BaseModel):
    """Schema for webhook statistics"""
    pending: int
    success: int
    failed: int
    retrying: int
    total: int
    success_rate: float


class WebhookSecretResponse(BaseModel):
    """Schema for webhook secret regeneration response"""
    webhook_id: UUID
    secret: str = Field(..., description="New HMAC secret")
    message: str = Field(default="Secret regenerated successfully")


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response"""
    success: bool
    message: str
    http_status: Optional[int]
    response_time_ms: Optional[int]
    error: Optional[str]


class WebhookEventTypesResponse(BaseModel):
    """Schema for available event types"""
    event_types: List[Dict[str, str]] = Field(
        ...,
        description="List of available event types with descriptions"
    )


class WebhookDeliveryRequest(BaseModel):
    """Schema for manual webhook delivery trigger"""
    event_type: str
    payload: Dict[str, Any] = Field(..., description="Event payload")
