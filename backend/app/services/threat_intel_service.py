from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.threat_indicator import ThreatIndicator
from app.db.base import utc_now


@dataclass
class ThreatIntelResult:
    provider: str
    target_value: str
    target_type: str  # domain, url, ip
    verdict: str      # malicious, clean, unknown, provider_error
    confidence: str   # high, medium, low
    response_status: str  # success, timeout, error, rate_limited, disabled
    raw_details: Dict[str, Any]
    observed_at: datetime
    expires_at: datetime
    attribution: str
    is_live_lookup: bool = True


class BaseThreatIntelProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def lookup(self, value: str, target_type: str = "domain") -> ThreatIntelResult:
        pass


class MockThreatIntelProvider(BaseThreatIntelProvider):
    """
    Mock threat intelligence adapter for offline testing and local development.
    Uses an explicit, small list of known test malicious and test clean domains.
    """

    MOCK_MALICIOUS_DOMAINS = {
        "malware-traffic-analysis.net",
        "testsafebrowsing.appspot.com",
        "ianfette.org",
        "phishing-test-site.badsite.org",
    }

    MOCK_CLEAN_DOMAINS = {
        "google.com",
        "github.com",
        "microsoft.com",
        "wikipedia.org",
    }

    @property
    def provider_name(self) -> str:
        return "mock_threat_intel"

    async def lookup(self, value: str, target_type: str = "domain") -> ThreatIntelResult:
        now = utc_now()
        expires = now + timedelta(hours=settings.THREAT_INTEL_CACHE_HOURS)
        normalized = value.lower().strip()

        if normalized in self.MOCK_MALICIOUS_DOMAINS or "badsite" in normalized:
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="malicious",
                confidence="high",
                response_status="success",
                raw_details={"threat_types": ["MALWARE", "SOCIAL_ENGINEERING"], "source": "mock_database"},
                observed_at=now,
                expires_at=expires,
                attribution="TraceGuard Mock Threat Intelligence (Local Test Suite)",
                is_live_lookup=True,
            )
        elif normalized in self.MOCK_CLEAN_DOMAINS:
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="clean",
                confidence="medium",
                response_status="success",
                raw_details={"threat_types": [], "source": "mock_database"},
                observed_at=now,
                expires_at=expires,
                attribution="TraceGuard Mock Threat Intelligence (Local Test Suite)",
                is_live_lookup=True,
            )
        else:
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="unknown",
                confidence="low",
                response_status="success",
                raw_details={"threat_types": [], "info": "Domain not present in mock feed"},
                observed_at=now,
                expires_at=expires,
                attribution="TraceGuard Mock Threat Intelligence (Local Test Suite)",
                is_live_lookup=True,
            )


class GoogleSafeBrowsingProvider(BaseThreatIntelProvider):
    """
    Google Safe Browsing v4 Threat Intelligence Adapter.
    Requires GOOGLE_SAFE_BROWSING_API_KEY environment variable.
    """

    API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_SAFE_BROWSING_API_KEY

    @property
    def provider_name(self) -> str:
        return "google_safebrowsing"

    async def lookup(self, value: str, target_type: str = "domain") -> ThreatIntelResult:
        now = utc_now()
        expires = now + timedelta(hours=settings.THREAT_INTEL_CACHE_HOURS)

        if not self.api_key:
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="unknown",
                confidence="low",
                response_status="disabled",
                raw_details={"error": "Google Safe Browsing API key not configured"},
                observed_at=now,
                expires_at=expires,
                attribution="Google Safe Browsing (Unconfigured)",
                is_live_lookup=False,
            )

        url_to_test = value if value.startswith("http") else f"https://{value}/"
        payload = {
            "client": {
                "clientId": "traceguard-ai",
                "clientVersion": "1.0.0",
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url_to_test}],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(
                    f"{self.API_URL}?key={self.api_key}",
                    json=payload,
                )

                if resp.status_code == 429:
                    logger.warning("Google Safe Browsing rate limit reached (HTTP 429)")
                    return ThreatIntelResult(
                        provider=self.provider_name,
                        target_value=value,
                        target_type=target_type,
                        verdict="unknown",
                        confidence="low",
                        response_status="rate_limited",
                        raw_details={"status_code": 429, "error": "Rate limit exceeded"},
                        observed_at=now,
                        expires_at=now + timedelta(minutes=15),
                        attribution="Google Safe Browsing",
                        is_live_lookup=False,
                    )
                elif resp.status_code != 200:
                    logger.error(f"Google Safe Browsing API error: HTTP {resp.status_code}")
                    return ThreatIntelResult(
                        provider=self.provider_name,
                        target_value=value,
                        target_type=target_type,
                        verdict="unknown",
                        confidence="low",
                        response_status="error",
                        raw_details={"status_code": resp.status_code, "body": resp.text[:200]},
                        observed_at=now,
                        expires_at=now + timedelta(minutes=15),
                        attribution="Google Safe Browsing",
                        is_live_lookup=False,
                    )

                data = resp.json()
                matches = data.get("matches", [])

                if matches:
                    threat_types = [m.get("threatType") for m in matches]
                    return ThreatIntelResult(
                        provider=self.provider_name,
                        target_value=value,
                        target_type=target_type,
                        verdict="malicious",
                        confidence="high",
                        response_status="success",
                        raw_details={"matches": matches, "threat_types": threat_types},
                        observed_at=now,
                        expires_at=expires,
                        attribution="Google Safe Browsing v4",
                        is_live_lookup=True,
                    )
                else:
                    return ThreatIntelResult(
                        provider=self.provider_name,
                        target_value=value,
                        target_type=target_type,
                        verdict="clean",
                        confidence="high",
                        response_status="success",
                        raw_details={"matches": []},
                        observed_at=now,
                        expires_at=expires,
                        attribution="Google Safe Browsing v4",
                        is_live_lookup=True,
                    )

        except httpx.TimeoutException:
            logger.warning(f"Google Safe Browsing lookup timed out for {value}")
            # NEVER mark safe on timeout
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="unknown",
                confidence="low",
                response_status="timeout",
                raw_details={"error": "Lookup request timed out"},
                observed_at=now,
                expires_at=now + timedelta(minutes=10),
                attribution="Google Safe Browsing",
                is_live_lookup=False,
            )
        except Exception as e:
            logger.error(f"Google Safe Browsing lookup unexpected exception: {e}")
            return ThreatIntelResult(
                provider=self.provider_name,
                target_value=value,
                target_type=target_type,
                verdict="unknown",
                confidence="low",
                response_status="error",
                raw_details={"error": str(e)},
                observed_at=now,
                expires_at=now + timedelta(minutes=10),
                attribution="Google Safe Browsing",
                is_live_lookup=False,
            )


class ThreatIntelService:
    """
    Coordinates threat intelligence lookups with caching in PostgreSQL.
    """

    def __init__(self):
        if settings.THREAT_INTEL_PROVIDER == "safebrowsing" and settings.GOOGLE_SAFE_BROWSING_API_KEY:
            self.provider: BaseThreatIntelProvider = GoogleSafeBrowsingProvider()
        else:
            self.provider = MockThreatIntelProvider()

    def get_cached_indicator(self, db: Session, value: str, target_type: str = "domain") -> Optional[ThreatIndicator]:
        now = utc_now()
        indicator = (
            db.query(ThreatIndicator)
            .filter(
                ThreatIndicator.normalized_value == value.lower().strip(),
                ThreatIndicator.indicator_type == target_type,
                ThreatIndicator.expires_at > now,
            )
            .first()
        )
        return indicator

    async def lookup_and_cache(
        self, db: Session, value: str, target_type: str = "domain", force_refresh: bool = False
    ) -> ThreatIntelResult:
        normalized = value.lower().strip()

        if not force_refresh:
            cached = self.get_cached_indicator(db, normalized, target_type)
            if cached:
                return ThreatIntelResult(
                    provider=cached.provider,
                    target_value=cached.normalized_value,
                    target_type=cached.indicator_type,
                    verdict=cached.verdict,
                    confidence=cached.confidence,
                    response_status=cached.response_status,
                    raw_details=cached.raw_details,
                    observed_at=cached.observed_at,
                    expires_at=cached.expires_at,
                    attribution=f"{cached.provider} (Cached)",
                    is_live_lookup=False,
                )

        # Execute provider lookup
        result = await self.provider.lookup(normalized, target_type)

        # Store or update in PostgreSQL ThreatIndicator table
        existing = (
            db.query(ThreatIndicator)
            .filter(
                ThreatIndicator.normalized_value == normalized,
                ThreatIndicator.indicator_type == target_type,
                ThreatIndicator.provider == result.provider,
            )
            .first()
        )

        if existing:
            existing.verdict = result.verdict
            existing.confidence = result.confidence
            existing.response_status = result.response_status
            existing.raw_details = result.raw_details
            existing.observed_at = result.observed_at
            existing.expires_at = result.expires_at
        else:
            new_indicator = ThreatIndicator(
                indicator_type=result.target_type,
                normalized_value=normalized,
                provider=result.provider,
                verdict=result.verdict,
                confidence=result.confidence,
                response_status=result.response_status,
                raw_details=result.raw_details,
                observed_at=result.observed_at,
                expires_at=result.expires_at,
            )
            db.add(new_indicator)

        db.commit()
        return result


threat_intel_service = ThreatIntelService()

