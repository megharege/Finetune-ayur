from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.hospital import PharmacyItem, PanchakarmaTherapy, PanchakarmaBooking
from app.schemas.all_schemas import PanchakarmaBookRequest

router = APIRouter(prefix="/hospital", tags=["Hospital Modules: Pharmacy & Panchakarma"])

@router.get("/pharmacy")
def get_pharmacy_inventory(category: str = None, low_stock: bool = False, db: Session = Depends(get_db)):
    """Hospital Module: Herbal pharmacy stock management and catalog."""
    query = db.query(PharmacyItem)
    if category:
        query = query.filter(PharmacyItem.category.ilike(f"%{category}%"))
    if low_stock:
        query = query.filter(PharmacyItem.stock_quantity <= PharmacyItem.reorder_level)
        
    items = query.all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "botanical_name": item.botanical_name,
            "classical_text": item.classical_text,
            "category": item.category,
            "stock_quantity": item.stock_quantity,
            "reorder_level": item.reorder_level,
            "is_low_stock": item.stock_quantity <= item.reorder_level,
            "unit_price": item.unit_price,
            "dosha_affinity": item.dosha_affinity,
            "indications": item.indications
        } for item in items
    ]

@router.get("/panchakarma")
def list_panchakarma_therapies(db: Session = Depends(get_db)):
    """Hospital Module: Panchakarma therapies catalog and protocol details."""
    therapies = db.query(PanchakarmaTherapy).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "sanskrit_name": t.sanskrit_name,
            "description": t.description,
            "duration_days": t.duration_days,
            "target_dosha": t.target_dosha,
            "price": t.price,
            "requires_doctor_referral": t.requires_doctor_referral,
            "benefits": t.benefits
        } for t in therapies
    ]

@router.post("/panchakarma/book")
def book_panchakarma(payload: PanchakarmaBookRequest, db: Session = Depends(get_db)):
    """Hospital Module: Book an authentic Panchakarma detoxification session."""
    therapy = db.query(PanchakarmaTherapy).filter(PanchakarmaTherapy.id == payload.therapy_id).first()
    if not therapy:
        raise HTTPException(status_code=404, detail="Therapy not found")
        
    booking = PanchakarmaBooking(
        patient_id=1,
        therapy_id=payload.therapy_id,
        start_date=payload.start_date,
        doctor_referral_id=payload.doctor_referral_id,
        status="confirmed"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return {
        "success": True,
        "booking_id": booking.id,
        "therapy_name": therapy.name,
        "start_date": booking.start_date.strftime("%d %B %Y"),
        "duration_days": therapy.duration_days,
        "price": therapy.price,
        "status": "CONFIRMED_PREPARATION_DIET_ASSIGNED"
    }
