from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.triage_service import evaluate_triage
from app.services.rag_service import search_shlokas
from app.models.user import User, PatientProfile
from app.models.doctor import Doctor
from app.schemas.all_schemas import IntakeSubmission, TriageResponse

router = APIRouter(prefix="/intake", tags=["Intake & Prakriti"])

PRAKRITI_QUESTIONS = [
    {
        "id": 1,
        "category": "Body Frame (Sharira Sansthana)",
        "question": "How would you describe your natural physical body build?",
        "options": [
            {"type": "vata", "text": "Slender, light bones, prominent joints, difficulty gaining weight"},
            {"type": "pitta", "text": "Medium, athletic build, symmetrical, well-proportioned"},
            {"type": "kapha", "text": "Broad, heavy bones, sturdy frame, easily gains weight"}
        ]
    },
    {
        "id": 2,
        "category": "Skin & Complexion (Tvak Lakshana)",
        "question": "What is the natural texture and sensation of your skin?",
        "options": [
            {"type": "vata", "text": "Dry, rough, thin, prone to cracking in cold weather"},
            {"type": "pitta", "text": "Warm, sensitive, prone to redness, moles, or acne"},
            {"type": "kapha", "text": "Thick, soft, cool, oily, well-hydrated"}
        ]
    },
    {
        "id": 3,
        "category": "Digestion & Appetite (Jatharagni)",
        "question": "How does your hunger and digestive capacity behave day-to-day?",
        "options": [
            {"type": "vata", "text": "Irregular (Vishama Agni): sometimes ravenous, sometimes skips meals"},
            {"type": "pitta", "text": "Sharp & intense (Tikshna Agni): becomes irritable if meals are delayed"},
            {"type": "kapha", "text": "Slow & steady (Manda Agni): can easily skip meals without discomfort"}
        ]
    },
    {
        "id": 4,
        "category": "Sleep Quality (Nidra)",
        "question": "How is the quality of your nocturnal sleep?",
        "options": [
            {"type": "vata", "text": "Light, easily awakened by minor noises, tendency for insomnia"},
            {"type": "pitta", "text": "Moderate (6-7 hrs), vivid or fiery dreams, feels refreshed quickly"},
            {"type": "kapha", "text": "Deep, heavy, prolonged (8+ hrs), difficulty waking up in the morning"}
        ]
    },
    {
        "id": 5,
        "category": "Mind & Stress Response (Manasa Prakriti)",
        "question": "Under high stress or exhaustion, what is your primary psychological reaction?",
        "options": [
            {"type": "vata", "text": "Anxiety, racing thoughts, restlessness, hyper-worry"},
            {"type": "pitta", "text": "Impatience, irritability, critical judgment, fiery frustration"},
            {"type": "kapha", "text": "Lethargy, procrastination, emotional withdrawal, comfort eating"}
        ]
    }
]

@router.get("/prakriti-quiz")
def get_prakriti_quiz():
    """Returns the standardized clinical Prakriti assessment questionnaire."""
    return {
        "title": "Classical Ayurveda Prakriti Diagnostic Matrix",
        "description": "Determines constitutional Dosha ratio (Vata-Pitta-Kapha) across physical and metabolic traits.",
        "questions": PRAKRITI_QUESTIONS
    }

@router.post("/submit")
def submit_intake(payload: IntakeSubmission, db: Session = Depends(get_db)):
    """
    Step 2: Intake form (disease, symptoms, medications, prakriti).
    Step 3: Red-flag triage rule-based check before any result.
    Step 4 & 5: Hybrid search & Shloka insights if cleared.
    """
    # 1. Red-flag triage check
    symptoms_str = ", ".join(payload.symptoms)
    triage_result = evaluate_triage(
        symptoms_text=symptoms_str,
        chief_complaint=payload.chief_complaint,
        severity_level=payload.severity_level
    )
    
    # Calculate Prakriti from answers if provided
    vata_count = 0
    pitta_count = 0
    kapha_count = 0
    
    if payload.prakriti_answers:
        for ans in payload.prakriti_answers:
            if ans.selected_option == "vata":
                vata_count += 1
            elif ans.selected_option == "pitta":
                pitta_count += 1
            elif ans.selected_option == "kapha":
                kapha_count += 1
                
    total_answers = max(1, vata_count + pitta_count + kapha_count)
    vata_pct = round((vata_count / total_answers) * 100) if payload.prakriti_answers else 35
    pitta_pct = round((pitta_count / total_answers) * 100) if payload.prakriti_answers else 45
    kapha_pct = round((kapha_count / total_answers) * 100) if payload.prakriti_answers else 20
    
    # Determine primary and secondary prakriti
    scores = [("Vata", vata_pct), ("Pitta", pitta_pct), ("Kapha", kapha_pct)]
    scores.sort(key=lambda x: x[1], reverse=True)
    primary_prakriti = scores[0][0]
    secondary_prakriti = scores[1][0]
    prakriti_name = f"{primary_prakriti}-{secondary_prakriti}"
    
    # If red flag: halt automated therapeutic retrieval
    if triage_result["is_red_flag"]:
        return {
            "triage": triage_result,
            "prakriti": {
                "name": prakriti_name,
                "vata": vata_pct,
                "pitta": pitta_pct,
                "kapha": kapha_pct
            },
            "shlokas": [],
            "matched_doctors": []
        }
        
    # Cleared: Retrieve classical shlokas (RAG)
    query_text = f"{payload.chief_complaint} {symptoms_str}"
    shloka_insights = search_shlokas(query=query_text, limit=6)
    
    # Fetch top matched doctors
    doctors = db.query(Doctor).filter(Doctor.is_verified == True).order_by(Doctor.trust_score.desc()).limit(4).all()
    if not doctors:
        doctors = db.query(Doctor).order_by(Doctor.trust_score.desc()).limit(4).all()
        
    doctor_matches = []
    for d in doctors:
        doctor_matches.append({
            "id": d.id,
            "name": d.name,
            "qualification": d.qualification,
            "specialty": d.specialty,
            "experience_years": d.experience_years,
            "consultation_fee": d.consultation_fee,
            "is_verified": d.is_verified,
            "trust_score": d.trust_score,
            "bayesian_rating": d.bayesian_rating,
            "avatar_url": d.avatar_url
        })
        
    return {
        "triage": triage_result,
        "prakriti": {
            "name": prakriti_name,
            "primary": primary_prakriti,
            "secondary": secondary_prakriti,
            "vata": vata_pct,
            "pitta": pitta_pct,
            "kapha": kapha_pct
        },
        "shlokas": shloka_insights,
        "matched_doctors": doctor_matches
    }
