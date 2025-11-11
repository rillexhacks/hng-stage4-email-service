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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            logger.info("🚀 Starting RabbitMQ consumer in thread...")
            loop.run_until_complete(async_email_consumer.connect())
            loop.run_until_complete(redis_client.connect())
            from src.db.main import init_db
            loop.run_until_complete(init_db())
            logger.info("✅ Database tables created in consumer thread")
            loop.run_until_complete(async_email_consumer.start_consuming())
            
        except Exception as e:
            logger.error(f"❌ Consumer thread failed: {str(e)}")
        finally:
            loop.close()
    
    # Actually start the thread
    consumer_thread = threading.Thread(target=run_consumer, daemon=True)
    consumer_thread.start()
    return consumer_thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    """
    # Startup
    logger.info("🚀 Starting Email Service...")
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


# app.include_router(router, tags=["email-service"])




if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI app
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development"
    )