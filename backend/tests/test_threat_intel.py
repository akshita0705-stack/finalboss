import pytest
from app.services.threat_intel_service import (
    MockThreatIntelProvider,
    GoogleSafeBrowsingProvider,
    ThreatIntelService,
)
from app.models.threat_indicator import ThreatIndicator


@pytest.mark.asyncio
async def test_mock_threat_intel_provider_verdicts():
    provider = MockThreatIntelProvider()

    # Malicious
    mal_res = await provider.lookup("testsafebrowsing.appspot.com")
    assert mal_res.verdict == "malicious"
    assert mal_res.confidence == "high"

    # Clean
    clean_res = await provider.lookup("google.com")
    assert clean_res.verdict == "clean"

    # Unknown
    unk_res = await provider.lookup("unrecorded-domain-123456.org")
    assert unk_res.verdict == "unknown"


@pytest.mark.asyncio
async def test_threat_intel_caching_in_postgres(db_session):
    service = ThreatIntelService()
    service.provider = MockThreatIntelProvider()

    # Perform lookup and cache
    res = await service.lookup_and_cache(db_session, "testsafebrowsing.appspot.com")
    assert res.verdict == "malicious"

    # Verify cached in DB
    cached = db_session.query(ThreatIndicator).filter(
        ThreatIndicator.normalized_value == "testsafebrowsing.appspot.com"
    ).first()
    assert cached is not None
    assert cached.verdict == "malicious"

    # Second lookup should hit cache
    cached_res = await service.lookup_and_cache(db_session, "testsafebrowsing.appspot.com")
    assert cached_res.is_live_lookup is False
    assert "Cached" in cached_res.attribution


@pytest.mark.asyncio
async def test_safe_browsing_timeout_never_marks_safe():
    # Instantiate provider with unconfigured key to verify disabled/unknown status
    provider = GoogleSafeBrowsingProvider(api_key=None)
    res = await provider.lookup("any-site.com")
    # Must NOT be marked clean
    assert res.verdict == "unknown"
    assert res.response_status == "disabled"

