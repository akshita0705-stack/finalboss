from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import UserScope, get_user_scope
from app.models.daily_report import DailyReport
from app.schemas.report import ReportDetailResponse, DailyActivityReportData, DailySecurityReportData
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Daily Reports"])


@router.get("/activity/daily", response_model=DailyActivityReportData)
def get_daily_activity_report(
    report_date: Optional[date] = Query(None, description="Report calendar date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Generate or retrieve a Daily Browsing Activity Report.
    Includes events, unique destinations, repetition count, timeline, and estimation limitations.
    """
    target_date = report_date or date.today()
    report_data = report_service.generate_daily_activity_report(
        db=db,
        target_date=target_date,
        installation_ids=scope.installation_ids,
    )
    return report_data


@router.get("/security/daily", response_model=DailySecurityReportData)
def get_daily_security_report(
    report_date: Optional[date] = Query(None, description="Report calendar date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Generate or retrieve a Daily Security Findings Report.
    Includes severity breakdown, high-risk items, lookalikes, unknown/failed lookups, and recommendations.
    """
    target_date = report_date or date.today()
    report_data = report_service.generate_daily_security_report(
        db=db,
        target_date=target_date,
        installation_ids=scope.installation_ids,
    )
    return report_data


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report_by_id(
    report_id: str,
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """Retrieve an existing report record by its unique ID."""
    report = db.query(DailyReport).filter(
        DailyReport.id == report_id,
        DailyReport.installation_id.in_(scope.installation_ids),
    ).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found",
        )
    return report


@router.get("/{report_id}/export")
def export_report_csv(
    report_id: str,
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """Export report in CSV or JSON format."""
    report = db.query(DailyReport).filter(
        DailyReport.id == report_id,
        DailyReport.installation_id.in_(scope.installation_ids),
    ).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found",
        )

    if format == "csv":
        csv_content = report_service.export_report_csv(report)
        filename = f"traceguard_report_{report.report_type}_{report.date_range_start.strftime('%Y%m%d')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        return report.summary_data
