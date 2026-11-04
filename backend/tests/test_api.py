import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.trust_score_service import calculate_bayesian_rating, calculate_trust_score
from app.services.triage_service import evaluate_triage

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["classical_texts"] == 8

def test_bayesian_rating_formula():
    # C=5, m=3.5
    # Doctor with 2 five-star reviews: sum=10, n=2 => (5*3.5 + 10) / (5 + 2) = 27.5 / 7 = 3.93 (NOT 5.0!)
    r1 = calculate_bayesian_rating(sum_ratings=10.0, total_reviews=2, C=5.0, m=3.5)
    assert r1 == 3.93
    
    # Doctor with 100 reviews averaging 4.8: sum=480, n=100 => (17.5 + 480) / 105 = 497.5 / 105 = 4.74
    r2 = calculate_bayesian_rating(sum_ratings=480.0, total_reviews=100, C=5.0, m=3.5)
    assert r2 == 4.74
    # Proven: Doctor with 2 reviews CANNOT outrank doctor with 100 high reviews
    assert r2 > r1

def test_trust_score_formula():
    # Trust score = 40% rating + 20% verification + 15% experience + 10% completion + 10% response + 5% profile
    res = calculate_trust_score(
        bayesian_rating=4.5,
        is_verified=True,
        experience_years=20,
        completion_rate=100.0,
        avg_response_time_hours=0.5,
        profile_completeness=100.0,
        is_kaggle_seed=False
    )
    # (4.5/5)*40 + 20*1.0 + 15*1.0 + 10*1.0 + 10*1.0 + 5*1.0 = 36 + 20 + 15 + 10 + 10 + 5 = 96.0
    assert res["trust_score"] == 96.0
    assert "breakdown" in res

def test_red_flag_triage():
    # Cardiac emergency triggers 112/108
    t1 = evaluate_triage(symptoms_text="I have severe crushing chest pain radiating to left arm", chief_complaint="Chest pain")
    assert t1["is_red_flag"] is True
    assert "112" in t1["emergency_numbers"]
    
    # Benign Ayurvedic symptom clears triage
    t2 = evaluate_triage(symptoms_text="Mild indigestion after eating heavy lentils, slight bloating", chief_complaint="Indigestion", severity_level=3)
    assert t2["is_red_flag"] is False
    assert t2["status"] == "TRIAGE_CLEARED"

def test_auth_otp_flow():
    req = client.post("/api/auth/request-otp", json={"phone_or_email": "+919876543210"})
    assert req.status_code == 200
    
    verify = client.post("/api/auth/verify-otp", json={"phone_or_email": "+919876543210", "otp": "123456", "full_name": "Test Vaidya"})
    assert verify.status_code == 200
    data = verify.json()
    assert "access_token" in data
    assert data["role"] in ["patient", "doctor"]

def test_classical_search():
    res = client.get("/api/search?q=Triphala")
    assert res.status_code == 200
    data = res.json()
    assert data["total_returned"] > 0
    first_verse = data["results"][0]
    assert "sanskrit" in first_verse
    assert "chunk_id" in first_verse

def test_doctor_directory_ranking():
    res = client.get("/api/doctors")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 3
    # Check that verified doctor ranks higher than unverified seed
    assert docs[0]["trust_score"] >= docs[-1]["trust_score"]

def test_patient_knowledge_graph():
    res = client.get("/api/consultations/1/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "links" in data
    types = [n["type"] for n in data["nodes"]]
    assert "Patient" in types
    assert "Doctor" in types
    assert "Dosha" in types
    assert "Shloka" in types
