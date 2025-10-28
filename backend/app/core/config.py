from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = "dev-secret"
    QR_SECRET: str = "dev-qr"

    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio12345"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_TICKETS: str = "tickets-pdf"

    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "tickets@example.local"

settings = Settings()
