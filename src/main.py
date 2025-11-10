"""
Main Application File for Email Service

This starts:
1. FastAPI web server (health checks, metrics)
2. RabbitMQ consumer worker (email processing)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from contextlib import asynccontextmanager
import threading

from app.config import settings
from app.database import init_db
from app.routes import router
from app.consumer import email_consumer
from app.redis_client import redis_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def start_consumer():
    """
    Start RabbitMQ consumer in background thread
    
    This runs continuously, processing messages from the queue
    """
    try:
        logger.info("🚀 Starting RabbitMQ consumer thread...")
        email_consumer.connect()
        email_consumer.start_consuming()
    except Exception as e:
        logger.error(f"❌ Consumer thread failed: {str(e)}")
        sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    
    Startup:
    - Initialize database
    - Connect to Redis
    - Start consumer thread
    
    Shutdown:
    - Close connections gracefully
    """
    # Startup
    logger.info("🚀 Starting Email Service...")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        sys.exit(1)
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        # Continue anyway - idempotency will be disabled
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(
        target=start_consumer,
        daemon=True
    )
    consumer_thread.start()
    logger.info("✅ Consumer thread started")
    
    logger.info("✅ Email Service started successfully!")
    logger.info(f"🌐 API available at http://0.0.0.0:{settings.service_port}")
    logger.info(f"📚 API docs at http://0.0.0.0:{settings.service_port}/docs")
    
    yield
    
    # Shutdown
    logger.info("⏹️ Shutting down Email Service...")
    
    # Stop consumer
    try:
        email_consumer.stop_consuming()
        logger.info("✅ Consumer stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping consumer: {str(e)}")
    
    # Disconnect Redis
    try:
        await redis_client.disconnect()
        logger.info("✅ Redis disconnected")
    except Exception as e:
        logger.error(f"❌ Error disconnecting Redis: {str(e)}")
    
    logger.info("✅ Email Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Email Service",
    description="Email notification processing service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, tags=["email-service"])


# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "email-service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI app
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development"
    )