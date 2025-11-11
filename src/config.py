import os
from pydantic_settings import BaseSettings
from pydantic import EmailStr, Field


class Settings(BaseSettings):
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/email_service")
    
    # RabbitMQ - use container names in Docker

    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_user: str = os.getenv("RABBITMQ_USER", "guest")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    rabbitmq_vhost: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Email Service
    service_name: str = os.getenv("SERVICE_NAME", "email-service")
    service_port: int = int(os.getenv("SERVICE_PORT", "8002"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Template Service
    template_service_url: str = os.getenv("TEMPLATE_SERVICE_URL", "http://localhost:8004")
    
    # SMTP Configuration
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "Notification System")
    
    # Circuit Breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_half_open_attempts: int = 2
    
    # Retry Settings
    max_retry_attempts: int = 3
    initial_retry_delay: int = int(os.getenv("INITIAL_RETRY_DELAY", "1"))
    max_retry_delay: int = int(os.getenv("MAX_RETRY_DELAY", "300"))
    backoff_multiplier: int = int(os.getenv("BACKOFF_MULTIPLIER", "2"))
    
    # Idempotency Configuration
    idempotency_ttl: int = int(os.getenv("IDEMPOTENCY_TTL", "86400"))
    
    # Queue Names
    email_queue_name: str = "email.queue"
    failed_queue_name: str = "email.failed.queue"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_rabbitmq_url() -> str:
   
    return (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}"
        f"{settings.rabbitmq_vhost}"
    )