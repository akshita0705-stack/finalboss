import os
import json
from typing import List, Optional, Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "TraceGuard AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./traceguard.db"

    # Security
    SECRET_KEY: str = "dev-traceguard-super-secret-key-change-in-production-min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Extension Auth
    EXTENSION_API_KEY: str = "tg_ext_dev_secret_key_987654321"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on", "debug")
        return bool(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Threat Intelligence
    THREAT_INTEL_ENABLED: bool = False
    THREAT_INTEL_PROVIDER: str = "mock"  # "mock" or "safebrowsing"
    GOOGLE_SAFE_BROWSING_API_KEY: Optional[str] = None
    THREAT_INTEL_CACHE_HOURS: int = 24

    # TigerGraph
    TIGERGRAPH_ENABLED: bool = False
    TIGERGRAPH_USE_MOCK: bool = True
    TIGERGRAPH_HOST: str = "http://127.0.0.1:9000"
    TIGERGRAPH_GRAPHNAME: str = "TraceGuardGraph"
    TIGERGRAPH_USERNAME: str = "tigergraph"
    TIGERGRAPH_PASSWORD: str = "tigergraph"
    TIGERGRAPH_SECRET: Optional[str] = None
    TIGERGRAPH_TOKEN: Optional[str] = None

    # AI Investigation Agent
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "fallback"  # "gemini", "openai", "fallback"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Data Retention & Rate Limits
    DATA_RETENTION_DAYS: int = 90
    RATE_LIMIT_PER_MINUTE: int = 120

    # Risk Scoring Thresholds
    RISK_THRESHOLD_LOW: int = 25
    RISK_THRESHOLD_MEDIUM: int = 50
    RISK_THRESHOLD_HIGH: int = 75
    RISK_THRESHOLD_CRITICAL: int = 90


settings = Settings()
