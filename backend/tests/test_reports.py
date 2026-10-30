import pytest
from datetime import date
from app.services.report_service import report_service
from app.models.browser_event import BrowserEvent
from app.models.security_finding import SecurityFinding
from app.models.daily_report import DailyReport
from app.db.base import utc_now


def test_daily_activity_report_generation(db_session):
    today = date.today()
    now = utc_now()

    # Add 2 sample events
    e1 = BrowserEvent(
        idempotency_key="rep-ev-1",
        installation_id="inst-rep",
        normalized_domain="testsite.org",
        sanitized_url_path="/page1",
        event_type="navigation",
        preliminary_risk_score=0,
        preliminary_severity="low",
        client_timestamp=now,
        created_at=now,
    )
    db_session.add(e1)
    db_session.commit()

    report_data = report_service.generate_daily_activity_report(db_session, target_date=today)
    assert report_data["total_navigation_events"] >= 1
    assert "estimation_limitations_disclaimer" in report_data
    assert "hourly_activity_distribution" in report_data
    assert "frequently_visited_domains" in report_data


def test_daily_security_report_generation(db_session):
    today = date.today()
    now = utc_now()

    # Add finding
    f1 = SecurityFinding(
        installation_id="inst-rep",
        domain="malicious-sample.net",
        category="phishing",
        severity="high",
        risk_score=80,
        status="active",
        confidence="high",
        explanation="Phishing brand combination",
        rule_id="RULE_DECEPTIVE_STRUCTURE",
        evidence={"sample": True},
        created_at=now,
    )
    db_session.add(f1)
    db_session.commit()

    sec_report = report_service.generate_daily_security_report(db_session, target_date=today)
    assert sec_report["total_findings"] >= 1
    assert sec_report["findings_by_severity"]["high"] >= 1
    assert len(sec_report["recommended_next_steps"]) >= 1
    assert "security_limitations_disclaimer" in sec_report


def test_report_csv_export(db_session):
    today = date.today()
    data = report_service.generate_daily_activity_report(db_session, target_date=today)
    report_record = db_session.query(DailyReport).filter(DailyReport.id == data["report_id"]).first()

    csv_text = report_service.export_report_csv(report_record)
    assert "Report ID" in csv_text
    assert "Total Navigation Events" in csv_text

