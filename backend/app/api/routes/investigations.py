from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.investigation import InvestigationRequest, InvestigationResponse
from app.agents.investigation_agent import investigation_agent

router = APIRouter(prefix="/investigations", tags=["AI Investigation Agent"])


@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
def investigate_security_question(
    req: InvestigationRequest,
    db: Session = Depends(get_db),
):
    """
    Submit an investigation question to the AI security agent.
    The agent retrieves strictly authorized evidence from the backend,
    cites specific finding IDs, event IDs, and timestamps, and clearly separates
    observed facts from inferred relationships.
    """
    response = investigation_agent.investigate(db=db, req=req)
    return response

