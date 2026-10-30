from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import UserScope, get_user_scope
from app.models.security_finding import SecurityFinding
from app.schemas.finding import SecurityFindingResponse, SecurityFindingUpdate

router = APIRouter(prefix="/findings", tags=["Security Findings"])


@router.get("", response_model=List[SecurityFindingResponse])
def list_security_findings(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    category: Optional[str] = Query(None, description="Filter by category (phishing, homograph, etc.)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, resolved, false_positive)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """List the current user's security findings with filtering and pagination."""
    query = db.query(SecurityFinding).filter(SecurityFinding.installation_id.in_(scope.installation_ids))

    if domain:
        query = query.filter(SecurityFinding.domain == domain.lower())
    if severity:
        query = query.filter(SecurityFinding.severity == severity.lower())
    if category:
        query = query.filter(SecurityFinding.category == category.lower())
    if status_filter:
        query = query.filter(SecurityFinding.status == status_filter.lower())

    findings = query.order_by(SecurityFinding.created_at.desc()).offset(offset).limit(limit).all()
    return findings


@router.get("/{finding_id}", response_model=SecurityFindingResponse)
def get_security_finding_details(
    finding_id: str,
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """Retrieve full details and structured evidence for a security finding."""
    finding = db.query(SecurityFinding).filter(
        SecurityFinding.id == finding_id,
        SecurityFinding.installation_id.in_(scope.installation_ids),
    ).first()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security finding '{finding_id}' not found",
        )
    return finding


@router.patch("/{finding_id}", response_model=SecurityFindingResponse)
def update_security_finding_status(
    finding_id: str,
    update_in: SecurityFindingUpdate,
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """Update finding status (e.g., active -> resolved or false_positive)."""
    finding = db.query(SecurityFinding).filter(
        SecurityFinding.id == finding_id,
        SecurityFinding.installation_id.in_(scope.installation_ids),
    ).first()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security finding '{finding_id}' not found",
        )

    allowed_statuses = {"active", "investigating", "resolved", "false_positive"}
    new_status = update_in.status.lower()
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Allowed: {list(allowed_statuses)}",
        )

    finding.status = new_status
    db.commit()
    db.refresh(finding)
    return finding

