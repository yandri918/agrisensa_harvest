import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AgriSensa Harvest Intelligence API"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://app.agrisensa.ai"
    ]
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/agrisensa_harvest"
    
    # Google Workspace & Drive Integration
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "" # Raw JSON credential string (Ideal for Railway environment)
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "credentials.json" # Path to local JSON file
    GOOGLE_DRIVE_ROOT_FOLDER_ID: str = "" # ID folder root di Google Drive
    GOOGLE_DRIVE_FOLDER_NAME: str = "AgriSensa_Harvest_Reports"
    
    N8N_WEBHOOK_HARVEST_CREATED: str = ""
    N8N_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

