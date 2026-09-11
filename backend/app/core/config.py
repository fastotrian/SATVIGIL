"""
SATVIGIL — Central Configuration
All values read from environment variables (set in .env file).
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "satvigil"
    POSTGRES_USER: str = "satvigil_user"
    POSTGRES_PASSWORD: str = "satvigil_pass"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # NASA FIRMS
    FIRMS_MAP_KEY: str = ""
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    # India bounding box: lon_min, lat_min, lon_max, lat_max
    INDIA_BBOX: str = "68.1766451354,7.96553477623,97.4025614766,35.4940095078"

    # AIS
    AISHUB_USERNAME: str = ""
    AISHUB_PASSWORD: str = ""
    GFW_API_TOKEN: str = ""

    # Copernicus/Sentinel
    COPERNICUS_CLIENT_ID: str = ""
    COPERNICUS_CLIENT_SECRET: str = ""

    # Mapbox
    VITE_MAPBOX_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Data fetch intervals (seconds)
    FIRMS_FETCH_INTERVAL_SECONDS: int = 10800   # 3 hours
    AIS_FETCH_INTERVAL_SECONDS: int = 900        # 15 minutes
    SENTINEL_FETCH_INTERVAL_SECONDS: int = 86400 # 24 hours

    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore"


settings = Settings()
