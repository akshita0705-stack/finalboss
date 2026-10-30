import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Set
import idna
import tldextract

# Set of query parameters that are known to carry credentials, session tokens, or PII
SENSITIVE_PARAM_NAMES: Set[str] = {
    "token", "access_token", "auth_token", "id_token", "refresh_token",
    "auth", "authentication", "authorization", "bearer",
    "password", "pass", "pwd", "secret", "client_secret",
    "key", "api_key", "apikey", "session", "session_id", "sessionid",
    "code", "verification_code", "otp", "pin", "signature", "sig",
    "state", "oauth_token", "user_id", "email", "username", "ssn"
}

# Supported protocols
ALLOWED_SCHEMES = {"http", "https"}

# IP address pattern (IPv4)
IPV4_REGEX = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

# Extract TLDExtract instance configured for cache or local fallback
extractor = tldextract.TLDExtract(cache_dir=None)


@dataclass
class NormalizedUrl:
    raw_url: str
    is_valid: bool
    error: Optional[str] = None
    scheme: str = ""
    host: str = ""
    domain: str = ""          # Registered domain (eTLD+1, e.g. "example.com")
    subdomain: str = ""       # Subdomain (e.g. "sub.account")
    suffix: str = ""          # Public suffix (e.g. "com", "co.uk")
    port: Optional[int] = None
    path: str = "/"
    sanitized_url: str = ""
    privacy_minimized_path: str = "/"
    is_ip_address: bool = False
    is_punycode: bool = False
    ascii_domain: str = ""


class UrlNormalizer:
    @staticmethod
    def normalize(raw_url: str, strip_query_strings: bool = True) -> NormalizedUrl:
        """
        Normalize a raw URL safely and deterministically:
        1. Check scheme and basic URL structure.
        2. Lowercase and decode/encode IDNA/punycode domain.
        3. Remove default ports (80 for http, 443 for https).
        4. Extract public suffix, registered domain, and subdomain boundaries.
        5. Redact or strip sensitive query parameters.
        6. Compute privacy-minimized path.
        """
        if not raw_url or not isinstance(raw_url, str):
            return NormalizedUrl(raw_url=str(raw_url), is_valid=False, error="URL is empty or not a string")

        raw_url = raw_url.strip()
        if len(raw_url) > 4096:
            return NormalizedUrl(raw_url=raw_url[:100], is_valid=False, error="URL exceeds maximum supported length (4096)")

        # Reject javascript:, data:, file:, etc.
        try:
            parsed = urllib.parse.urlsplit(raw_url)
        except Exception as e:
            return NormalizedUrl(raw_url=raw_url, is_valid=False, error=f"Malformed URL structure: {e}")

        scheme = (parsed.scheme or "").lower()
        if not scheme:
            # If no scheme given, reject or default only if standard host exists
            return NormalizedUrl(raw_url=raw_url, is_valid=False, error="Missing URL scheme")

        if scheme not in ALLOWED_SCHEMES:
            return NormalizedUrl(
                raw_url=raw_url,
                is_valid=False,
                error=f"Unsupported scheme '{scheme}'. Only http and https are allowed."
            )

        if not parsed.netloc:
            return NormalizedUrl(raw_url=raw_url, is_valid=False, error="URL has no hostname or network location")

        # Parse host and port
        netloc = parsed.netloc
        host = netloc
        port: Optional[int] = None

        if "@" in host:
            # Userinfo in URL (e.g. http://user:pass@evil.com) -> reject or strip userinfo
            host = host.split("@")[-1]

        if ":" in host:
            host_parts = host.rsplit(":", 1)
            host = host_parts[0]
            try:
                port = int(host_parts[1])
                # Drop default ports
                if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
                    port = None
            except ValueError:
                return NormalizedUrl(raw_url=raw_url, is_valid=False, error="Invalid port in URL")

        host = host.lower().strip(".")
        if not host:
            return NormalizedUrl(raw_url=raw_url, is_valid=False, error="Invalid empty hostname")

        # Check for IP address
        is_ip = bool(IPV4_REGEX.match(host))

        # Handle IDNA / Punycode
        is_punycode = host.startswith("xn--") or ".xn--" in host
        ascii_host = host
        try:
            ascii_host = idna.encode(host).decode("ascii")
        except Exception:
            # If host already ascii or idna fails, keep sanitized host
            ascii_host = host.encode("ascii", "ignore").decode("ascii")

        # Extract registered domain using tldextract
        try:
            ext = extractor(ascii_host)
            domain = getattr(ext, "top_domain_under_public_suffix", "")
            if not domain:
                domain = f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else (ext.domain or ascii_host)
            subdomain = ext.subdomain
            suffix = ext.suffix
        except Exception:
            # Fallback split
            parts = ascii_host.split(".")
            if len(parts) >= 2:
                domain = ".".join(parts[-2:])
                subdomain = ".".join(parts[:-2])
                suffix = parts[-1]
            else:
                domain = ascii_host
                subdomain = ""
                suffix = ""

        # Normalize path
        path = parsed.path or "/"
        # Ensure path begins with /
        if not path.startswith("/"):
            path = "/" + path

        # Sanitize query parameters
        query = parsed.query
        sanitized_query = ""
        if query and not strip_query_strings:
            param_pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
            sanitized_pairs = []
            for k, v in param_pairs:
                if k.lower() in SENSITIVE_PARAM_NAMES:
                    sanitized_pairs.append((k, "[REDACTED]"))
                else:
                    sanitized_pairs.append((k, v))
            sanitized_query = urllib.parse.urlencode(sanitized_pairs)

        # Build sanitized full URL
        port_suffix = f":{port}" if port is not None else ""
        query_part = f"?{sanitized_query}" if sanitized_query else ""
        sanitized_url = f"{scheme}://{ascii_host}{port_suffix}{path}{query_part}"

        # Privacy-minimized path: only retain top-level directory segment if present
        path_segments = [s for s in path.split("/") if s]
        if path_segments:
            privacy_minimized_path = f"/{path_segments[0]}"
        else:
            privacy_minimized_path = "/"

        return NormalizedUrl(
            raw_url=raw_url,
            is_valid=True,
            error=None,
            scheme=scheme,
            host=ascii_host,
            domain=domain,
            subdomain=subdomain,
            suffix=suffix,
            port=port,
            path=path,
            sanitized_url=sanitized_url,
            privacy_minimized_path=privacy_minimized_path,
            is_ip_address=is_ip,
            is_punycode=is_punycode,
            ascii_domain=domain,
        )
