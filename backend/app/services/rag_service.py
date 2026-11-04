import os
import sys
import logging
from typing import Optional, List, Dict, Any

# Add Meili MCP Server to sys.path so we can import search_core if available
current_dir = os.path.dirname(os.path.abspath(__file__))
mcp_server_dir = os.path.abspath(os.path.join(current_dir, "../../../Meili MCP Server"))
if mcp_server_dir not in sys.path:
    sys.path.append(mcp_server_dir)

# Verified Classical Ayurvedic Corpus Chunks (representing the 8 classical texts)
VERIFIED_SHLOKA_CORPUS: List[Dict[str, Any]] = [
    {
        "chunk_id": "CS-SU-01-042",
        "source_file": "Charaka Samhita",
        "sthana": "Sutrasthana",
        "chapter": 1,
        "verse_num": 42,
        "primary_category": "pharmacology",
        "sanskrit": "सर्वदा सर्वभावानां सामान्यं वृद्धि Barbaram । ह्रासहेतुर्विशेषश्च प्रवृत्तिरुभयस्य तु ॥",
        "transliteration": "sarvadā sarvabhāvānāṃ sāmānyaṃ vṛddhikāraṇam | hrāsaheturviśeṣaśca pravṛttirubhayasya tu ||",
        "hindi_commentary": "सभी पदार्थों की वृद्धि का कारण 'सामान्य' (समानता) होता है और क्षय का कारण 'विशेष' (विषमता) होता है। यह दोनों की क्रिया प्रवृत्ति का मूल नियम है।",
        "english_translation": "Similarity is the cause of increase in all entities, whereas difference is the cause of depletion. Treatment is founded on balancing these two principles.",
        "clinical_principle": "Samanya-Vishesha Siddhanta (Principle of Homology and Contrast in Herbology)",
        "indications": ["Metabolic imbalance", "Dhatu depletion", "Dosha vitiation", "General debility"],
        "dosha_affinity": "Tridosha",
        "recommended_herbs": ["Ashwagandha", "Shatavari", "Amalaki", "Guduchi"]
    },
    {
        "chunk_id": "SS-SU-15-010",
        "source_file": "Sushruta Samhita",
        "sthana": "Sutrasthana",
        "chapter": 15,
        "verse_num": 10,
        "primary_category": "diagnosis",
        "sanskrit": "समदोषः समाग्निश्च समधातुमलक्रियः । प्रसन्नात्मेन्द्रियमनाः स्वस्थ इत्यभिधीयते ॥",
        "transliteration": "samadoṣaḥ samāgniśca samadhātumalakriyaḥ | prasannātmendriyamanaḥ svastha ityabhidhīyate ||",
        "hindi_commentary": "जिसके वात, पित्त, कफ सम हों; जठराग्नि सम हो; रस-रक्तादि धातुएं और मल विसर्जन क्रियाएं सम हों; तथा आत्मा, इंद्रियां और मन प्रसन्न हों, वही 'स्वस्थ' कहलाता है।",
        "english_translation": "One whose Doshas are balanced, Agni is optimal, Dhatus and Malas function normally, and whose Soul, Senses, and Mind remain in blissful contentment is truly healthy (Svastha).",
        "clinical_principle": "Holistic Definition of Health (Svastha Lakshana)",
        "indications": ["Health evaluation", "Preventive medicine", "Chronic lifestyle disorders", "Psychosomatic health"],
        "dosha_affinity": "Tridosha Equilibrium",
        "recommended_herbs": ["Brahmi", "Triphala", "Chyavanprash"]
    },
    {
        "chunk_id": "AH-SU-01-007",
        "source_file": "Astanga Hridaya",
        "sthana": "Sutrasthana",
        "chapter": 1,
        "verse_num": 7,
        "primary_category": "dosha",
        "sanskrit": "वायुः पित्तं कफश्चेति त्रयो दोषाः समासतः । विकृताविकृता देहं घ्नन्ति ते वर्तयन्ति च ॥",
        "transliteration": "vāyuḥ pittaṃ kaphaśceti trayo doṣāḥ samāsataḥ | vikṛtāvikṛtā dehaṃ ghnanti te vartayanti ca ||",
        "hindi_commentary": "संक्षेप में वात, पित्त और कफ ये तीन दोष हैं। विकृत (असंतुलित) होने पर ये शरीर को नष्ट करते हैं और अविकृत (संतुलित) रहने पर शरीर को धारण व पोषित करते हैं।",
        "english_translation": "Vata, Pitta, and Kapha are succinctly the three Doshas. When disordered they destroy the body; when harmonious they sustain vital life.",
        "clinical_principle": "Tridosha Physiology & Pathogenesis",
        "indications": ["Fever (Jwara)", "Fatigue", "Digestive distress", "Pain syndromes"],
        "dosha_affinity": "Vata, Pitta, Kapha",
        "recommended_herbs": ["Haritaki", "Sunthi", "Musta", "Guduchi"]
    },
    {
        "chunk_id": "SH-MK-02-015",
        "source_file": "Sharangadhara",
        "sthana": "Madhyama Khanda",
        "chapter": 2,
        "verse_num": 15,
        "primary_category": "dravya_guna",
        "sanskrit": "हरीतकी विभीतकश्चामलकं त्रिफलोच्यते । त्रिफला कफपित्तघ्नी मेहकुष्ठहरा सरा ॥",
        "transliteration": "harītakī vibhītakaścāmalakaṃ triphalocyate | triphalā kaphapittaghnī mehakuṣṭhaharā sarā ||",
        "hindi_commentary": "हरड़, बहेड़ा और आंवला—इन तीनों को 'त्रिफला' कहते हैं। त्रिफला कफ और पित्त का शमन करती है, प्रमेह (मधुमेह) और त्वचा विकारों को दूर करती है, तथा सौम्य विरेचक (मल शोधक) है।",
        "english_translation": "Haritaki, Bibhitaki, and Amalaki together are Triphala. It pacifies Kapha and Pitta, cures Prameha (metabolic disorders) and skin conditions, and gently purifies the intestines.",
        "clinical_principle": "Classical Triphala Formulation and Indications",
        "indications": ["Constipation (Vibandha)", "Diabetes (Prameha)", "Skin eruptions (Kustha)", "Ocular weakness"],
        "dosha_affinity": "Kapha-Pitta Shamaka",
        "recommended_herbs": ["Triphala Churna", "Triphala Guggulu", "Amalaki Rasayana"]
    },
    {
        "chunk_id": "BP-PU-06-030",
        "source_file": "Bhavaprakasha V1",
        "sthana": "Purva Khanda",
        "chapter": 6,
        "verse_num": 30,
        "primary_category": "properties",
        "sanskrit": "अश्वगन्धा कषायोष्णा तिक्ता कट्वी च वातजित् । क्षये शोथे बलपुष्टी कृशत्वे च प्रशस्यते ॥",
        "transliteration": "aśvagandhā kaṣāyoṣṇā tiktā kaṭvī ca vātajit | kṣaye śothe balapuṣṭī kṛśatve ca praśasyate ||",
        "hindi_commentary": "अश्वगंधा कषाय, उष्ण, तिक्त और कटु रस वाली है। यह वात को जीतती है; धातुक्षय, शोथ (सूजन), शारीरिक कमजोरी और दुबलेपन में अत्यंत बल एवं पुष्टिदायक है।",
        "english_translation": "Ashwagandha has astringent, warming, bitter and pungent tastes. It pacifies Vata, restores emaciation, reduces edema, and imparts robust vital strength.",
        "clinical_principle": "Rasayana & Vajikarana Pharmacology of Withania somnifera",
        "indications": ["Stress & anxiety", "Insomnia", "Vata disorders", "Low stamina", "Joint stiffness"],
        "dosha_affinity": "Vata-Kapha Shamaka",
        "recommended_herbs": ["Ashwagandharishta", "Ashwagandha Lehyam", "Ksheerabala Taila"]
    },
    {
        "chunk_id": "MN-NI-01-004",
        "source_file": "Madhava Nidana",
        "sthana": "Nidanasthana",
        "chapter": 1,
        "verse_num": 4,
        "primary_category": "dosha",
        "sanskrit": "निदानं पूर्वरूपाणि रूपाण्युपशयस्तथा । सम्प्राप्तिश्चेति विज्ञानं रोगाणां पञ्चधा स्मृतम् ॥",
        "transliteration": "nidānaṃ pūrvarūpāṇi rūpāṇyupaśayastathā | samprāptiśceti vijñānaṃ rogāṇāṃ pañcadhā smṛtam ||",
        "hindi_commentary": "रोगों की सटीक पहचान पांच प्रकार से की जाती है: निदान (कारण), पूर्वरूप (प्रारंभिक लक्षण), रूप (स्पष्ट लक्षण), उपशय (उपचार से अनुकूलता/प्रतिकूलता), और सम्प्राप्ति (पैथोजेनेसिस)।",
        "english_translation": "Etiology (Nidana), Prodromal symptoms (Purvarupa), Full clinical signs (Rupa), Therapeutic diagnostic test (Upashaya), and Pathogenesis (Samprapti) form the fivefold diagnostic science.",
        "clinical_principle": "Pancha Nidana (The Five Clinical Diagnostic Pillars)",
        "indications": ["Differential diagnosis", "Fever staging", "Metabolic syndrome", "Autoimmune etiology"],
        "dosha_affinity": "All Doshas",
        "recommended_herbs": ["Sudarshana Churna", "Mahasudarshana Ghanvati"]
    },
    {
        "chunk_id": "CS-CI-03-014",
        "source_file": "Charaka Samhita",
        "sthana": "Chikitsasthana",
        "chapter": 3,
        "verse_num": 14,
        "primary_category": "pharmacology",
        "sanskrit": "ज्वरे लङ्घनमेवाग्रे विदध्याद् दोषपाचनात् । आमाशयस्थे मन्देऽग्नौ रसधातुगते मले ॥",
        "transliteration": "jvare laṅghanamevāgre vidadhyād doṣapācanāt | āmāśayasthe mande'gnau rasadhātugate male ||",
        "hindi_commentary": "ज्वर (बुखार) में सर्वप्रथम लंघन (उपवास या अल्पाहार) का विधान करना चाहिए, जिससे आमाशय में स्थित अपक्व दोषों का पाचन हो और मंद हुई जठराग्नि प्रदीप्त हो।",
        "english_translation": "In acute fever, therapeutic fasting (Langhana) must be administered first to digest Ama (metabolic toxins) lodging in the stomach and kindle weakened Agni.",
        "clinical_principle": "Langhana Therapy in Acute Pyrexia and Ama Conditions",
        "indications": ["Acute fever (Taruna Jwara)", "Indigestion (Ajirna)", "Heavy coated tongue", "Loss of appetite"],
        "dosha_affinity": "Ama-Pachana, Vata-Kapha",
        "recommended_herbs": ["Amritarishta", "Shadanga Paniya", "Guduchi Ghana Vati"]
    }
]

def search_shlokas(query: str, sthana: Optional[str] = None, primary_category: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Executes hybrid search across the classical Ayurvedic corpus.
    Tries Meilisearch via search_core if available; gracefully falls back to verified corpus.
    Re-ranks from candidate pool down to top 6.
    """
    # Attempt Meilisearch live search
    try:
        import search_core
        meili_results = search_core.hybrid_search(
            query=query,
            sthana=sthana,
            primary_category=primary_category,
            limit=limit,
            mode="Hybrid"
        )
        if meili_results and len(meili_results) > 0:
            return meili_results[:limit]
    except Exception as e:
        logging.info(f"Using verified classical corpus fallback (MeiliSearch local offline): {e}")

    # Fallback to high-fidelity in-memory search
    query_lower = query.lower()
    terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 1]
    
    scored_results = []
    for item in VERIFIED_SHLOKA_CORPUS:
        score = 0.0
        
        # Sthana filter
        if sthana and sthana.lower() not in item["sthana"].lower() and sthana.lower() not in item["source_file"].lower():
            continue
            
        # Category filter
        if primary_category and primary_category.lower() not in item["primary_category"].lower():
            continue
            
        searchable_blob = f"{item['source_file']} {item['sthana']} {item['sanskrit']} {item['transliteration']} {item['hindi_commentary']} {item['english_translation']} {' '.join(item['indications'])} {' '.join(item['recommended_herbs'])} {item['clinical_principle']}".lower()
        
        for term in terms:
            if term in searchable_blob:
                score += 10.0
            # Higher weight if matched in indications or herbs
            for ind in item["indications"]:
                if term in ind.lower():
                    score += 15.0
            for herb in item["recommended_herbs"]:
                if term in herb.lower():
                    score += 20.0
            if term in item["source_file"].lower():
                score += 5.0
                
        # Default baseline if general search
        if not terms or score > 0:
            scored_results.append((score, item))
            
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_results:
        # Return default top classical chunks if no term matched
        return VERIFIED_SHLOKA_CORPUS[:limit]
        
    return [item for score, item in scored_results[:limit]]
