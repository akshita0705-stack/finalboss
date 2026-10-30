import pytest
from app.services.url_normalizer import UrlNormalizer
from app.services.detection_service import detection_engine


def test_benign_domain_evaluation():
    norm = UrlNormalizer.normalize("https://google.com/search")
    assessment = detection_engine.assess_url(norm)
    assert assessment.risk_score == 0
    assert assessment.severity == "low"
    assert assessment.immediate_alert is False
    assert len(assessment.rules_triggered) == 0


def test_legitimate_brand_domain_not_flagged_as_lookalike():
    # Legitimate brand domains must NOT be identified as their own lookalike!
    norm = UrlNormalizer.normalize("https://paypal.com/signin")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_LOOKALIKE_DOMAIN" not in assessment.rules_triggered
    assert assessment.lookalike_candidate is None


def test_lookalike_domain_candidate_detection():
    # 'paypa1.com' vs 'paypal.com' (Levenshtein distance 1)
    norm = UrlNormalizer.normalize("https://paypa1.com/login")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_LOOKALIKE_DOMAIN" in assessment.rules_triggered
    assert assessment.lookalike_candidate is not None
    assert assessment.lookalike_candidate["target_domain"] == "paypal.com"
    assert assessment.lookalike_candidate["edit_distance"] == 1
    # Verify similarity alone does not claim guaranteed maliciousness
    assert "Lookalike candidate match alone does not prove malicious intent" in assessment.lookalike_candidate["disclaimer"]


def test_raw_ip_hostname_detection():
    norm = UrlNormalizer.normalize("http://192.168.1.50/admin")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_IP_HOST" in assessment.rules_triggered
    assert assessment.risk_score >= 40


def test_excessive_subdomain_depth():
    norm = UrlNormalizer.normalize("https://login.secure.update.account.evil.com/auth")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_EXCESSIVE_SUBDOMAINS" in assessment.rules_triggered


def test_deceptive_brand_and_action_keywords():
    norm = UrlNormalizer.normalize("http://paypal-security-login.randomsite.com/verify")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_DECEPTIVE_STRUCTURE" in assessment.rules_triggered
    assert assessment.severity in ("high", "critical")
    assert assessment.immediate_alert is True


def test_punycode_homograph_detection():
    norm = UrlNormalizer.normalize("http://xn--pple-43d.com/store")
    assessment = detection_engine.assess_url(norm)
    assert "RULE_HOMOGRAPH_PUNYCODE" in assessment.rules_triggered

