from fastapi import APIRouter, Query
from typing import Optional
from app.services.rag_service import search_shlokas, VERIFIED_SHLOKA_CORPUS

router = APIRouter(prefix="/search", tags=["Classical Shloka RAG Search"])

@router.get("")
def search_corpus_get(
    q: str = Query(..., description="Ayurvedic symptom, disease, herb, or concept"),
    sthana: Optional[str] = Query(None, description="Filter by Sthana or Book"),
    category: Optional[str] = Query(None, description="Filter by primary category"),
    limit: int = Query(6, ge=1, le=30)
):
    """
    Step 4 & 5: Hybrid search (keyword + semantic, rerank top 30 to 6).
    Returns real Sanskrit verses, transliteration, Hindi commentary, and citations.
    """
    results = search_shlokas(query=q, sthana=sthana, primary_category=category, limit=limit)
    return {
        "query": q,
        "sthana_filter": sthana,
        "category_filter": category,
        "total_returned": len(results),
        "results": results
    }

@router.get("/all-shlokas")
def get_all_classical_shlokas():
    """Returns the verified classical shloka corpus across the 8 classical texts."""
    return {
        "total": len(VERIFIED_SHLOKA_CORPUS),
        "texts": list(set(s["source_file"] for s in VERIFIED_SHLOKA_CORPUS)),
        "categories": list(set(s["primary_category"] for s in VERIFIED_SHLOKA_CORPUS)),
        "shlokas": VERIFIED_SHLOKA_CORPUS
    }
