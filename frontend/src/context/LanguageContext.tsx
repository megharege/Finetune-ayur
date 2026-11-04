import React, { createContext, useContext, useState, ReactNode } from 'react';

type Language = 'en' | 'hi';

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (key: string) => string;
}

const translations: Record<string, Record<Language, string>> = {
  // Navigation
  'nav.home': { en: 'Home', hi: 'मुख्य पृष्ठ' },
  'nav.explorer': { en: 'AyurLLM Explorer', hi: 'श्लोक अनुसंधान' },
  'nav.intake': { en: 'Prakriti & Intake', hi: 'प्रकृति व निदान' },
  'nav.doctors': { en: 'Find Doctors', hi: 'वैद्य खोजें' },
  'nav.consult': { en: 'Teleconsultation', hi: 'वीडियो परामर्श' },
  'nav.hospital': { en: 'Hospital ERP', hi: 'चिकित्सालय प्रबंधन' },
  'nav.portal': { en: 'Patient EHR', hi: 'रोगी स्वास्थ्य अभिलेख' },
  'nav.emergency': { en: 'Emergency 112/108', hi: 'आपातकालीन 112/108' },
  
  // Hero & General
  'hero.tagline': { en: 'From Classical Manuscript to Machine-Searchable Medicine', hi: 'प्राचीन पांडुलिपि से आधुनिक डिजिटल चिकित्सा तक' },
  'hero.subtitle': { en: 'Verified clinical intelligence across 8 classical Ayurvedic texts backed by RAG, hybrid search, and Bayesian doctor verification.', hi: '८ शास्त्रीय संहिताओं पर आधारित प्रमाणित श्लोक खोज एवं बायेसियन वैद्य विश्वसनीयता प्रणाली।' },
  'hero.search_placeholder': { en: 'Search classical texts (e.g., Triphala, Jwara, Agni, Insomnia)...', hi: 'शास्त्रीय श्लोक खोजें (जैसे: त्रिफला, ज्वर, अग्नि, अनिद्रा)...' },
  'hero.explore_btn': { en: 'Explore Shlokas', hi: 'श्लोक देखें' },
  'hero.consult_btn': { en: 'Consult a Verified Vaidya', hi: 'प्रमाणित वैद्य से परामर्श लें' },
  
  // Triage & Emergency
  'triage.alert_title': { en: 'Clinical Safety Protocol (Red-Flag Triage)', hi: 'चिकित्सीय सुरक्षा नियम (रेड-फ्लैग ट्राइएज)' },
  'triage.emergency_msg': { en: 'Immediate Allopathic Emergency Care Required', hi: 'तत्काल आपातकालीन चिकित्सा देखभाल आवश्यक है' },
  'triage.call_action': { en: 'Call National Emergency 112 or Ambulance 108 immediately', hi: 'तुरंत राष्ट्रीय आपातकाल 112 या एम्बुलेंस 108 पर कॉल करें' },
  
  // RAG & Shloka
  'shloka.title': { en: 'Classical Ayurvedic RAG Corpus', hi: 'शास्त्रीय आयुर्वेद श्लोक कोष' },
  'shloka.sanskrit': { en: 'Original Sanskrit Verse', hi: 'मूल संस्कृत श्लोक' },
  'shloka.transliteration': { en: 'IAST Transliteration', hi: 'रोमन लिपि (IAST)' },
  'shloka.hindi_commentary': { en: 'Hindi Commentary (Gemini 2.5 Pro)', hi: 'हिन्दी टीका (जेमिनी २.५ प्रो)' },
  'shloka.english_meaning': { en: 'English Translation & Principle', hi: 'अंग्रेज़ी अनुवाद एवं सिद्धांत' },
  'shloka.indications': { en: 'Therapeutic Indications', hi: 'रोगोपयोग व फलश्रुति' },
  'shloka.chunk_id': { en: 'Source Chunk Citation', hi: 'संहिता संदर्भ (चंक आईडी)' },
  
  // Doctors & Trust Score
  'doctor.directory': { en: 'Verified Vaidya Network', hi: 'प्रमाणित वैद्य नेटवर्क' },
  'doctor.trust_score': { en: 'Bayesian Trust Score', hi: 'बायेसियन विश्वसनीयता स्कोर' },
  'doctor.verified_badge': { en: 'Verified Council Registry', hi: 'प्रमाणित परिषद पंजीयन' },
  'doctor.unverified_seed': { en: 'Kaggle Dataset (Unverified Seed)', hi: 'कैगल डेटासेट (अपुष्ट प्रविष्टि)' },
  'doctor.book_consult': { en: 'Book Consultation (Razorpay)', hi: 'परामर्श बुक करें (रेज़रपे)' },
  'doctor.view_trust_math': { en: 'View Trust Formula Breakdown', hi: 'स्कोर गणना सूत्र देखें' },

  // Hospital Modules
  'hospital.pharmacy': { en: 'Herbal Pharmacy & Stock', hi: 'औषधालय एवं स्टॉक' },
  'hospital.panchakarma': { en: 'Panchakarma Detox Booking', hi: 'पंचकर्म चिकित्सा बुकिंग' },
  'hospital.analytics': { en: 'Hospital Clinical Analytics', hi: 'चिकित्सालय विश्लेषण' },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [lang, setLang] = useState<Language>('en');

  const toggleLang = () => {
    setLang(prev => (prev === 'en' ? 'hi' : 'en'));
  };

  const t = (key: string): string => {
    if (translations[key] && translations[key][lang]) {
      return translations[key][lang];
    }
    return key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
