from sqlalchemy import Column, String, DateTime, Integer, Text, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class EmailStatus(str, enum.Enum):

    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class EmailLog(Base):

    __tablename__ = "email_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Unique Identifiers
    request_id = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique request ID for idempotency",
    )

    correlation_id = Column(
        String(255), index=True, comment="Correlation ID for tracing across services"
    )

    # Email Details
    recipient = Column(
        String(255), nullable=False, index=True, comment="Recipient email address"
    )

    subject = Column(String(500), nullable=False, comment="Email subject line")

    body_text = Column(Text, comment="Plain text email body")

    body_html = Column(Text, comment="HTML email body")

    template_id = Column(String(100), comment="Template ID used for this email")

    template_variables = Column(JSON, comment="Variables used for template rendering")

    # Status Tracking
    status = Column(
        Enum(EmailStatus),
        default=EmailStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current email delivery status",
    )

    retry_count = Column(Integer, default=0, comment="Number of retry attempts")

    max_retries = Column(Integer, default=5, comment="Maximum allowed retry attempts")

    # Error Handling
    error_message = Column(Text, comment="Error message if delivery failed")

    last_error_at = Column(DateTime(timezone=True), comment="Timestamp of last error")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the email was first queued",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )

    sent_at = Column(
        DateTime(timezone=True), comment="When the email was successfully sent"
    )

    # Metadata
    metadata = Column(JSON, comment="Additional metadata (user agent, IP, etc.)")

    def __repr__(self):
        return (
            f"<EmailLog(id={self.id}, "
            f"request_id={self.request_id}, "
            f"recipient={self.recipient}, "
            f"status={self.status})>"
        )
