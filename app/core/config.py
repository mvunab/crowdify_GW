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

    # Resend Configuration (reemplaza MailHog)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "tickets@example.local"
    
    # SMTP Configuration (legacy, mantenido para compatibilidad)
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "tickets@example.local"

    # Mercado Pago Configuration
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    MERCADOPAGO_PUBLIC_KEY: str = ""
    MERCADOPAGO_WEBHOOK_SECRET: str = ""
    MERCADOPAGO_ENVIRONMENT: str = "sandbox"  # sandbox o production
    
    # Payku Configuration
    PAYKU_TOKEN_PUBLICO: str = ""
    PAYKU_TOKEN_PRIVADO: str = ""
    PAYKU_ENVIRONMENT: str = "sandbox"  # sandbox o production
    
    APP_BASE_URL: str = "http://localhost:3000"  # URL del frontend para redirects
    FRONTEND_URL: str = ""  # URL del frontend (puede ser ngrok o producción)
    FRONTEND_PRODUCTION_URL: str = "https://crodify.vercel.app"  # URL de producción del frontend (Vercel)
    NGROK_URL: str = ""  # URL de ngrok para webhooks en desarrollo (ej: https://xxx.ngrok-free.dev)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar campos extra en .env que no están en el modelo

settings = Settings()
