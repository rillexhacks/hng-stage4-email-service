from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

# -------------------
# Queue Message Schemas
# -------------------

class QueueEmailMessage(BaseModel):
    """Schema for messages received from the queue - more flexible"""
    notification_id: Optional[str] = Field(None)
    player_id: Optional[str] = Field(None)
    to_email: Optional[EmailStr] = Field(None)
    from_email: Optional[EmailStr] = Field(None)
    subject: Optional[str] = Field(None)
    content: Optional[str] = Field(None)
    html_content: Optional[str] = Field(None)
    request_id: Optional[str] = Field(None)
    correlation_id: Optional[str] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Additional fields that might come from external services
    user_email: Optional[EmailStr] = Field(None)
    email: Optional[EmailStr] = Field(None)
    message: Optional[str] = Field(None)
    title: Optional[str] = Field(None)
    body: Optional[str] = Field(None)
    
    def to_direct_email_request(self) -> 'DirectEmailRequest':
        """Convert queue message to DirectEmailRequest with field mapping"""
        # Try to extract email from various possible fields
        recipient_email = (
            self.to_email or
            self.user_email or
            self.email
        )
        
        # Try to extract subject from various possible fields
        email_subject = (
            self.subject or
            self.title or
            "Notification"  # Default subject
        )
        
        # Try to extract content from various possible fields
        email_content = (
            self.content or
            self.message or
            self.body or
            "You have a new notification"  # Default content
        )
        
        if not recipient_email:
            raise ValueError("No valid email address found in message")
            
        return DirectEmailRequest(
            to_email=recipient_email,
            from_email=self.from_email or "noreply@company.com",
            subject=email_subject,
            content=email_content,
            html_content=self.html_content
        )

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
