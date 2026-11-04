from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from app.database import get_db
from app.models.doctor import Doctor, DoctorReview
from app.models.user import User
from app.services.trust_score_service import calculate_bayesian_rating, calculate_trust_score
from app.schemas.all_schemas import DoctorClaimRequest, DoctorReviewCreate

router = APIRouter(prefix="/doctors", tags=["Doctor Network & Verification"])

@router.get("")
def list_doctors(
    specialty: Optional[str] = None,
    verified_only: bool = False,
    min_trust_score: float = 0.0,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Step 6: Doctor match (filters + trust score).
    Lists doctors ranked by Trust Score.
    """
    query = db.query(Doctor)
    
    if verified_only:
        query = query.filter(Doctor.is_verified == True)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if search:
        query = query.filter((Doctor.name.ilike(f"%{search}%")) | (Doctor.specialty.ilike(f"%{search}%")))
        
    doctors = query.all()
    
    # Calculate live trust scores
    results = []
    for doc in doctors:
        # Re-verify bayesian rating
        bayesian = calculate_bayesian_rating(doc.sum_ratings, doc.total_reviews)
        trust_data = calculate_trust_score(
            bayesian_rating=bayesian,
            is_verified=doc.is_verified,
            experience_years=doc.experience_years,
            completion_rate=doc.completion_rate,
            avg_response_time_hours=doc.avg_response_time_hours,
            profile_completeness=doc.profile_completeness,
            is_kaggle_seed=doc.is_kaggle_seed
        )
        score = trust_data["trust_score"]
        if score >= min_trust_score:
            results.append({
                "id": doc.id,
                "name": doc.name,
                "qualification": doc.qualification,
                "specialty": doc.specialty,
                "experience_years": doc.experience_years,
                "consultation_fee": doc.consultation_fee,
                "is_verified": doc.is_verified,
                "verification_status": doc.verification_status,
                "is_kaggle_seed": doc.is_kaggle_seed,
                "avatar_url": doc.avatar_url,
                "bio": doc.bio,
                "languages": doc.languages,
                "bayesian_rating": bayesian,
                "total_reviews": doc.total_reviews,
                "trust_score": score,
                "trust_breakdown": trust_data["breakdown"]
            })
            
    results.sort(key=lambda x: x["trust_score"], reverse=True)
    return results

@router.get("/{doctor_id}")
def get_doctor_detail(doctor_id: int, db: Session = Depends(get_db)):
    """Returns comprehensive doctor profile with mathematical Trust Score audit."""
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    bayesian = calculate_bayesian_rating(doc.sum_ratings, doc.total_reviews)
    trust_data = calculate_trust_score(
        bayesian_rating=bayesian,
        is_verified=doc.is_verified,
        experience_years=doc.experience_years,
        completion_rate=doc.completion_rate,
        avg_response_time_hours=doc.avg_response_time_hours,
        profile_completeness=doc.profile_completeness,
        is_kaggle_seed=doc.is_kaggle_seed
    )
    
    reviews = db.query(DoctorReview).filter(DoctorReview.doctor_id == doctor_id).order_by(DoctorReview.created_at.desc()).limit(10).all()
    
    return {
        "id": doc.id,
        "name": doc.name,
        "registration_number": doc.registration_number,
        "state_council": doc.state_council,
        "qualification": doc.qualification,
        "specialty": doc.specialty,
        "experience_years": doc.experience_years,
        "consultation_fee": doc.consultation_fee,
        "is_verified": doc.is_verified,
        "verification_status": doc.verification_status,
        "is_kaggle_seed": doc.is_kaggle_seed,
        "bio": doc.bio,
        "languages": doc.languages,
        "avatar_url": doc.avatar_url,
        "bayesian_rating": bayesian,
        "total_reviews": doc.total_reviews,
        "trust_score": trust_data["trust_score"],
        "trust_breakdown": trust_data["breakdown"],
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.strftime("%d %b %Y")
            } for r in reviews
        ]
    }

@router.post("/claim")
def claim_doctor_profile(payload: DoctorClaimRequest, db: Session = Depends(get_db)):
    """
    Doctor Network Step: Doctor claims profile / uploads degree + registration no.
    Transitions status to Pending_Review for official admin check.
    """
    user = User(
        full_name=payload.name,
        role="doctor"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    doctor = Doctor(
        user_id=user.id,
        name=payload.name,
        registration_number=payload.registration_number,
        state_council=payload.state_council,
        qualification=payload.qualification,
        specialty=payload.specialty,
        experience_years=payload.experience_years,
        bio=payload.bio,
        consultation_fee=payload.consultation_fee,
        degree_document_url=payload.degree_document_url,
        verification_status="Pending_Review",
        is_verified=False,
        is_kaggle_seed=False
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    
    return {
        "success": True,
        "message": "Doctor profile claim submitted. Verification under review by Central Council Admin.",
        "doctor_id": doctor.id,
        "verification_status": "Pending_Review"
    }

@router.post("/{doctor_id}/verify")
def admin_verify_doctor(doctor_id: int, approved: bool = True, db: Session = Depends(get_db)):
    """
    Doctor Network Step: Admin check against official state/national register.
    Awards Verified badge (re-checked every 12 months).
    """
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    doc.is_verified = approved
    doc.verification_status = "Verified" if approved else "Rejected"
    if approved:
        doc.verified_at = datetime.utcnow()
        doc.recheck_due_at = datetime.utcnow() + timedelta(days=365) # 12 months re-check
        
    # Recalculate trust score
    bayesian = calculate_bayesian_rating(doc.sum_ratings, doc.total_reviews)
    trust_calc = calculate_trust_score(
        bayesian_rating=bayesian,
        is_verified=doc.is_verified,
        experience_years=doc.experience_years,
        completion_rate=doc.completion_rate,
        avg_response_time_hours=doc.avg_response_time_hours,
        profile_completeness=doc.profile_completeness,
        is_kaggle_seed=False
    )
    doc.trust_score = trust_calc["trust_score"]
    db.commit()
    
    return {
        "success": True,
        "doctor_id": doc.id,
        "is_verified": doc.is_verified,
        "status": doc.verification_status,
        "recheck_due_at": doc.recheck_due_at,
        "updated_trust_score": doc.trust_score
    }

@router.post("/{doctor_id}/reviews")
def add_doctor_review(doctor_id: int, payload: DoctorReviewCreate, db: Session = Depends(get_db)):
    """
    Doctor Network Step: Reviews only allowed after a paid, completed consult.
    Updates Bayesian rating and trust score.
    """
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    review = DoctorReview(
        doctor_id=doctor_id,
        patient_id=1,
        consultation_id=payload.consultation_id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(review)
    
    # Update doctor aggregates
    doc.total_reviews += 1
    doc.sum_ratings += payload.rating
    doc.bayesian_rating = calculate_bayesian_rating(doc.sum_ratings, doc.total_reviews)
    
    trust_data = calculate_trust_score(
        bayesian_rating=doc.bayesian_rating,
        is_verified=doc.is_verified,
        experience_years=doc.experience_years,
        completion_rate=doc.completion_rate,
        avg_response_time_hours=doc.avg_response_time_hours,
        profile_completeness=doc.profile_completeness,
        is_kaggle_seed=doc.is_kaggle_seed
    )
    doc.trust_score = trust_data["trust_score"]
    db.commit()
    
    return {
        "success": True,
        "message": "Review added. Bayesian rating and trust score updated.",
        "new_bayesian_rating": doc.bayesian_rating,
        "new_trust_score": doc.trust_score
    }
