from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class EPrescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), unique=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    
    # Classical citations & RAG reference
    # JSON list of cited chunks: [{"chunk_id": "...", "source_book": "Charaka Samhita", "verse": "...", "sanskrit": "...", "indication": "..."}]
    classical_citations = Column(Text, default="[]")
    
    # Herbal Formulations: [{"name": "Triphala Churna", "dosage": "3g twice daily", "anupana": "Warm water", "duration": "14 days"}]
    formulations = Column(Text, default="[]")
    
    # Ahar (Dietary advice) & Vihar (Lifestyle modifications)
    ahar_diet_plan = Column(Text, default="")
    vihar_lifestyle_plan = Column(Text, default="")
    follow_up_advice = Column(Text, default="")
    
    digital_signature = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    consultation = relationship("Consultation", back_populates="prescription")
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("Doctor", foreign_keys=[doctor_id])
