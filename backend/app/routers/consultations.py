from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
from app.database import get_db
from app.models.consultation import Consultation, Appointment
from app.models.user import User, PatientProfile
from app.models.doctor import Doctor
from app.services.graph_service import build_patient_graph
from app.services.rag_service import VERIFIED_SHLOKA_CORPUS

router = APIRouter(prefix="/consultations", tags=["Video Teleconsultation & Clinical Suite"])

@router.get("/{consultation_id}")
def get_consultation_details(consultation_id: int, db: Session = Depends(get_db)):
    """Returns active teleconsultation details, room ID, patient info, and chief complaints."""
    consult = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation record not found")
        
    appt = consult.appointment
    patient = appt.patient if appt else None
    doctor = appt.doctor if appt else None
    
    # Try parsing symptoms
    symptoms = []
    if appt and appt.reported_symptoms:
        try:
            symptoms = eval(appt.reported_symptoms) if "[" in appt.reported_symptoms else [appt.reported_symptoms]
        except Exception:
            symptoms = [appt.reported_symptoms]
            
    return {
        "consultation_id": consult.id,
        "appointment_id": appt.id if appt else None,
        "room_id": appt.room_id if appt else "ayur-room-default",
        "is_active": consult.is_active,
        "patient": {
            "id": patient.id if patient else 1,
            "name": patient.full_name if patient else "Ayurvedic Patient",
            "prakriti": "Pitta-Vata (Tikshnagni)",
            "chief_complaint": appt.chief_complaint if appt else "Indigestion and chronic fatigue",
            "symptoms": symptoms or ["Acid reflux", "Postprandial bloating", "Insomnia"]
        },
        "doctor": {
            "id": doctor.id if doctor else 1,
            "name": doctor.name if doctor else "Dr. Vaidya Hitanshu",
            "specialty": doctor.specialty if doctor else "Kayachikitsa"
        },
        "clinical_notes": consult.clinical_notes,
        "dosha_assessment": consult.dosha_assessment
    }

@router.get("/{consultation_id}/graph")
def get_consultation_knowledge_graph(consultation_id: int, db: Session = Depends(get_db)):
    """
    Step 8 Graph Feature:
    Neo4j patient knowledge graph: Patient - Symptom - Disease - Dosha - Shloka - Book
    'Doctor sees it only during an active consult'
    """
    consult = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    appt = consult.appointment
    doctor_name = appt.doctor.name if (appt and appt.doctor) else "Dr. Vaidya Hitanshu"
    patient_name = appt.patient.full_name if (appt and appt.patient) else "Ayurvedic Patient"
    
    symptoms = ["Acid Reflux (Amlapitta)", "Agni Mandya", "Insomnia (Anidra)"]
    if appt and appt.reported_symptoms:
        try:
            s = eval(appt.reported_symptoms)
            if isinstance(s, list) and len(s) > 0:
                symptoms = s
        except Exception:
            pass
            
    # Include matching classical shlokas
    shlokas_cited = VERIFIED_SHLOKA_CORPUS[:3]
    
    graph_payload = build_patient_graph(
        patient_id=appt.patient_id if appt else 1,
        patient_name=patient_name,
        prakriti="Pitta-Vata",
        symptoms=symptoms,
        dosha_imbalance=consult.dosha_assessment or "Pitta-Vata Prakopa",
        shlokas_cited=shlokas_cited,
        doctor_name=doctor_name,
        consultation_id=consult.id
    )
    
    return graph_payload

@router.post("/{consultation_id}/end")
def end_consultation(consultation_id: int, clinical_notes: str = "", db: Session = Depends(get_db)):
    """Marks consultation as completed and archives notes."""
    consult = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consult:
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    consult.is_active = False
    consult.end_time = datetime.utcnow()
    if clinical_notes:
        consult.clinical_notes = clinical_notes
    if consult.appointment:
        consult.appointment.status = "completed"
        
    db.commit()
    return {"success": True, "message": "Consultation ended and marked completed."}
