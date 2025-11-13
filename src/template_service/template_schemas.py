# src/template_schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Union
from datetime import datetime
from enum import Enum
from uuid import UUID

class TemplateType(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"

class TemplateStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"

# Request Schemas
class TemplateCreate(BaseModel):
    template_code: str = Field(..., example="welcome_email")
    name: str = Field(..., example="Welcome Email")
    description: Optional[str] = Field(None, example="Sent to new users after signup")
    subject: str = Field(..., example="Welcome to Our Service, {{name}}!")
    body_html: str = Field(..., example="<h1>Welcome {{name}}!</h1><p>Your order {{order_id}} is confirmed.</p>")
    body_text: Optional[str] = Field(None, example="Welcome {{name}}! Your order {{order_id}} is confirmed.")
    template_type: TemplateType = Field(default=TemplateType.EMAIL)
    language: str = Field(default="en", example="en")
    variables: List[str] = Field(default=[], example=["name", "order_id"])
    created_by: Optional[str] = Field(None, example="system")

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    status: Optional[TemplateStatus] = None
    change_reason: Optional[str] = None

class TemplateRenderRequest(BaseModel):
    template_code: str = Field(..., example="welcome_email")
    language: Optional[str] = Field("en", example="en")
    variables: Dict[str, str] = Field(..., example={"name": "John Doe", "order_id": "12345"})

# Response Schemas
class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Union[str, UUID]
    template_code: str
    name: str
    description: Optional[str]
    subject: str
    body_html: str
    body_text: Optional[str]
    template_type: TemplateType
    language: str
    variables: List[str]
    status: TemplateStatus
    version: int
    is_current: bool
    created_at: datetime
    updated_at: datetime

class RenderedTemplate(BaseModel):
    template_code: str
    language: str
    subject: str
    body_html: str
    body_text: Optional[str]

class TemplateVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: Union[str, UUID]
    template_code: str
    version: int
    subject: str
    body_html: str
    body_text: Optional[str]
    change_reason: Optional[str]
    created_at: datetime