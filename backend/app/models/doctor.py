from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, index=True)
    registration_number = Column(String, index=True, nullable=True)
    state_council = Column(String, default="Ayurvedic Central Council of Medicine")
    qualification = Column(String, default="BAMS, MD (Ayurveda)")
    specialty = Column(String, default="Kayachikitsa (General Medicine)") # Kayachikitsa, Panchakarma, Shalya, Shalakya, Kaumarbhritya
    experience_years = Column(Integer, default=5)
    bio = Column(Text, default="")
    avatar_url = Column(String, nullable=True)
    consultation_fee = Column(Float, default=500.0)
    languages = Column(String, default="English, Hindi, Sanskrit")
    
    # Verification pipeline
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String, default="Unverified") # "Unverified", "Pending_Review", "Verified", "Rejected"
    is_kaggle_seed = Column(Boolean, default=False)
    degree_document_url = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    recheck_due_at = Column(DateTime, nullable=True)
    
    # Review metrics for Bayesian Rating
    # Bayesian Rating = (C * m + sum_ratings) / (C + total_reviews)
    # Default prior: C = 5 reviews, m = 3.5 prior mean rating
    total_reviews = Column(Integer, default=0)
    sum_ratings = Column(Float, default=0.0)
    raw_average_rating = Column(Float, default=0.0)
    bayesian_rating = Column(Float, default=3.5)
    
    # Component metrics for Trust Score (0 - 100)
    # Trust score = 40% rating + 20% verification + 15% experience + 10% completion rate + 10% response time + 5% profile
    completion_rate = Column(Float, default=95.0) # Percentage 0 - 100
    avg_response_time_hours = Column(Float, default=1.5) # In hours
    profile_completeness = Column(Float, default=85.0) # Percentage 0 - 100
    trust_score = Column(Float, default=65.0) # Calculated score 0 - 100
    
    user = relationship("User", back_populates="doctor_profile")
    reviews = relationship("DoctorReview", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

class DoctorReview(Base):
    __tablename__ = "doctor_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("users.id"))
    consultation_id = Column(Integer, nullable=True) # Must be linked to completed paid consult
    rating = Column(Float) # 1.0 to 5.0
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    doctor = relationship("Doctor", back_populates="reviews")
