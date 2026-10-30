import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_MIN_SEVERITY = {"low", "medium", "high", "critical"}
ALLOWED_NOTIFICATION_KEYS = {"browser_notifications", "min_severity"}

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    monitoring_enabled: bool
    excluded_domains: List[str]
    retention_days: int
    notification_preferences: Dict[str, Any]
    updated_at: Optional[datetime] = None


class UserSettingsUpdate(BaseModel):
    monitoring_enabled: Optional[bool] = None
    excluded_domains: Optional[List[str]] = Field(default=None, max_length=200)
    retention_days: Optional[int] = Field(default=None, ge=1, le=365)
    notification_preferences: Optional[Dict[str, Any]] = None

    @field_validator("excluded_domains")
    @classmethod
    def clean_domains(cls, value: Optional[List[str]]):
        if value is None:
            return value
        cleaned: List[str] = []
        for raw in value:
            item = raw.strip().lower().rstrip(".")
            if item.startswith("*."):
                item = item[2:]
            try:
                item = item.encode("idna").decode("ascii")
            except UnicodeError:
                raise ValueError(f"Invalid domain: {raw!r}")
            if not _DOMAIN_RE.match(item):
                raise ValueError(f"Invalid domain: {raw!r}")
            if item not in cleaned:
                cleaned.append(item)
        return cleaned

    @field_validator("notification_preferences")
    @classmethod
    def check_notifications(cls, value: Optional[Dict[str, Any]]):
        if value is None:
            return value
        unknown = set(value) - ALLOWED_NOTIFICATION_KEYS
        if unknown:
            raise ValueError(f"Unknown notification keys: {sorted(unknown)}")
        if "browser_notifications" in value and not isinstance(value["browser_notifications"], bool):
            raise ValueError("browser_notifications must be true or false")
        if "min_severity" in value and value["min_severity"] not in ALLOWED_MIN_SEVERITY:
            raise ValueError("min_severity must be one of: low, medium, high, critical")
        return value