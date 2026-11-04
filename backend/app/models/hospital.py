from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from datetime import datetime
from app.database import Base

class PharmacyItem(Base):
    __tablename__ = "pharmacy_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    botanical_name = Column(String, default="")
    classical_text = Column(String, default="Charaka Samhita")
    category = Column(String, default="Churna") # Churna, Vati, Asava/Arishta, Taila, Ghrita, Rasayana
    stock_quantity = Column(Integer, default=50)
    reorder_level = Column(Integer, default=10)
    unit_price = Column(Float, default=150.0)
    indications = Column(String, default="")
    ingredients = Column(Text, default="")
    dosha_affinity = Column(String, default="Tridoshahara") # Vatahara, Pittahara, Kaphahara, Tridoshahara

class PanchakarmaTherapy(Base):
    __tablename__ = "panchakarma_therapies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Vamana, Virechana, Basti, Nasya, Raktamokshana, Shirodhara, Abhyanga
    sanskrit_name = Column(String, default="")
    description = Column(Text)
    duration_days = Column(Integer, default=7)
    target_dosha = Column(String, default="Vata")
    price = Column(Float, default=4500.0)
    requires_doctor_referral = Column(Boolean, default=True)
    benefits = Column(Text)

class PanchakarmaBooking(Base):
    __tablename__ = "panchakarma_bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    therapy_id = Column(Integer, ForeignKey("panchakarma_therapies.id"))
    start_date = Column(DateTime)
    status = Column(String, default="confirmed") # confirmed, in_progress, completed, cancelled
    doctor_referral_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
