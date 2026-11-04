from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.database import get_db
from app.core.config import settings
from app.models.user import User, PatientProfile
from app.models.doctor import Doctor
from app.schemas.all_schemas import RequestOTP, VerifyOTP, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

@router.post("/request-otp")
def request_otp(payload: RequestOTP):
    """
    Step 1: Sign up + consent (Phone / Email OTP).
    In local/test mode, OTP is fixed to '123456' for instant testing.
    """
    identifier = payload.phone_or_email.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Phone or email is required")
        
    return {
        "success": True,
        "message": f"Verification OTP sent to {identifier}",
        "simulated_otp": "123456",
        "expires_in_seconds": 300
    }

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOTP, db: Session = Depends(get_db)):
    """Verifies OTP and logs in / registers the user."""
    identifier = payload.phone_or_email.strip()
    if payload.otp != "123456":
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please enter 123456")
        
    # Check if user exists
    user = db.query(User).filter((User.phone == identifier) | (User.email == identifier)).first()
    
    if not user:
        is_email = "@" in identifier
        user = User(
            email=identifier if is_email else None,
            phone=identifier if not is_email else None,
            full_name=payload.full_name or "Ayur Practitioner",
            role="patient"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default patient profile
        profile = PatientProfile(user_id=user.id, consent_given=True)
        db.add(profile)
        db.commit()
        
    token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.full_name})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "phone_or_email": identifier
    }

@router.get("/me")
def get_current_user_profile(user_id: int = 1, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Return fallback demo user
        return {
            "id": 1,
            "full_name": "Dr. Hitanshu Choraria",
            "role": "doctor",
            "email": "hitanshu@ayurllm.org",
            "phone": "+91 9876543210"
        }
    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "email": user.email,
        "phone": user.phone
    }
