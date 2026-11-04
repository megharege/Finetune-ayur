from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.services.triage_service import evaluate_triage

router = APIRouter(prefix="/triage", tags=["Clinical Triage"])

class QuickTriageCheck(BaseModel):
    symptoms: str
    chief_complaint: Optional[str] = ""
    severity: int = 1

@router.post("/check")
def check_triage(payload: QuickTriageCheck):
    """
    Dedicated rule-based triage safety check endpoint.
    Triggers red flag & 112/108 advisory on critical cardiovascular/stroke/respiratory emergencies.
    """
    return evaluate_triage(
        symptoms_text=payload.symptoms,
        chief_complaint=payload.chief_complaint or "",
        severity_level=payload.severity
    )
