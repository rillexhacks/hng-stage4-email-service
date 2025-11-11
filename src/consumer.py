import asyncio
import json
import logging
from typing import Optional

from aio_pika import connect_robust, IncomingMessage
import aio_pika
from aio_pika.abc import AbstractIncomingMessage

import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import settings, get_rabbitmq_url
from .schemas import DirectEmailRequest, EmailResponseData
from .db.main import get_db
from .models import EmailLog, EmailStatus
from .email_sender import email_sender
from .redis_client import redis_client
from .circuit_breaker import CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class AsyncEmailConsumer:

    def __init__(self):
        self.queue_name = settings.email_queue_name
        self.failed_queue_name = settings.failed_queue_name
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            self.connection = await connect_robust(
                get_rabbitmq_url()
            )
            self.channel = await self.connection.channel()

            # Ensure only 1 message is processed at a time per worker
            await self.channel.set_qos(prefetch_count=1)

            # Declare queues
            await self.channel.declare_queue(self.queue_name, durable=True)
            await self.channel.declare_queue(self.failed_queue_name, durable=True)

            logger.info("Connected to RabbitMQ successfully (async)")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def start_consuming(self):
      
        queue = await self.channel.declare_queue(self.queue_name, durable=True)
        logger.info(f"Starting async consumption from queue: {self.queue_name}")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():  # auto-ack
                    await self.process_message(message)

    async def process_message(self, message: AbstractIncomingMessage):
        """
        Process a single message from the queue
        """
        request_id = None
        try:
            body = message.body.decode()
            data = json.loads(body)

            # Validate with your DirectEmailRequest schema
            email_request = DirectEmailRequest(**data)
            request_id = data.get("request_id", "unknown")

            logger.info(
                f"Received email message. Request ID: {request_id}, Recipient: {email_request.to_email}"
            )

            success = await self._process_email_async(
                email_request=email_request,
                request_id=request_id,
                additional_data=data, 
            )

            if not success:
                await self._handle_failure(data, request_id)

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}. Request ID: {request_id}")
            await message.reject(requeue=True)

    async def _process_email_async(self, email_request: DirectEmailRequest, 
                                request_id: str, additional_data: dict) -> bool:
        try:
            # 1. Idempotency check
            if await redis_client.is_processed(request_id):
                logger.warning(f"Duplicate email. Request ID: {request_id}")
                return True

           
            async with get_db() as db:
                email_log = EmailLog(
                    request_id=request_id,
                    recipient=email_request.to_email,
                    subject=email_request.subject,
                    body_text=email_request.content,
                    body_html=email_request.html_content,
                    status=EmailStatus.PROCESSING
                )
                db.add(email_log)
                await db.commit()
                await db.refresh(email_log)
                log_id = email_log.id

            # 3. Send email directly using the schema data
            await email_sender.send_email(
                recipient=email_request.to_email,
                subject=email_request.subject,
                body_html=email_request.html_content or email_request.content,
                body_text=email_request.content,
                request_id=request_id,
            )

           
            async with get_db() as db:
                email_log = await db.get(EmailLog, log_id)
                email_log.status = EmailStatus.SENT
                await db.commit()

            # 5. Mark as processed in Redis
            await redis_client.mark_as_processed(request_id)

            logger.info(f"✅ Email sent successfully! Request ID: {request_id}")
            return True

        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open. Will retry later. Request ID: {request_id}")
            return False

        except Exception as e:

            try:
                from sqlalchemy import select, update
                async with get_db() as db:
                    # Use proper SQLAlchemy 2.0 syntax
                    stmt = select(EmailLog).where(EmailLog.request_id == request_id)
                    result = await db.execute(stmt)
                    email_log = result.scalar_one_or_none()
                    
                    if email_log:
                        email_log.status = EmailStatus.FAILED
                        email_log.error_message = str(e)
                        email_log.retry_count += 1
                        await db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update DB: {str(db_error)}")

            logger.error(f"Email processing failed: {str(e)}. Request ID: {request_id}")
            return False

    async def _handle_failure(self, data: dict, request_id: str):
        """Handle failed messages: retry or move to dead-letter"""
      
        async with get_db() as db:
            from sqlalchemy import select
            stmt = select(EmailLog).where(EmailLog.request_id == request_id)
            result = await db.execute(stmt)
            email_log = result.scalar_one_or_none()
            retry_count = email_log.retry_count if email_log else 0

        retry_count = 0  # Temporary fix

        if retry_count >= settings.max_retry_attempts:
            logger.error(f"Max retries reached. Moving to failed queue. Request ID: {request_id}")
            failed_queue = await self.channel.declare_queue(self.failed_queue_name, durable=True)
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(data).encode()),
                routing_key=self.failed_queue_name
            )
        else:
            logger.warning(f"Will retry email. Request ID: {request_id}")


# Global instance
async_email_consumer = AsyncEmailConsumer()


async def main():
    await async_email_consumer.connect()
    await async_email_consumer.start_consuming()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
