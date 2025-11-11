# src/routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from src.db.main import get_db
from src.schemas import (
    DirectEmailRequest,
    EmailResponse,
    EmailResponseData,
    EmailStatusResponse,
    EmailStatusData,
    EmailStatusDeliveryInfo,
)
from src.models import EmailLog, EmailStatus
from src.email_sender import create_email_sender
from src.redis_client import redis_client
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


@router.post("/send", response_model=EmailResponse)
async def send_email(
    email_request: DirectEmailRequest, db: AsyncSession = Depends(get_db)
):
    request_id = f"api_{uuid.uuid4().hex[:12]}"
    email_sender = create_email_sender()

    try:
        # Check idempotency
        if await redis_client.is_processed(request_id):
            raise HTTPException(
                status_code=400,
                detail=f"Email with request_id '{request_id}' was already processed",
            )

        # Create database log entry (ASYNC WAY)
        email_log = EmailLog(
            request_id=request_id,
            recipient=email_request.to_email,
            subject=email_request.subject,
            body_text=email_request.content,
            body_html=email_request.html_content,
            status=EmailStatus.PROCESSING,
            email_metadata={"source": "api", "from_email": email_request.from_email},
        )

        # Async database operations
        db.add(email_log)
        await db.commit()
        await db.refresh(email_log)

        # Send email
        success = await email_sender.send_email(
            recipient=email_request.to_email,
            subject=email_request.subject,
            body_html=email_request.html_content or email_request.content,
            body_text=email_request.content,
            request_id=request_id,
        )

        # Update database status (ASYNC WAY)
        if success:
            email_log.status = EmailStatus.SENT
            email_log.sent_at = datetime.utcnow()
        else:
            email_log.status = EmailStatus.FAILED
            email_log.error_message = "Failed to send email"

        await db.commit()

        # Mark as processed in Redis
        await redis_client.mark_as_processed(request_id)

        return EmailResponse(
            success=True,
            data=EmailResponseData(
                message_id=request_id,
                status="sent" if success else "failed",
                service_response="Email queued successfully",
                timestamp=datetime.utcnow(),
            ),
            message="Email sent successfully" if success else "Email failed to send",
        )

    except Exception as e:
        # Update database on error (ASYNC WAY)
        try:
            result = await db.execute(
                select(EmailLog).where(EmailLog.request_id == request_id)
            )
            email_log = result.scalar_one_or_none()
            if email_log:
                email_log.status = EmailStatus.FAILED
                email_log.error_message = str(e)
                await db.commit()
        except:
            pass

        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/status/{request_id}", response_model=EmailStatusResponse)
async def get_email_status(request_id: str, db: AsyncSession = Depends(get_db)):
   
    # Async database query
    result = await db.execute(select(EmailLog).where(EmailLog.request_id == request_id))
    email_log = result.scalar_one_or_none()

    if not email_log:
        raise HTTPException(
            status_code=404, detail=f"Email with request_id '{request_id}' not found"
        )

    return EmailStatusResponse(
        success=True,
        data=EmailStatusData(
            message_id=email_log.request_id,
            status=email_log.status.value,
            recipient=email_log.recipient,
            subject=email_log.subject,
            sent_at=email_log.sent_at,
            delivery_info=EmailStatusDeliveryInfo(
                retry_count=email_log.retry_count, error_message=email_log.error_message
            ),
        ),
        message="Email status retrieved successfully",
    )


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    redis_healthy = (
        redis_client._connected if hasattr(redis_client, "_connected") else False
    )

    email_sender = create_email_sender()
    email_service_healthy = email_sender.circuit_breaker.state.value != "open"

    database_healthy = False
    try:
        result = await db.execute(select(1))
        database_healthy = result.scalar() == 1
    except:
        database_healthy = False

    return {
        "status": (
            "healthy"
            if redis_healthy and email_service_healthy and database_healthy
            else "degraded"
        ),
        "timestamp": datetime.utcnow(),
        "service": "email-service",
        "dependencies": {
            "redis": "connected" if redis_healthy else "disconnected",
            "smtp": "healthy" if email_service_healthy else "unhealthy",
            "database": "connected" if database_healthy else "disconnected",
        },
    }


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    try:
        # Get counts by status - FIXED QUERY
        result = await db.execute(
            select(EmailLog.status, func.count(EmailLog.id))
            .group_by(EmailLog.status)
        )
        status_counts = result.all()
        
        # Get today's stats
        today = datetime.utcnow().date()
        result = await db.execute(
            select(EmailLog).where(EmailLog.created_at >= today)
        )
        today_emails = result.scalars().all()
        
        sent_today = len([e for e in today_emails if e.status == EmailStatus.SENT])
        failed_today = len([e for e in today_emails if e.status == EmailStatus.FAILED])
        
        # Create email sender for circuit breaker status
        email_sender = create_email_sender()
        
        return {
            "success": True,
            "data": {
                "emails_sent_today": sent_today,
                "emails_failed_today": failed_today,
                "total_emails": len(today_emails),
                "status_breakdown": {
                    status.value: count for status, count in status_counts
                },
                "circuit_breaker_status": email_sender.get_circuit_breaker_status()
            },
            "message": "Metrics retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )
