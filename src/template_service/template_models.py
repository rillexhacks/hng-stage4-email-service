# src/template_models.py
from sqlalchemy import Column, String, Text, JSON, Integer, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import uuid

TemplateBase = declarative_base()
class TemplateStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"

class TemplateType(str, enum.Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"

class EmailTemplate(TemplateBase):
    __tablename__ = "email_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    subject = Column(String, nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text)
    template_type = Column(Enum(TemplateType), default=TemplateType.EMAIL, nullable=False)
    language = Column(String, default="en", nullable=False)
    variables = Column(JSON)  # Expected variables: ["name", "order_id", "amount"]
    status = Column(Enum(TemplateStatus), default=TemplateStatus.ACTIVE, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class TemplateVersion(TemplateBase):
    __tablename__ = "template_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    subject = Column(String, nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text)
    variables = Column(JSON)
    change_reason = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())