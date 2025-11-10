from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
from datetime import datetime

# -------------------
# Request Schemas
# -------------------

class DirectEmailRequest(BaseModel):
    to_email: EmailStr = Field(..., example="user@example.com")
    from_email: Optional[EmailStr] = Field("noreply@company.com", example="noreply@company.com")
    subject: str = Field(..., example="Welcome to Our Service")
    content: str = Field(..., example="Hello, welcome to our platform!")
    html_content: Optional[str] = Field(None, description="HTML version of email")

# -------------------
# Response Schemas
# -------------------

class EmailResponseData(BaseModel):
    message_id: str = Field(..., example="uuid-1234-5678")
    status: str = Field(..., example="sent")  
    service_response: Optional[str] = Field(None, description="Response from SMTP service")
    timestamp: datetime = Field(..., example="2025-11-10T10:00:00Z")

class EmailResponse(BaseModel):
    success: bool = Field(..., example=True)
    data: EmailResponseData
    message: Optional[str] = Field(None, example="Email sent successfully")

class EmailStatusDeliveryInfo(BaseModel):
    smtp_response: Optional[str] = Field(None)
    bounce_reason: Optional[str] = Field(None)
    retry_count: Optional[int] = Field(0)

class EmailStatusData(BaseModel):
    message_id: str = Field(..., example="uuid-1234-5678")
    status: str = Field(..., example="queued")  
    recipient: EmailStr = Field(..., example="user@example.com")
    subject: str = Field(..., example="Welcome to Our Service")
    sent_at: Optional[datetime] = Field(None)
    delivery_info: EmailStatusDeliveryInfo = Field(default_factory=EmailStatusDeliveryInfo)

class EmailStatusResponse(BaseModel):
    success: bool = Field(..., example=True)
    data: EmailStatusData
    message: Optional[str] = Field(None)

class HealthDependencies(BaseModel):
    rabbitmq: str = Field(..., example="connected")
    smtp: str = Field(..., example="connected")
    template_service: str = Field(..., example="connected")

class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    timestamp: datetime
    service: str = Field(..., example="email-service")
    dependencies: HealthDependencies

class MetricsData(BaseModel):
    emails_sent_today: int = Field(..., example=1000)
    emails_failed_today: int = Field(..., example=50)
    queue_length: int = Field(..., example=10)
    average_processing_time: float = Field(..., example=0.45)
    smtp_errors: int = Field(..., example=5)

class MetricsResponse(BaseModel):
    success: bool = Field(..., example=True)
    data: MetricsData
    message: Optional[str] = Field(None)
