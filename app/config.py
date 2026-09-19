import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AgriSensa Harvest Intelligence API"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://app.agrisensa.ai"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/agrisensa_harvest"
    
    # Clerk Authentication
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: str = "pk_test_dm9jYWwtc2Vhc25haWwtNDU0My5jbGVyay5hY2NvdW50cy5kZXYk"
    CLERK_PUBLISHABLE_KEY: str = "pk_test_dm9jYWwtc2Vhc25haWwtNDU0My5jbGVyay5hY2NvdW50cy5kZXYk"
    CLERK_SECRET_KEY: str = "sk_test_P73AFF9FSijCnvmaRIqZGEsHtBOkWjpSsWHZCLeGYR"
    CLERK_JWT_KEY: str = ""

    # Google Workspace & Drive Integration
    GOOGLE_DRIVE_WEBHOOK_URL: str = "" # URL Web App dari Google Apps Script (Sederhana & Tanpa GCP)
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "" # Raw JSON credential string (Opsional untuk GCP)
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "credentials.json" # Path to local JSON file
    GOOGLE_DRIVE_ROOT_FOLDER_ID: str = "" # ID folder root di Google Drive
    GOOGLE_DRIVE_FOLDER_NAME: str = "AgriSensa_Harvest_Reports"
    
    # Notification & Webhook Integration (WhatsApp / Telegram / Slack / n8n)
    NOTIFICATION_ENABLED: bool = True
    WEBHOOK_URL: str = "" # WhatsApp gateway / Discord / Slack / n8n webhook
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    N8N_WEBHOOK_HARVEST_CREATED: str = ""
    N8N_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

