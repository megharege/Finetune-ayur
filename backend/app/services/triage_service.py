import re

RED_FLAG_PATTERNS = [
    {
        "category": "Cardiac Emergency",
        "keywords": ["chest pain", "crushing chest", "radiating to jaw", "radiating to left arm", "heart attack", "chhati me dard", "dil ka daura"],
        "severity": "CRITICAL",
        "emergency_advice": "Immediate emergency room care required. Call 112 (National Emergency) or 108 (Ambulance) immediately. Do not drive yourself."
    },
    {
        "category": "Cerebrovascular (Stroke)",
        "keywords": ["facial drooping", "slurred speech", "sudden paralysis", "arm weakness", "loss of vision", "muh tedha", "lakwa", "stroke"],
        "severity": "CRITICAL",
        "emergency_advice": "Time is critical for acute stroke. Every minute matters. Call 112 / 108 immediately for the nearest stroke-ready hospital."
    },
    {
        "category": "Severe Respiratory Distress",
        "keywords": ["cannot breathe", "gasping for air", "severe shortness of breath", "blue lips", "choking", "saans lene me takleef", "dam ghutna"],
        "severity": "CRITICAL",
        "emergency_advice": "Critical hypoxia risk. Call 112 / 108 immediately. Keep patient sitting upright with open airways."
    },
    {
        "category": "Severe Hemorrhage or Shock",
        "keywords": ["coughing blood", "vomiting blood", "heavy bleeding", "unconscious", "khoon ki ulti", "behosh"],
        "severity": "CRITICAL",
        "emergency_advice": "Potential internal bleeding or shock. Call 112 / 108 immediately and elevate legs if patient feels faint."
    },
    {
        "category": "Acute Poisoning / Anaphylaxis",
        "keywords": ["swallowed poison", "snake bite", "bee sting swelling throat", "poisoning", "zeher", "saap ka katna"],
        "severity": "CRITICAL",
        "emergency_advice": "Acute medical toxicology emergency. Call 112 / 108 immediately. Note the time and substance if safe to do so."
    }
]

def evaluate_triage(symptoms_text: str, chief_complaint: str = "", severity_level: int = 1) -> dict:
    """
    Evaluates symptoms against clinical rule-based red-flag triage criteria.
    Mandated by AyurLLM Section B: Red-flag triage rule-based check before any result.
    Emergency hotline: 112 / 108.
    """
    combined_text = f"{symptoms_text} {chief_complaint}".lower()
    
    matched_flags = []
    for pattern in RED_FLAG_PATTERNS:
        for kw in pattern["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', combined_text):
                matched_flags.append({
                    "category": pattern["category"],
                    "matched_term": kw,
                    "severity": pattern["severity"],
                    "advice": pattern["emergency_advice"]
                })
                break
                
    if matched_flags or severity_level >= 9:
        return {
            "is_red_flag": True,
            "status": "EMERGENCY_RED_FLAG",
            "emergency_numbers": ["112", "108"],
            "matched_reasons": matched_flags or [{"category": "Extreme Severity Rating", "matched_term": f"Severity {severity_level}/10", "advice": "Patient self-reported critical symptom severity."}],
            "action_required": "EMERGENCY_DISPATCH_CALL_112_OR_108",
            "clinical_disclaimer": "AyurLLM RAG results are halted for patient safety. Emergency allopathic care is mandatory for acute life-threatening presentations."
        }
        
    return {
        "is_red_flag": False,
        "status": "TRIAGE_CLEARED",
        "matched_reasons": [],
        "action_required": "PROCEED_TO_SHLOKA_INSIGHT_AND_DOCTOR_MATCH",
        "clinical_disclaimer": "Cleared for classical Ayurvedic lifestyle, diet assessment, and registered doctor consultation."
    }
