from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    slot_time = Column(DateTime)
    status = Column(String, default="scheduled")  # scheduled, in_progress, completed, cancelled
    
    # Razorpay Payment
    amount = Column(Float, default=500.0)
    currency = Column(String, default="INR")
    payment_id = Column(String, nullable=True)
    razorpay_order_id = Column(String, nullable=True)
    payment_status = Column(String, default="paid") # pending, paid, refunded
    
    # Clinical intake attached to appointment
    chief_complaint = Column(Text, default="")
    reported_symptoms = Column(Text, default="[]") # JSON list of symptoms
    triage_status = Column(String, default="Clear") # Clear, Warning, Red-Flag
    room_id = Column(String, index=True) # Unique room id for WebRTC call
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("Doctor", back_populates="appointments")
    consultation = relationship("Consultation", back_populates="appointment", uselist=False)

class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    clinical_notes = Column(Text, default="")
    dosha_assessment = Column(String, default="Vata-Pitta Imbalance")
    chat_log = Column(Text, default="[]") # JSON messages
    is_active = Column(Boolean, default=False)
    
    appointment = relationship("Appointment", back_populates="consultation")
    prescription = relationship("EPrescription", back_populates="consultation", uselist=False)
