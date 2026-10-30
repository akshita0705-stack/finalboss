import io
import csv
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.logging import logger
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.models.security_finding import SecurityFinding
from app.models.threat_indicator import ThreatIndicator
from app.models.graph_sync_job import GraphSyncJob
from app.models.daily_report import DailyReport
from app.schemas.report import DailyActivityReportData, DailySecurityReportData
from app.db.base import utc_now


class ReportService:
    def generate_daily_activity_report(
        self,
        db: Session,
        target_date: datetime.date,
        installation_id: Optional[str] = None,
        installation_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate and build daily browsing activity report for a specific calendar day.
        Assumptions and limitations are explicitly documented.
        """
        start_dt = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)

        # 1. Query browser events within window
        ev_query = db.query(BrowserEvent).filter(
            BrowserEvent.created_at >= start_dt,
            BrowserEvent.created_at <= end_dt,
        )
        if installation_id:
            ev_query = ev_query.filter(BrowserEvent.installation_id == installation_id)
        if installation_ids is not None:
            ev_query = ev_query.filter(BrowserEvent.installation_id.in_(installation_ids))
        events = ev_query.order_by(BrowserEvent.created_at.asc()).all()

        total_events = len(events)
        unique_domains = len(set(e.normalized_domain for e in events))

        # 2. Query visits for repetition analytics
        vis_query = db.query(Visit).filter(
            Visit.last_seen_at >= start_dt,
            Visit.last_seen_at <= end_dt,
        )
        if installation_id:
            vis_query = vis_query.filter(Visit.installation_id == installation_id)
        if installation_ids is not None:
            vis_query = vis_query.filter(Visit.installation_id.in_(installation_ids))
        visits = vis_query.all()

        repeated_visits = sum(v.visit_count - 1 for v in visits if v.visit_count > 1)

        # Frequently visited domains
        domain_counts: Dict[str, int] = {}
        for e in events:
            domain_counts[e.normalized_domain] = domain_counts.get(e.normalized_domain, 0) + 1
        
        top_domains = [
            {"domain": dom, "event_count": count}
            for dom, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Hourly distribution (0 to 23)
        hourly_counts = {h: 0 for h in range(24)}
        for e in events:
            hour = e.created_at.hour
            hourly_counts[hour] += 1
        hourly_distribution = [{"hour": h, "count": count} for h, count in sorted(hourly_counts.items())]

        # Chronological timeline
        timeline = [
            {
                "timestamp": e.created_at.isoformat(),
                "domain": e.normalized_domain,
                "sanitized_url": f"{e.scheme}://{e.normalized_domain}{e.sanitized_url_path}",
                "event_type": e.event_type,
                "risk_score": e.preliminary_risk_score,
                "severity": e.preliminary_severity,
            }
            for e in events[:50]
        ]

        # Estimated time-on-site calculation with stated assumptions
        # Assumption: Time between consecutive events within 15 minutes is attributed to session.
        # Gaps > 15 minutes treated as idle/separate sessions.
        estimated_active_minutes = 0
        if len(events) >= 2:
            for i in range(len(events) - 1):
                delta = (events[i + 1].created_at - events[i].created_at).total_seconds()
                if 0 < delta <= 900:  # <= 15 minutes
                    estimated_active_minutes += int(delta // 60)

        disclaimer = (
            "Activity reports are aggregated exclusively from observed browser navigation events. "
            "Estimated active minutes is a heuristic approximation based on consecutive event timestamps (<15m gaps) "
            "and does NOT represent exact foreground time, application productivity, or user intent."
        )

        report_data = {
            "date": target_date.isoformat(),
            "total_navigation_events": total_events,
            "unique_domains_visited": unique_domains,
            "repeated_visits_count": repeated_visits,
            "frequently_visited_domains": top_domains,
            "hourly_activity_distribution": hourly_distribution,
            "chronological_activity_timeline": timeline,
            "estimated_time_on_site": {
                "estimated_active_minutes": estimated_active_minutes,
                "consecutive_threshold_seconds": 900,
                "calculation_method": "Inter-event delta cap heuristic",
            },
            "estimation_limitations_disclaimer": disclaimer,
        }

        # Save or update DailyReport record
        report_record = DailyReport(
            installation_id=installation_id or (installation_ids[0] if installation_ids and len(installation_ids) == 1 else None),
            report_type="activity",
            date_range_start=start_dt,
            date_range_end=end_dt,
            summary_data=report_data,
            status="completed",
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)

        report_data["report_id"] = report_record.id
        return report_data

    def generate_daily_security_report(
        self,
        db: Session,
        target_date: datetime.date,
        installation_id: Optional[str] = None,
        installation_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate and build daily security findings report for a specific calendar day.
        """
        start_dt = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)

        # 1. Query findings within window
        find_query = db.query(SecurityFinding).filter(
            SecurityFinding.created_at >= start_dt,
            SecurityFinding.created_at <= end_dt,
        )
        if installation_id:
            find_query = find_query.filter(SecurityFinding.installation_id == installation_id)
        if installation_ids is not None:
            find_query = find_query.filter(SecurityFinding.installation_id.in_(installation_ids))
        findings = find_query.all()

        total_findings = len(findings)

        # Breakdown by severity
        sev_counts: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
        cat_counts: Dict[str, int] = {}
        high_risk_observations = []
        lookalike_candidates = []
        observed_redirects = []
        unresolved_findings = []

        for f in findings:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
            cat_counts[f.category] = cat_counts.get(f.category, 0) + 1

            if f.severity in ("high", "critical"):
                high_risk_observations.append({
                    "finding_id": f.id,
                    "domain": f.domain,
                    "severity": f.severity,
                    "risk_score": f.risk_score,
                    "explanation": f.explanation,
                    "category": f.category,
                })

            if f.status == "active":
                unresolved_findings.append({
                    "finding_id": f.id,
                    "domain": f.domain,
                    "severity": f.severity,
                    "explanation": f.explanation,
                })

            lookalike = f.evidence.get("lookalike_candidate")
            if lookalike:
                lookalike_candidates.append({
                    "finding_id": f.id,
                    "domain": f.domain,
                    "impersonated_target": lookalike.get("target_domain"),
                    "similarity_score": lookalike.get("similarity_score"),
                    "edit_distance": lookalike.get("edit_distance"),
                })

        # Query provider error/unknown counts from ThreatIndicators
        ti_query = db.query(ThreatIndicator).filter(
            ThreatIndicator.created_at >= start_dt,
            ThreatIndicator.created_at <= end_dt,
        )
        indicators = ti_query.all()
        provider_failures = [
            {"provider": ind.provider, "value": ind.normalized_value, "status": ind.response_status}
            for ind in indicators if ind.response_status != "success"
        ]

        # Query graph sync failures
        failed_graph_jobs = (
            db.query(GraphSyncJob)
            .filter(
                GraphSyncJob.created_at >= start_dt,
                GraphSyncJob.created_at <= end_dt,
                GraphSyncJob.status == "failed",
            )
            .count()
        )

        recommended_steps = []
        if high_risk_observations:
            recommended_steps.append(
                f"Isolate and investigate {len(high_risk_observations)} high/critical security findings immediately."
            )
        if lookalike_candidates:
            recommended_steps.append(
                f"Verify credentials entered on {len(lookalike_candidates)} candidate lookalike domains."
            )
        if failed_graph_jobs > 0:
            recommended_steps.append(
                f"Inspect {failed_graph_jobs} failed graph synchronization jobs and TigerGraph connectivity."
            )
        if not recommended_steps:
            recommended_steps.append("No active critical incidents requiring analyst escalation.")

        disclaimer = (
            "TraceGuard AI Security Reports summarize observed deterministic heuristics and threat intelligence feeds. "
            "Absence of findings does not guarantee safety. Do not treat TraceGuard as an antivirus replacement."
        )

        report_data = {
            "date": target_date.isoformat(),
            "total_findings": total_findings,
            "findings_by_severity": sev_counts,
            "findings_by_category": cat_counts,
            "high_risk_and_suspicious_observations": high_risk_observations[:20],
            "lookalike_domain_candidates": lookalike_candidates,
            "observed_redirects_and_external_relationships": observed_redirects,
            "unknown_assessments_and_provider_failures": provider_failures,
            "unresolved_findings": unresolved_findings[:20],
            "recommended_next_steps": recommended_steps,
            "graph_sync_failures_count": failed_graph_jobs,
            "security_limitations_disclaimer": disclaimer,
        }

        # Save to database
        report_record = DailyReport(
            installation_id=installation_id or (installation_ids[0] if installation_ids and len(installation_ids) == 1 else None),
            report_type="security",
            date_range_start=start_dt,
            date_range_end=end_dt,
            summary_data=report_data,
            status="completed",
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)

        report_data["report_id"] = report_record.id
        return report_data

    def export_report_csv(self, report: DailyReport) -> str:
        """Export report data to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        data = report.summary_data or {}
        writer.writerow(["Report ID", report.id])
        writer.writerow(["Report Type", report.report_type])
        writer.writerow(["Start Date", report.date_range_start.isoformat()])
        writer.writerow(["End Date", report.date_range_end.isoformat()])
        writer.writerow([])

        if report.report_type == "activity":
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Navigation Events", data.get("total_navigation_events", 0)])
            writer.writerow(["Unique Domains", data.get("unique_domains_visited", 0)])
            writer.writerow(["Repeated Visits", data.get("repeated_visits_count", 0)])
            writer.writerow([])
            writer.writerow(["Frequently Visited Domains"])
            writer.writerow(["Domain", "Event Count"])
            for d in data.get("frequently_visited_domains", []):
                writer.writerow([d.get("domain"), d.get("event_count")])

        elif report.report_type == "security":
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Findings", data.get("total_findings", 0)])
            writer.writerow([])
            writer.writerow(["Findings by Severity"])
            for sev, count in data.get("findings_by_severity", {}).items():
                writer.writerow([sev, count])
            writer.writerow([])
            writer.writerow(["High Risk Observations"])
            writer.writerow(["Finding ID", "Domain", "Severity", "Risk Score", "Explanation"])
            for obs in data.get("high_risk_and_suspicious_observations", []):
                writer.writerow([
                    obs.get("finding_id"),
                    obs.get("domain"),
                    obs.get("severity"),
                    obs.get("risk_score"),
                    obs.get("explanation"),
                ])

        return output.getvalue()


report_service = ReportService()

