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
    
    N8N_WEBHOOK_HARVEST_CREATED: str = ""
    N8N_WEBHOOK_SECRET: str = ""
    GOOGLE_DRIVE_HARVEST_FOLDER_ID: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
