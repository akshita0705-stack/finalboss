import pytest
from app.services.url_normalizer import UrlNormalizer


def test_standard_url_normalization():
    norm = UrlNormalizer.normalize("HTTPS://WWW.EXAMPLE.COM/path/to/page")
    assert norm.is_valid is True
    assert norm.scheme == "https"
    assert norm.host == "www.example.com"
    assert norm.domain == "example.com"
    assert norm.subdomain == "www"
    assert norm.privacy_minimized_path == "/path"


def test_default_port_stripping():
    norm_http = UrlNormalizer.normalize("http://example.com:80/home")
    assert norm_http.port is None
    assert norm_http.sanitized_url == "http://example.com/home"

    norm_https = UrlNormalizer.normalize("https://example.com:443/secure")
    assert norm_https.port is None
    assert norm_https.sanitized_url == "https://example.com/secure"

    norm_custom = UrlNormalizer.normalize("http://example.com:8080/api")
    assert norm_custom.port == 8080
    assert norm_custom.sanitized_url == "http://example.com:8080/api"


def test_sensitive_query_parameter_redaction():
    url = "https://example.com/oauth/callback?token=secret123&session_id=sess99&safe_param=hello"
    norm = UrlNormalizer.normalize(url, strip_query_strings=False)
    assert norm.is_valid is True
    assert "token=%5BREDACTED%5D" in norm.sanitized_url or "token=[REDACTED]" in norm.sanitized_url
    assert "session_id=%5BREDACTED%5D" in norm.sanitized_url or "session_id=[REDACTED]" in norm.sanitized_url
    assert "safe_param=hello" in norm.sanitized_url


def test_idna_punycode_handling():
    # Apple unicode spoof (xn--pple-43d.com)
    norm = UrlNormalizer.normalize("http://xn--pple-43d.com/login")
    assert norm.is_valid is True
    assert norm.is_punycode is True
    assert "xn--pple-43d.com" in norm.host


def test_unsupported_schemes_rejected():
    invalid_schemes = [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/html,<script>alert(1)</script>",
        "about:blank",
    ]
    for url in invalid_schemes:
        norm = UrlNormalizer.normalize(url)
        assert norm.is_valid is False
        assert "Unsupported scheme" in norm.error or "Missing URL scheme" in norm.error


def test_ip_address_host_detection():
    norm = UrlNormalizer.normalize("http://192.168.1.1/admin")
    assert norm.is_valid is True
    assert norm.is_ip_address is True
    assert norm.host == "192.168.1.1"


def test_empty_or_malformed_url():
    assert UrlNormalizer.normalize("").is_valid is False
    assert UrlNormalizer.normalize(None).is_valid is False
    assert UrlNormalizer.normalize("not_a_valid_url").is_valid is False

