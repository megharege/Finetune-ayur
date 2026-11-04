from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, default="Ayur User")
    role = Column(String, default="patient")  # "patient", "doctor", "admin"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    prakriti_primary = Column(String, default="Vata-Pitta")  # Vata, Pitta, Kapha, or combinations
    prakriti_secondary = Column(String, default="Pitta")
    vata_score = Column(Integer, default=35)
    pitta_score = Column(Integer, default=45)
    kapha_score = Column(Integer, default=20)
    current_medications = Column(Text, default="")
    allergies = Column(Text, default="")
    medical_history = Column(Text, default="")
    emergency_contact = Column(String, nullable=True)
    consent_given = Column(Boolean, default=True)
    consent_timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="patient_profile")
