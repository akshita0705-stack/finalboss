import sys
import os
from datetime import datetime, timedelta, timezone

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db.session import SessionLocal
from app.core.security import get_password_hash, hash_api_key
from app.models.user import User, ApiKey
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.models.security_finding import SecurityFinding
from app.models.threat_indicator import ThreatIndicator
from app.models.graph_sync_job import GraphSyncJob
from app.core.config import settings
from app.db.base import utc_now


def seed_database():
    print("[*] Seeding TraceGuard AI development database...")
    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin = db.query(User).filter(User.email == "admin@traceguard.ai").first()
        if not admin:
            admin = User(
                email="admin@traceguard.ai",
                hashed_password=get_password_hash("AdminPassword123!"),
                full_name="Chief Security Officer",
                role="admin",
            )
            db.add(admin)
            db.flush()
            print("  [+] Created default Admin user: admin@traceguard.ai / AdminPassword123!")
        else:
            print("  [-] Admin user already exists.")

        # 2. Seed Analyst User
        analyst = db.query(User).filter(User.email == "analyst@traceguard.ai").first()
        if not analyst:
            analyst = User(
                email="analyst@traceguard.ai",
                hashed_password=get_password_hash("AnalystPassword123!"),
                full_name="SOC Analyst Tier 2",
                role="analyst",
            )
            db.add(analyst)
            db.flush()
            print("  [+] Created Analyst user: analyst@traceguard.ai / AnalystPassword123!")

        # 3. Seed Default Extension API Key
        ext_key_hash = hash_api_key(settings.EXTENSION_API_KEY)
        api_key = db.query(ApiKey).filter(ApiKey.hashed_key == ext_key_hash).first()
        if not api_key:
            api_key = ApiKey(
                installation_id="demo-extension-install-001",
                user_id=admin.id,
                hashed_key=ext_key_hash,
                name="Default Chrome Extension Dev Key",
            )
            db.add(api_key)
            db.flush()
            print(f"  [+] Seeded Extension API Key: {settings.EXTENSION_API_KEY}")

        # 4. Seed Representative Browser Events & Findings
        demo_install_id = "demo-extension-install-001"
        now = utc_now()

        test_destinations = [
            # Benign
            {
                "url": "https://github.com/fastapi/fastapi",
                "domain": "github.com",
                "path": "/fastapi",
                "risk": 0,
                "sev": "low",
                "finding": None,
                "visits": 14,
            },
            {
                "url": "https://docs.python.org/3/library/",
                "domain": "docs.python.org",
                "path": "/3",
                "risk": 0,
                "sev": "low",
                "finding": None,
                "visits": 28,
            },
            {
                "url": "https://www.google.com/search",
                "domain": "google.com",
                "path": "/search",
                "risk": 0,
                "sev": "low",
                "finding": None,
                "visits": 42,
            },
            # Lookalike Spoofing Candidate
            {
                "url": "https://paypa1-security-login.com/account/recovery",
                "domain": "paypa1-security-login.com",
                "path": "/account",
                "risk": 85,
                "sev": "high",
                "visits": 2,
                "finding": {
                    "category": "homograph",
                    "rule": "RULE_LOOKALIKE_DOMAIN",
                    "explanation": "Lookalike candidate for 'paypal.com' (Levenshtein distance 1, similarity 0.88) combined with deceptive keywords.",
                    "evidence": {
                        "target_domain": "paypal.com",
                        "similarity_score": 0.88,
                        "edit_distance": 1,
                        "brand": "paypal",
                    },
                },
            },
            # Deceptive Brand Subdomain on Suspicious TLD
            {
                "url": "http://microsoft.verify-account.security-update.top/login",
                "domain": "security-update.top",
                "path": "/login",
                "risk": 90,
                "sev": "critical",
                "visits": 1,
                "finding": {
                    "category": "phishing",
                    "rule": "RULE_DECEPTIVE_STRUCTURE",
                    "explanation": "Deceptive brand 'microsoft' nested across deep subdomains under high-abuse TLD '.top'.",
                    "evidence": {
                        "brand": "microsoft",
                        "subdomain": "microsoft.verify-account",
                        "tld": "top",
                    },
                },
            },
            # Raw IP Host navigation
            {
                "url": "http://192.168.1.100:8080/admin/c2",
                "domain": "192.168.1.100",
                "path": "/admin",
                "risk": 45,
                "sev": "medium",
                "visits": 3,
                "finding": {
                    "category": "deceptive_structure",
                    "rule": "RULE_IP_HOST",
                    "explanation": "Direct raw IP address navigation observed.",
                    "evidence": {"is_ip_address": True, "host": "192.168.1.100"},
                },
            },
        ]

        for i, item in enumerate(test_destinations):
            ev_key = f"seed-key-{item['domain']}"
            existing_ev = db.query(BrowserEvent).filter(BrowserEvent.idempotency_key == ev_key).first()
            if not existing_ev:
                event_time = now - timedelta(hours=i * 2)
                ev = BrowserEvent(
                    idempotency_key=ev_key,
                    installation_id=demo_install_id,
                    user_id=admin.id,
                    normalized_domain=item["domain"],
                    sanitized_url_path=item["path"],
                    scheme="https" if "https" in item["url"] else "http",
                    event_type="navigation",
                    source="chrome_extension",
                    processing_status="assessed",
                    preliminary_risk_score=item["risk"],
                    preliminary_severity=item["sev"],
                    client_timestamp=event_time,
                    created_at=event_time,
                )
                db.add(ev)
                db.flush()

                # Add visit record
                vis = Visit(
                    installation_id=demo_install_id,
                    user_id=admin.id,
                    normalized_domain=item["domain"],
                    privacy_minimized_path=item["path"],
                    visit_count=item["visits"],
                    first_seen_at=event_time - timedelta(days=2),
                    last_seen_at=event_time,
                )
                db.add(vis)
                db.flush()

                # Add finding if present
                if item["finding"]:
                    f_info = item["finding"]
                    finding = SecurityFinding(
                        event_id=ev.id,
                        installation_id=demo_install_id,
                        domain=item["domain"],
                        category=f_info["category"],
                        severity=item["sev"],
                        risk_score=item["risk"],
                        status="active",
                        confidence="high",
                        explanation=f_info["explanation"],
                        rule_id=f_info["rule"],
                        provider_source="deterministic_detection_engine",
                        evidence=f_info["evidence"],
                        created_at=event_time,
                    )
                    db.add(finding)
                    db.flush()

                    # Add Graph Sync Job
                    job = GraphSyncJob(
                        entity_type="finding",
                        entity_id=finding.id,
                        operation="upsert",
                        status="synced",
                        synced_at=now,
                    )
                    db.add(job)

        db.commit()
        print("[+] Seed completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"[!] Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

