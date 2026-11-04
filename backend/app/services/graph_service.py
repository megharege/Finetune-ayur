import logging
from typing import Dict, Any, List
from app.core.config import settings

def build_patient_graph(
    patient_id: int,
    patient_name: str,
    prakriti: str,
    symptoms: List[str],
    dosha_imbalance: str,
    shlokas_cited: List[Dict[str, Any]],
    doctor_name: str = "Dr. Vaidya Hitanshu",
    consultation_id: int = 1
) -> Dict[str, Any]:
    """
    Constructs the patient knowledge graph schema as specified in AyurLLM Section B:
    Patient - Symptom - Disease - Dosha - Shloka - Book | Patient - Consultation - Doctor
    Restricted to certified doctors during active consults.
    """
    nodes = []
    links = []
    
    # 1. Patient Node
    p_node_id = f"patient_{patient_id}"
    nodes.append({
        "id": p_node_id,
        "label": patient_name,
        "type": "Patient",
        "color": "#1b5e4b",
        "radius": 24,
        "details": {"prakriti": prakriti, "patient_id": patient_id}
    })
    
    # 2. Consultation Node
    c_node_id = f"consult_{consultation_id}"
    nodes.append({
        "id": c_node_id,
        "label": f"Consultation #{consultation_id}",
        "type": "Consultation",
        "color": "#d97706",
        "radius": 18,
        "details": {"status": "ACTIVE_TELECONSULT"}
    })
    links.append({"source": p_node_id, "target": c_node_id, "relation": "HAD_CONSULTATION"})
    
    # 3. Doctor Node
    doc_node_id = f"doctor_{doctor_name.replace(' ', '_')}"
    nodes.append({
        "id": doc_node_id,
        "label": doctor_name,
        "type": "Doctor",
        "color": "#2563eb",
        "radius": 20,
        "details": {"status": "Verified Vaidya"}
    })
    links.append({"source": c_node_id, "target": doc_node_id, "relation": "CONDUCTED_BY"})
    
    # 4. Dosha Node
    dosha_node_id = f"dosha_{dosha_imbalance.replace(' ', '_')}"
    nodes.append({
        "id": dosha_node_id,
        "label": dosha_imbalance,
        "type": "Dosha",
        "color": "#dc2626",
        "radius": 20,
        "details": {"vitiation": "Prakopa"}
    })
    links.append({"source": p_node_id, "target": dosha_node_id, "relation": "HAS_IMBALANCE"})
    
    # 5. Symptom Nodes
    for i, sym in enumerate(symptoms):
        sym_node_id = f"sym_{i}_{sym.replace(' ', '_')}"
        nodes.append({
            "id": sym_node_id,
            "label": sym,
            "type": "Symptom",
            "color": "#9333ea",
            "radius": 16,
            "details": {"severity": "Moderate"}
        })
        links.append({"source": p_node_id, "target": sym_node_id, "relation": "EXHIBITS"})
        links.append({"source": sym_node_id, "target": dosha_node_id, "relation": "INDICATES_DOSHA"})
        
    # 6. Shloka & Book Nodes
    for i, shloka in enumerate(shlokas_cited):
        shloka_node_id = f"shloka_{shloka.get('chunk_id', i)}"
        nodes.append({
            "id": shloka_node_id,
            "label": f"Verse: {shloka.get('chunk_id', 'Chunk')}",
            "type": "Shloka",
            "color": "#059669",
            "radius": 16,
            "details": {
                "chunk_id": shloka.get("chunk_id"),
                "sanskrit": shloka.get("sanskrit"),
                "principle": shloka.get("clinical_principle")
            }
        })
        links.append({"source": dosha_node_id, "target": shloka_node_id, "relation": "TREATABLE_BY"})
        
        # Book Node
        book_name = shloka.get("source_file", "Charaka Samhita")
        book_node_id = f"book_{book_name.replace(' ', '_')}"
        if not any(n["id"] == book_node_id for n in nodes):
            nodes.append({
                "id": book_node_id,
                "label": book_name,
                "type": "Book",
                "color": "#b45309",
                "radius": 18,
                "details": {"classical_authority": "Brihat Trayi"}
            })
        links.append({"source": shloka_node_id, "target": book_node_id, "relation": "ORIGINATES_IN"})
        
    return {
        "nodes": nodes,
        "links": links,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(links),
            "root_patient": patient_name,
            "active_consult_doctor": doctor_name
        }
    }
