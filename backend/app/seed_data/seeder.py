from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.user import User, PatientProfile
from app.models.doctor import Doctor, DoctorReview
from app.models.hospital import PharmacyItem, PanchakarmaTherapy
from app.models.consultation import Appointment, Consultation
from app.services.trust_score_service import calculate_bayesian_rating, calculate_trust_score

def seed_database(db: Session):
    """Populates initial verified doctors, Kaggle seeds, pharmacy inventory, and therapies."""
    # Check if already seeded
    if db.query(Doctor).count() > 0:
        return

    print("Seeding AyurLLM Hospital Platform data...")

    # 1. Primary Test Patient
    patient_user = User(
        email="patient@ayurllm.org",
        phone="+919876543210",
        full_name="Ananya Sharma",
        role="patient"
    )
    db.add(patient_user)
    db.commit()
    db.refresh(patient_user)

    patient_profile = PatientProfile(
        user_id=patient_user.id,
        age=32,
        gender="Female",
        prakriti_primary="Pitta-Vata",
        prakriti_secondary="Vata",
        vata_score=35,
        pitta_score=50,
        kapha_score=15,
        medical_history="Chronic acid reflux and occasional anxiety-induced insomnia.",
        current_medications="None regular",
        consent_given=True
    )
    db.add(patient_profile)

    # 2. Doctors:
    # A. Verified Senior Practitioners
    doctors_data = [
        {
            "name": "Dr. Vaidya Hitanshu Choraria",
            "email": "hitanshu@ayurllm.org",
            "registration_number": "CCIM-ND-2021-0941",
            "state_council": "Central Council of Indian Medicine, New Delhi",
            "qualification": "BAMS, MD (Kayachikitsa, NIA Jaipur)",
            "specialty": "Kayachikitsa (Internal Medicine & Metabolic Disorders)",
            "experience_years": 16,
            "bio": "Senior Ayurvedic Physician specializing in chronic autoimmune, digestive, and lifestyle metabolic conditions through classical Brihat Trayi protocols.",
            "avatar_url": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=400&auto=format&fit=crop&q=80",
            "consultation_fee": 800.0,
            "languages": "English, Hindi, Sanskrit",
            "is_verified": True,
            "verification_status": "Verified",
            "is_kaggle_seed": False,
            "total_reviews": 64,
            "sum_ratings": 313.6, # avg 4.9
            "completion_rate": 98.5,
            "avg_response_time_hours": 0.8,
            "profile_completeness": 100.0
        },
        {
            "name": "Dr. Vaidya Megha Rege",
            "email": "megha@ayurllm.org",
            "registration_number": "MAH-AYUR-2019-4402",
            "state_council": "Maharashtra Council of Indian Medicine, Mumbai",
            "qualification": "BAMS, MS (Shalakya Tantra, IPGT&RA Jamnagar)",
            "specialty": "Shalakya & Panchakarma (ENT, Ophthalmology & Detox)",
            "experience_years": 14,
            "bio": "Gold medalist Ayurvedic Surgeon and Panchakarma Specialist focusing on sensory organ disorders, degenerative ocular conditions, and deep bio-purification.",
            "avatar_url": "https://images.unsplash.com/photo-1594824813589-98782a20b925?w=400&auto=format&fit=crop&q=80",
            "consultation_fee": 750.0,
            "languages": "English, Hindi, Marathi",
            "is_verified": True,
            "verification_status": "Verified",
            "is_kaggle_seed": False,
            "total_reviews": 48,
            "sum_ratings": 230.4, # avg 4.8
            "completion_rate": 96.0,
            "avg_response_time_hours": 1.2,
            "profile_completeness": 95.0
        },
        {
            "name": "Dr. Anand Jadon",
            "email": "anand@ayurllm.org",
            "registration_number": "UP-AYUR-2018-7719",
            "state_council": "Board of Ayurvedic and Unani Systems, Uttar Pradesh",
            "qualification": "BAMS, MD (Dravya Guna, BHU Varanasi)",
            "specialty": "Dravya Guna & Rasayana (Classical Herbology & Longevity)",
            "experience_years": 11,
            "bio": "Expert pharmacologist and clinical researcher in botanical formulations, polyherbal synergy, and geriatric rejuvenation therapies.",
            "avatar_url": "https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=400&auto=format&fit=crop&q=80",
            "consultation_fee": 600.0,
            "languages": "English, Hindi",
            "is_verified": True,
            "verification_status": "Verified",
            "is_kaggle_seed": False,
            "total_reviews": 32,
            "sum_ratings": 150.4, # avg 4.7
            "completion_rate": 94.0,
            "avg_response_time_hours": 1.5,
            "profile_completeness": 90.0
        },
        # B. Kaggle Dataset Seed Doctors (Required to be UNVERIFIED until official claimed)
        {
            "name": "Dr. Rameshwar Nath Shastri (Kaggle Seed)",
            "email": "rameshwar.seed@ayurllm.org",
            "registration_number": "PENDING-CLAIM",
            "state_council": "Listed in Kaggle National Practitioner Dataset",
            "qualification": "BAMS (Ayurveda)",
            "specialty": "Kayachikitsa (General Medicine)",
            "experience_years": 8,
            "bio": "Practitioner listed in initial open-source Kaggle healthcare registry. Profile awaiting physician claim and registration credential upload.",
            "avatar_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=400&auto=format&fit=crop&q=80",
            "consultation_fee": 400.0,
            "languages": "Hindi",
            "is_verified": False,
            "verification_status": "Unverified",
            "is_kaggle_seed": True,
            "total_reviews": 2,
            "sum_ratings": 10.0, # 2 five-star reviews (Bayesian rating will prevent outranking!)
            "completion_rate": 80.0,
            "avg_response_time_hours": 18.0,
            "profile_completeness": 45.0
        },
        {
            "name": "Dr. Sunita Kulkarni (Kaggle Seed)",
            "email": "sunita.seed@ayurllm.org",
            "registration_number": "PENDING-CLAIM",
            "state_council": "Listed in Kaggle National Practitioner Dataset",
            "qualification": "BAMS",
            "specialty": "Prasuti Tantra (Women's Health)",
            "experience_years": 6,
            "bio": "Practitioner listed in initial open-source Kaggle directory. Requires state registry check before Verified badge can be granted.",
            "avatar_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&auto=format&fit=crop&q=80",
            "consultation_fee": 450.0,
            "languages": "English, Marathi",
            "is_verified": False,
            "verification_status": "Unverified",
            "is_kaggle_seed": True,
            "total_reviews": 4,
            "sum_ratings": 16.0,
            "completion_rate": 85.0,
            "avg_response_time_hours": 12.0,
            "profile_completeness": 50.0
        }
    ]

    created_doctors = []
    for d in doctors_data:
        u = User(
            email=d["email"],
            full_name=d["name"],
            role="doctor"
        )
        db.add(u)
        db.commit()
        db.refresh(u)

        bayesian = calculate_bayesian_rating(d["sum_ratings"], d["total_reviews"])
        trust_calc = calculate_trust_score(
            bayesian_rating=bayesian,
            is_verified=d["is_verified"],
            experience_years=d["experience_years"],
            completion_rate=d["completion_rate"],
            avg_response_time_hours=d["avg_response_time_hours"],
            profile_completeness=d["profile_completeness"],
            is_kaggle_seed=d["is_kaggle_seed"]
        )

        doc = Doctor(
            user_id=u.id,
            name=d["name"],
            registration_number=d["registration_number"],
            state_council=d["state_council"],
            qualification=d["qualification"],
            specialty=d["specialty"],
            experience_years=d["experience_years"],
            bio=d["bio"],
            avatar_url=d["avatar_url"],
            consultation_fee=d["consultation_fee"],
            languages=d["languages"],
            is_verified=d["is_verified"],
            verification_status=d["verification_status"],
            is_kaggle_seed=d["is_kaggle_seed"],
            total_reviews=d["total_reviews"],
            sum_ratings=d["sum_ratings"],
            bayesian_rating=bayesian,
            completion_rate=d["completion_rate"],
            avg_response_time_hours=d["avg_response_time_hours"],
            profile_completeness=d["profile_completeness"],
            trust_score=trust_calc["trust_score"]
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        created_doctors.append(doc)

    # 3. Pharmacy Items
    pharmacy_catalog = [
        {
            "name": "Triphala Churna",
            "botanical_name": "Terminalia chebula, Terminalia bellirica, Phyllanthus emblica",
            "classical_text": "Sharangadhara Samhita",
            "category": "Churna",
            "stock_quantity": 85,
            "reorder_level": 20,
            "unit_price": 180.0,
            "indications": "Digestive sluggishness, gentle bowel regulation, ocular fatigue, Kapha-Pitta balance",
            "dosha_affinity": "Tridoshahara"
        },
        {
            "name": "Ashwagandharishta",
            "botanical_name": "Withania somnifera compound ferment",
            "classical_text": "Bhavaprakasha V1",
            "category": "Asava/Arishta",
            "stock_quantity": 42,
            "reorder_level": 15,
            "unit_price": 240.0,
            "indications": "Vata vyadhi, nervous exhaustion, debility, mental stress, sleep latency",
            "dosha_affinity": "Vatahara"
        },
        {
            "name": "Brahmi Vati (Gold Pearl)",
            "botanical_name": "Bacopa monnieri compound",
            "classical_text": "Charaka Samhita",
            "category": "Vati",
            "stock_quantity": 60,
            "reorder_level": 10,
            "unit_price": 320.0,
            "indications": "Cognitive clarity, memory enhancement (Medhya Rasayana), stress management",
            "dosha_affinity": "Pitta-Vata Shamaka"
        },
        {
            "name": "Ksheerabala Taila (101 Aavartana)",
            "botanical_name": "Sida cordifolia infused sesame milk oil",
            "classical_text": "Astanga Hridaya",
            "category": "Taila",
            "stock_quantity": 8, # Low stock alert!
            "reorder_level": 12,
            "unit_price": 450.0,
            "indications": "Neurological Vata disorders, sciatica, cervical spondylosis, soothing abhyanga",
            "dosha_affinity": "Vatahara"
        },
        {
            "name": "Mahasudarshana Ghanvati",
            "botanical_name": "Swertia chirata & 52 polyherbal synergy",
            "classical_text": "Madhava Nidana",
            "category": "Vati",
            "stock_quantity": 75,
            "reorder_level": 20,
            "unit_price": 210.0,
            "indications": "Ama digestion, intermittent fever (Jwara), acute toxic Pitta accumulation",
            "dosha_affinity": "Pitta-Kapha Shamaka"
        }
    ]

    for p in pharmacy_catalog:
        item = PharmacyItem(**p)
        db.add(item)

    # 4. Panchakarma Therapies
    therapies_catalog = [
        {
            "name": "Shirodhara (Nervous System Soothing)",
            "sanskrit_name": "शिरोधारा",
            "description": "Continuous, rhythmic stream of warm medicated herbal oil gently poured across the forehead (Ajna Chakra) to recalibrate brainwave frequencies.",
            "duration_days": 7,
            "target_dosha": "Vata-Pitta",
            "price": 6500.0,
            "requires_doctor_referral": True,
            "benefits": "Deep nervous system reset, chronic insomnia relief, hypertension mitigation, anxiety dissipation."
        },
        {
            "name": "Virechana (Metabolic & Liver Purging)",
            "sanskrit_name": "विरेचन कर्म",
            "description": "Controlled therapeutic purgation targeting accumulated Pitta toxins from the liver, gallbladder, and small intestine through herbal ghee preparation.",
            "duration_days": 14,
            "target_dosha": "Pitta",
            "price": 12500.0,
            "requires_doctor_referral": True,
            "benefits": "Clears refractory dermatitis, psoriasis, chronic hyperacidity, liver sluggishness, and metabolic syndrome."
        },
        {
            "name": "Basti Karma (Medicated Enema Therapy)",
            "sanskrit_name": "बस्ति कर्म",
            "description": "The mother of all treatments for Vata. Alternating decoction (Niruha) and lipid (Anuvasana) herbal enemas to nourish the colon and bone tissue.",
            "duration_days": 8,
            "target_dosha": "Vata",
            "price": 8500.0,
            "requires_doctor_referral": True,
            "benefits": "Reverses joint degeneration, arthritis, chronic constipation, sciatica, neuromuscular stiffness."
        },
        {
            "name": "Nasya (Sensory & Sinus Purification)",
            "sanskrit_name": "नास्य कर्म",
            "description": "Administration of potent medicated oils into nasal passages following facial steam and massage, clearing the supra-clavicular region.",
            "duration_days": 5,
            "target_dosha": "Kapha",
            "price": 4200.0,
            "requires_doctor_referral": False,
            "benefits": "Relieves chronic sinusitis, migraine, cervical stiffness, and optimizes pituitary-hypothalamic function."
        }
    ]

    for t in therapies_catalog:
        therapy = PanchakarmaTherapy(**t)
        db.add(therapy)

    # 5. Seed an active appointment and consultation for instant testing
    first_doctor = created_doctors[0]
    sample_appt = Appointment(
        patient_id=patient_user.id,
        doctor_id=first_doctor.id,
        slot_time=datetime.utcnow() + timedelta(hours=2),
        amount=first_doctor.consultation_fee,
        status="in_progress",
        payment_status="paid",
        chief_complaint="Severe hyperacidity with sour belching and sleep disruption",
        reported_symptoms="['Acid Reflux (Amlapitta)', 'Heartburn (Vidaha)', 'Insomnia (Anidra)']",
        triage_status="Clear",
        room_id="ayur-consult-live-101"
    )
    db.add(sample_appt)
    db.commit()
    db.refresh(sample_appt)

    sample_consult = Consultation(
        appointment_id=sample_appt.id,
        start_time=datetime.utcnow() - timedelta(minutes=10),
        clinical_notes="Patient presents with secondary Pitta vitiation manifesting as Amlapitta and Tikshnagni. Prescribed cooling Pitta-Shamaka herbs and Shatavari ghee.",
        dosha_assessment="Pitta-Vata Prakopa (Vidagdha Ajeerna)",
        is_active=True
    )
    db.add(sample_consult)
    db.commit()

    print("Database seeding completed successfully.")
