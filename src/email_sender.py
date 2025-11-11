import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from .config import settings
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class EmailSender:

    def __init__(self):
        """Initialize email sender with circuit breaker"""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from
        self.from_name = settings.smtp_from_name

        # Initialize circuit breaker for SMTP
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout=settings.circuit_breaker_timeout,
            half_open_attempts=settings.circuit_breaker_half_open_attempts,
            name="smtp",
        )

        logger.info(
            f"Email sender initialized: "
            f"SMTP={self.smtp_host}:{self.smtp_port}, "
            f"From={self.from_email}"
        )

    async def send_email(
        self,
        recipient: str,
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        try:
            # Use circuit breaker to prevent cascading failures
            return await self.circuit_breaker.call_async(
                self._send_email_async,  
                recipient=recipient,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                request_id=request_id,
            )

        except CircuitBreakerOpenError as e:
            logger.error(
                f" Circuit breaker is OPEN. "
                f"Cannot send email to {recipient}. "
                f"Request ID: {request_id}"
            )
            raise

        except Exception as e:
            logger.error(
                f" Failed to send email to {recipient}. "
                f"Error: {str(e)}. Request ID: {request_id}"
            )
            raise


    async def _send_email_async(
        self,
        recipient: str,
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
            
      
        # Create message container
        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = recipient
        message["Subject"] = subject

        # Add request ID to headers for tracking
        if request_id:
            message["X-Request-ID"] = request_id

        # Add plain text body
        if body_text:
            part_text = MIMEText(body_text, "plain", "utf-8")
            message.attach(part_text)

        # Add HTML body
        if body_html:
            part_html = MIMEText(body_html, "html", "utf-8")
            message.attach(part_html)

        # If neither provided, use empty text
        if not body_text and not body_html:
            part_text = MIMEText("", "plain", "utf-8")
            message.attach(part_text)

        try:
            # Send email using aiosmtplib
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True,  
                timeout=30,
            )
            logger.info(
                f" Email sent successfully to {recipient}. "
                f"Subject: '{subject}'. Request ID: {request_id}"
            )
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(
                f" SMTP error sending to {recipient}: {str(e)}. "
                f"Request ID: {request_id}"
            )
            raise

        except Exception as e:
            logger.error(
                f" Unexpected error sending to {recipient}: {str(e)}. "
                f"Request ID: {request_id}"
            )
            raise

    async def test_connection(self) -> bool:
     
        try:
            # Try to connect and authenticate
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host, port=self.smtp_port, timeout=10
            ) as smtp:
                await smtp.starttls()
                await smtp.login(self.smtp_user, self.smtp_password)

            logger.info(" SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f" SMTP connection test failed: {str(e)}")
            return False

    def get_circuit_breaker_status(self) -> dict:
       
        return self.circuit_breaker.get_state()


# Global email sender instance
email_sender = EmailSender()
