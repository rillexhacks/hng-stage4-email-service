
from pydantic_settings import BaseSettings
from pydantic import EmailStr, Field


class Settings(BaseSettings):
    
    # Service Configuration
    service_name: str = "email-service"
    service_port: int = 8002
    environment: str = "development"
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:admin@localhost:5432/email_db",
        description="PostgreSQL connection string"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching"
    )
    
    # RabbitMQ Configuration
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    email_queue_name: str = "email.queue"
    failed_queue_name: str = "email.failed.queue"
    
    # Template Service
    template_service_url: str = Field(
        default="http://localhost:8004",
        description="Base URL for Template Service"
    )
    
    # SMTP Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: EmailStr = Field(
        default="your-email@gmail.com",
        description="SMTP username (email address)"
    )
    smtp_password: str = Field(
        default="your-app-password",
        description="SMTP password or app-specific password"
    )
    smtp_from: EmailStr = Field(
        default="noreply@yourapp.com",
        description="From email address"
    )
    smtp_from_name: str = "Your App Notifications"
    
    # Retry Configuration
    max_retry_attempts: int = 5
    initial_retry_delay: int = 1  # seconds
    max_retry_delay: int = 300  # 5 minutes
    backoff_multiplier: int = 2
    
    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 30  # seconds
    circuit_breaker_half_open_attempts: int = 1
    
    # Idempotency Configuration
    idempotency_ttl: int = 86400  # 24 hours
    
    # Logging Configuration
    log_level: str = "INFO"
    
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