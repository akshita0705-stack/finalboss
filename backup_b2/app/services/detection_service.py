import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.services.url_normalizer import NormalizedUrl

# Target brand domains commonly targeted by phishing and spoofing
TARGET_MONITORED_DOMAINS = [
    "google.com",
    "paypal.com",
    "microsoft.com",
    "apple.com",
    "amazon.com",
    "facebook.com",
    "netflix.com",
    "bankofamerica.com",
    "chase.com",
    "wellsfargo.com",
    "github.com",
    "dropbox.com",
    "login.microsoftonline.com",
    "accounts.google.com",
]

# Sensitive brand tokens commonly embedded into spoofing domains
BRAND_KEYWORDS = [
    "paypal", "apple", "google", "microsoft", "amazon", "netflix",
    "chase", "wellsfargo", "bankofamerica", "binance", "coinbase",
    "metamask", "ledger", "trezor", "outlook", "office365"
]

# Deceptive security keywords commonly used in phishing paths and subdomains
DECEPTIVE_KEYWORDS = [
    "verify", "login", "signin", "security", "update", "account",
    "confirm", "secure", "authenticate", "wallet", "recovery", "support",
    "billing", "suspended", "unlock"
]

# TLDs with high historical malicious/phishing concentration
SUSPICIOUS_TLDS = {
    "zip", "mov", "top", "tk", "ml", "ga", "cf", "gq", "work", "click", "rest"
}


def compute_levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return compute_levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def compute_normalized_similarity(s1: str, s2: str) -> float:
    """Return similarity ratio between 0.0 and 1.0."""
    return difflib.SequenceMatcher(None, s1, s2).ratio()


@dataclass
class DetectionRuleResult:
    rule_id: str
    rule_name: str
    triggered: bool
    score_contribution: int
    severity: str  # low, medium, high, critical
    confidence: str  # low, medium, high
    explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssessmentResult:
    risk_score: int
    severity: str
    confidence: str
    immediate_alert: bool
    explanation: str
    rules_triggered: List[str]
    rule_results: List[DetectionRuleResult]
    lookalike_candidate: Optional[Dict[str, Any]] = None
    contributing_signals: List[Dict[str, Any]] = field(default_factory=list)


class DetectionService:
    """
    Deterministic, explainable security detection engine.
    Analyzes URLs, domains, and redirect patterns against modular security rules.
    """

    def assess_url(
        self,
        norm_url: NormalizedUrl,
        redirect_chain: Optional[List[Dict[str, Any]]] = None,
        cached_indicator_verdict: Optional[str] = None,
    ) -> AssessmentResult:
        if not norm_url.is_valid:
            return AssessmentResult(
                risk_score=60,
                severity="medium",
                confidence="high",
                immediate_alert=False,
                explanation=f"Malformed or unsupported URL: {norm_url.error}",
                rules_triggered=["RULE_INVALID_URL"],
                rule_results=[
                    DetectionRuleResult(
                        rule_id="RULE_INVALID_URL",
                        rule_name="Invalid or Unsupported URL Structure",
                        triggered=True,
                        score_contribution=60,
                        severity="medium",
                        confidence="high",
                        explanation=norm_url.error or "Invalid URL",
                    )
                ],
            )

        results: List[DetectionRuleResult] = []

        # Rule 1: Host is raw IP address
        results.append(self._check_ip_hostname(norm_url))

        # Rule 2: Excessive Subdomain Depth
        results.append(self._check_subdomain_depth(norm_url))

        # Rule 3: Homograph / Punycode (IDN spoofing)
        results.append(self._check_punycode_homograph(norm_url))

        # Rule 4: Lookalike Domain Similarity (Separate candidate evidence from verdict)
        lookalike_rule, lookalike_cand = self._check_lookalike_domain(norm_url)
        results.append(lookalike_rule)

        # Rule 5: Deceptive Brand / Security Keyword Embedding
        results.append(self._check_deceptive_structure(norm_url))

        # Rule 6: Suspicious TLD
        results.append(self._check_suspicious_tld(norm_url))

        # Rule 7: Suspicious Redirect Chain
        results.append(self._check_redirect_chain(norm_url, redirect_chain))

        # Rule 8: Known Threat Indicator
        if cached_indicator_verdict:
            results.append(self._check_cached_indicator(cached_indicator_verdict))

        # Aggregate Risk Score
        triggered_rules = [r for r in results if r.triggered]
        raw_score = sum(r.score_contribution for r in triggered_rules)
        # Cap score between 0 and 100
        risk_score = min(100, max(0, raw_score))

        # Determine severity based on configurable thresholds
        if risk_score >= settings.RISK_THRESHOLD_CRITICAL:
            severity = "critical"
        elif risk_score >= settings.RISK_THRESHOLD_HIGH:
            severity = "high"
        elif risk_score >= settings.RISK_THRESHOLD_MEDIUM:
            severity = "medium"
        else:
            severity = "low"

        # Overall confidence is derived from highest confidence among triggered rules
        confidence_levels = {"low": 1, "medium": 2, "high": 3}
        if triggered_rules:
            highest_conf = max(triggered_rules, key=lambda r: confidence_levels.get(r.confidence, 1)).confidence
        else:
            highest_conf = "high"

        # Determine if immediate live alert is required
        immediate_alert = severity in ("high", "critical")

        # Synthesize concise explanation
        if triggered_rules:
            explanations = [r.explanation for r in triggered_rules[:3]]
            summary_explanation = " | ".join(explanations)
        else:
            summary_explanation = "No suspicious heuristics or lookalike patterns identified."

        return AssessmentResult(
            risk_score=risk_score,
            severity=severity,
            confidence=highest_conf,
            immediate_alert=immediate_alert,
            explanation=summary_explanation,
            rules_triggered=[r.rule_id for r in triggered_rules],
            rule_results=results,
            lookalike_candidate=lookalike_cand,
            contributing_signals=[
                {
                    "rule_id": r.rule_id,
                    "name": r.rule_name,
                    "score": r.score_contribution,
                    "confidence": r.confidence,
                    "evidence": r.evidence,
                }
                for r in triggered_rules
            ],
        )

    def _check_ip_hostname(self, norm: NormalizedUrl) -> DetectionRuleResult:
        if norm.is_ip_address:
            return DetectionRuleResult(
                rule_id="RULE_IP_HOST",
                rule_name="Raw IP Address Navigation",
                triggered=True,
                score_contribution=45,
                severity="medium",
                confidence="high",
                explanation=f"Direct IP address '{norm.host}' used as hostname, typical of unauthenticated or C2 endpoints.",
                evidence={"host": norm.host, "is_ip_address": True},
            )
        return DetectionRuleResult(
            rule_id="RULE_IP_HOST",
            rule_name="Raw IP Address Navigation",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation="Hostname is a registered domain name, not a raw IP address.",
        )

    def _check_subdomain_depth(self, norm: NormalizedUrl) -> DetectionRuleResult:
        subdomain = norm.subdomain
        if subdomain:
            parts = [p for p in subdomain.split(".") if p]
            if len(parts) >= 3:
                return DetectionRuleResult(
                    rule_id="RULE_EXCESSIVE_SUBDOMAINS",
                    rule_name="Excessive Subdomain Depth",
                    triggered=True,
                    score_contribution=35,
                    severity="medium",
                    confidence="medium",
                    explanation=f"Excessive subdomain depth ({len(parts)} levels: '{subdomain}') can mask destination domain.",
                    evidence={"subdomain": subdomain, "level_count": len(parts)},
                )
        return DetectionRuleResult(
            rule_id="RULE_EXCESSIVE_SUBDOMAINS",
            rule_name="Excessive Subdomain Depth",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation="Normal subdomain depth.",
        )

    def _check_punycode_homograph(self, norm: NormalizedUrl) -> DetectionRuleResult:
        if norm.is_punycode:
            return DetectionRuleResult(
                rule_id="RULE_HOMOGRAPH_PUNYCODE",
                rule_name="Punycode / IDN Spoofing Candidate",
                triggered=True,
                score_contribution=50,
                severity="high",
                confidence="high",
                explanation=f"Punycode encoded domain '{norm.host}' detected. May represent internationalized homograph impersonation.",
                evidence={"host": norm.host, "is_punycode": True},
            )
        return DetectionRuleResult(
            rule_id="RULE_HOMOGRAPH_PUNYCODE",
            rule_name="Punycode / IDN Spoofing Candidate",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation="Standard ASCII hostname without punycode prefix.",
        )

    def _check_lookalike_domain(
        self, norm: NormalizedUrl
    ) -> Tuple[DetectionRuleResult, Optional[Dict[str, Any]]]:
        domain = norm.domain.lower()
        if not domain:
            return (
                DetectionRuleResult(
                    rule_id="RULE_LOOKALIKE_DOMAIN",
                    rule_name="Lookalike Domain Similarity",
                    triggered=False,
                    score_contribution=0,
                    severity="low",
                    confidence="high",
                    explanation="No domain extracted.",
                ),
                None,
            )

        best_match = None
        highest_sim = 0.0
        lowest_dist = 999

        for target in TARGET_MONITORED_DOMAINS:
            # If domain is the legitimate brand domain itself, it's not a lookalike!
            if domain == target:
                return (
                    DetectionRuleResult(
                        rule_id="RULE_LOOKALIKE_DOMAIN",
                        rule_name="Lookalike Domain Similarity",
                        triggered=False,
                        score_contribution=0,
                        severity="low",
                        confidence="high",
                        explanation=f"Matches verified legitimate target domain '{target}'.",
                    ),
                    None,
                )

            dist = compute_levenshtein_distance(domain, target)
            sim = compute_normalized_similarity(domain, target)

            # Lookalike match candidate condition:
            # 1. Edit distance 1 or 2 with high similarity
            # 2. Or prefix/suffix typo squatting (e.g. paypal-security.com vs paypal.com)
            target_stem = target.split(".")[0]
            domain_stem = domain.split(".")[0]
            stem_sim = compute_normalized_similarity(domain_stem, target_stem)

            if (dist <= 2 and sim >= 0.80) or (stem_sim >= 0.85 and domain_stem != target_stem):
                if sim > highest_sim:
                    highest_sim = sim
                    lowest_dist = dist
                    best_match = {
                        "target_domain": target,
                        "candidate_domain": domain,
                        "similarity_score": round(sim, 3),
                        "edit_distance": dist,
                        "disclaimer": "Lookalike candidate match alone does not prove malicious intent.",
                    }

        if best_match:
            # Lookalike similarity contributes moderate risk, keeping verdict explainable
            score = 45 if lowest_dist <= 1 else 30
            return (
                DetectionRuleResult(
                    rule_id="RULE_LOOKALIKE_DOMAIN",
                    rule_name="Lookalike Domain Similarity Candidate",
                    triggered=True,
                    score_contribution=score,
                    severity="medium",
                    confidence="medium",
                    explanation=f"Potential lookalike candidate for '{best_match['target_domain']}' (edit distance: {lowest_dist}, similarity: {best_match['similarity_score']}).",
                    evidence=best_match,
                ),
                best_match,
            )

        return (
            DetectionRuleResult(
                rule_id="RULE_LOOKALIKE_DOMAIN",
                rule_name="Lookalike Domain Similarity",
                triggered=False,
                score_contribution=0,
                severity="low",
                confidence="high",
                explanation="No lookalike patterns found against high-profile target domains.",
            ),
            None,
        )

    def _check_deceptive_structure(self, norm: NormalizedUrl) -> DetectionRuleResult:
        host = norm.host.lower()
        subdomain = norm.subdomain.lower()
        path = norm.path.lower()
        registered_domain = norm.domain.lower()

        matched_brand = None
        for brand in BRAND_KEYWORDS:
            # Check if brand keyword appears in subdomain or host, but NOT as the registered domain
            if brand in host and not registered_domain.startswith(brand):
                matched_brand = brand
                break

        matched_deceptive_keyword = None
        for kw in DECEPTIVE_KEYWORDS:
            if kw in host or kw in path:
                matched_deceptive_keyword = kw
                break

        if matched_brand and matched_deceptive_keyword:
            return DetectionRuleResult(
                rule_id="RULE_DECEPTIVE_STRUCTURE",
                rule_name="Deceptive Brand and Action Keyword Pattern",
                triggered=True,
                score_contribution=75,
                severity="high",
                confidence="high",
                explanation=f"Deceptive pattern: Brand '{matched_brand}' combined with action keyword '{matched_deceptive_keyword}' on untrusted domain '{registered_domain}'.",
                evidence={
                    "brand": matched_brand,
                    "keyword": matched_deceptive_keyword,
                    "registered_domain": registered_domain,
                    "full_host": host,
                },
            )
        elif matched_brand:
            return DetectionRuleResult(
                rule_id="RULE_DECEPTIVE_STRUCTURE",
                rule_name="Deceptive Brand Placement",
                triggered=True,
                score_contribution=35,
                severity="medium",
                confidence="medium",
                explanation=f"Brand keyword '{matched_brand}' detected in subdomain/host of separate registered domain '{registered_domain}'.",
                evidence={"brand": matched_brand, "registered_domain": registered_domain},
            )

        return DetectionRuleResult(
            rule_id="RULE_DECEPTIVE_STRUCTURE",
            rule_name="Deceptive Structure Analysis",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation="No deceptive brand-action combinations detected.",
        )

    def _check_suspicious_tld(self, norm: NormalizedUrl) -> DetectionRuleResult:
        suffix = norm.suffix.lower()
        if suffix in SUSPICIOUS_TLDS:
            return DetectionRuleResult(
                rule_id="RULE_SUSPICIOUS_TLD",
                rule_name="High-Abuse Top-Level Domain",
                triggered=True,
                score_contribution=20,
                severity="low",
                confidence="low",
                explanation=f"Top-level domain '.{suffix}' has elevated correlation with ephemeral spam and phishing campaigns.",
                evidence={"tld": suffix},
            )
        return DetectionRuleResult(
            rule_id="RULE_SUSPICIOUS_TLD",
            rule_name="Top-Level Domain Reputation",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation=f"Standard top-level domain '.{suffix}'.",
        )

    def _check_redirect_chain(
        self, norm: NormalizedUrl, redirect_chain: Optional[List[Dict[str, Any]]]
    ) -> DetectionRuleResult:
        if not redirect_chain or len(redirect_chain) <= 1:
            return DetectionRuleResult(
                rule_id="RULE_SUSPICIOUS_REDIRECT",
                rule_name="Redirect Chain Analysis",
                triggered=False,
                score_contribution=0,
                severity="low",
                confidence="high",
                explanation="Direct navigation with no external redirect hops.",
            )

        # Multiple redirect hops across different domains
        domains_in_chain = set()
        for hop in redirect_chain:
            hop_url = hop.get("url", "")
            hop_domain = hop.get("domain", "")
            if hop_domain:
                domains_in_chain.add(hop_domain)

        if len(domains_in_chain) >= 3:
            return DetectionRuleResult(
                rule_id="RULE_SUSPICIOUS_REDIRECT",
                rule_name="Multi-Domain Redirect Anomaly",
                triggered=True,
                score_contribution=30,
                severity="medium",
                confidence="medium",
                explanation=f"Redirect chain traversed {len(domains_in_chain)} distinct domains ({', '.join(list(domains_in_chain)[:3])}).",
                evidence={"domain_count": len(domains_in_chain), "chain_length": len(redirect_chain)},
            )

        return DetectionRuleResult(
            rule_id="RULE_SUSPICIOUS_REDIRECT",
            rule_name="Redirect Chain Analysis",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="medium",
            explanation="Normal single redirect hop.",
        )

    def _check_cached_indicator(self, verdict: str) -> DetectionRuleResult:
        if verdict == "malicious":
            return DetectionRuleResult(
                rule_id="RULE_KNOWN_INDICATOR",
                rule_name="Known Threat Intelligence Match",
                triggered=True,
                score_contribution=95,
                severity="critical",
                confidence="high",
                explanation="Domain matches confirmed malicious indicator in threat intelligence repository.",
                evidence={"verdict": "malicious"},
            )
        elif verdict == "suspicious":
            return DetectionRuleResult(
                rule_id="RULE_KNOWN_INDICATOR",
                rule_name="Suspicious Threat Indicator Match",
                triggered=True,
                score_contribution=50,
                severity="medium",
                confidence="medium",
                explanation="Domain flagged as suspicious by threat intelligence feeds.",
                evidence={"verdict": "suspicious"},
            )
        return DetectionRuleResult(
            rule_id="RULE_KNOWN_INDICATOR",
            rule_name="Threat Indicator Match",
            triggered=False,
            score_contribution=0,
            severity="low",
            confidence="high",
            explanation="No known malicious indicators found.",
        )


detection_engine = DetectionService()
