from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth ---
class RequestOTP(BaseModel):
    phone_or_email: str
    role: str = "patient" # "patient", "doctor", "admin"

class VerifyOTP(BaseModel):
    phone_or_email: str
    otp: str
    full_name: Optional[str] = "Ayurvedic Patient"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: str
    phone_or_email: str

# --- Intake & Triage ---
class PrakritiQuestionAnswer(BaseModel):
    question_id: int
    selected_option: str # "vata", "pitta", "kapha"

class IntakeSubmission(BaseModel):
    chief_complaint: str
    symptoms: List[str]
    severity_level: int = Field(default=3, ge=1, le=10)
    duration_days: int = 7
    current_medications: Optional[str] = ""
    known_allergies: Optional[str] = ""
    prakriti_answers: Optional[List[PrakritiQuestionAnswer]] = None

class TriageResponse(BaseModel):
    is_red_flag: bool
    status: str
    emergency_numbers: List[str]
    matched_reasons: List[Dict[str, Any]]
    action_required: str
    clinical_disclaimer: str

# --- Search / RAG ---
class SearchRequest(BaseModel):
    query: str
    sthana: Optional[str] = None
    primary_category: Optional[str] = None
    limit: int = 6

# --- Doctor ---
class DoctorClaimRequest(BaseModel):
    name: str
    registration_number: str
    state_council: str
    qualification: str
    specialty: str
    experience_years: int
    bio: str
    consultation_fee: float = 500.0
    degree_document_url: Optional[str] = "https://example.com/degree.pdf"

class DoctorReviewCreate(BaseModel):
    doctor_id: int
    consultation_id: int
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: str

# --- Appointment & Payment ---
class AppointmentBooking(BaseModel):
    doctor_id: int
    slot_time: datetime
    chief_complaint: str
    symptoms: List[str]

class RazorpayVerify(BaseModel):
    appointment_id: int
    razorpay_payment_id: str
    razorpay_order_id: Optional[str] = "order_mock_123"
    razorpay_signature: Optional[str] = "sig_mock_456"

# --- E-Prescription ---
class FormulationItem(BaseModel):
    name: str
    dosage: str
    anupana: str # Carrier e.g. "Warm water", "Honey", "Ghee"
    duration: str

class CitationItem(BaseModel):
    chunk_id: str
    source_book: str
    sanskrit: str
    indication: str

class PrescriptionCreate(BaseModel):
    consultation_id: int
    patient_id: int
    classical_citations: List[CitationItem]
    formulations: List[FormulationItem]
    ahar_diet_plan: str
    vihar_lifestyle_plan: str
    follow_up_advice: str
    dosha_assessment: str

# --- Hospital ---
class PanchakarmaBookRequest(BaseModel):
    therapy_id: int
    start_date: datetime
    doctor_referral_id: Optional[int] = None
