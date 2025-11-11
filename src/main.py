from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from contextlib import asynccontextmanager
import asyncio
import threading

import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.db.main import init_db
# from src.routes import router     # Comment out - don't have this yet
from src.consumer import async_email_consumer
from src.redis_client import redis_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def start_consumer_in_thread():
    """
    Start RabbitMQ consumer in background thread with its own event loop
    """
    def run_consumer():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            logger.info("🚀 Starting RabbitMQ consumer in thread...")
            loop.run_until_complete(async_email_consumer.connect())
            loop.run_until_complete(async_email_consumer.start_consuming())
        except Exception as e:
            logger.error(f"❌ Consumer thread failed: {str(e)}")
        finally:
            loop.close()

    consumer_thread = threading.Thread(
        target=run_consumer,
        daemon=True,
        name="email-consumer"
    )
    consumer_thread.start()
    return consumer_thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    """
    # Startup
    logger.info("🚀 Starting Email Service...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        # Continue without database for now
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        # Continue anyway - idempotency will be disabled
    
    # Start consumer
    consumer_thread = start_consumer_in_thread()
    
    logger.info("✅ Email Service started successfully!")
    logger.info(f"🌐 API available at http://0.0.0.0:{settings.service_port}")
    logger.info(f"📚 API docs at http://0.0.0.0:{settings.service_port}/docs")
    
    yield
    
    # Shutdown
    logger.info("⏹️ Shutting down Email Service...")
    
    # Stop consumer
    try:
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
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Comment out router for now - we'll create it later
# app.include_router(router, tags=["email-service"])


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