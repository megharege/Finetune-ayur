import React, { useState } from 'react';
import { 
  Search, 
  ArrowRight, 
  Sparkles, 
  ShieldCheck, 
  Stethoscope, 
  Video, 
  FileText, 
  BookOpen, 
  Award,
  AlertTriangle,
  ChevronRight,
  Leaf
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

interface HomePageProps {
  setActiveTab: (tab: string) => void;
  onSearchQuery: (query: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ setActiveTab, onSearchQuery }) => {
  const { t } = useLanguage();
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearchQuery(query.trim());
      setActiveTab('explorer');
    }
  };

  const stats = [
    { label: 'Classical Texts', value: '8', desc: 'Brihat & Laghu Trayi' },
    { label: 'Verified Chunks', value: '7,549', desc: 'MD5 0 collisions' },
    { label: 'Real Sanskrit', value: '95.8%', desc: 'Devanagari verified' },
    { label: 'Tokens Processed', value: '~5.2M', desc: 'Multilingual corpus' },
    { label: 'Chunk Collisions', value: '0', desc: 'Unique MD5 hash IDs' },
    { label: 'Vector Embedded', value: '18.3%', desc: 'e5-small (384-d)' },
  ];

  const workflowSteps = [
    { num: '01', title: 'Sign up + Consent', desc: 'Phone / Email OTP' },
    { num: '02', title: 'Intake Assessment', desc: 'Disease, Prakriti, Symptoms' },
    { num: '03', title: 'Red-Flag Triage', desc: 'Rule check (112/108 alert)', highlight: true },
    { num: '04', title: 'Hybrid Search', desc: 'Keyword + Semantic' },
    { num: '05', title: 'Shloka Insight', desc: 'Sanskrit, Hindi, Citations' },
    { num: '06', title: 'Doctor Match', desc: 'Bayesian Trust Score (0-100)' },
    { num: '07', title: 'Book & Pay', desc: 'Slots & Razorpay Checkout' },
    { num: '08', title: 'Video Teleconsult', desc: 'WebRTC, Notes, Neo4j Graph' },
    { num: '09', title: 'E-Prescription', desc: 'Herbs, Diet & Lifestyle Plan' },
    { num: '10', title: 'Follow-Up Care', desc: 'Reminders & Review' },
  ];

  const popularSearches = ['Triphala', 'Amlapitta', 'Ashwagandha', 'Jwara', 'Tikshnagni', 'Virechana'];

  return (
    <div className="space-y-16 pb-16">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-16 bg-gradient-to-b from-ayur-50/60 via-white to-parchment-50 border-b border-ayur-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            {/* Tag badge */}
            <div className="inline-flex items-center space-x-2 bg-ayur-100 border border-ayur-200 text-ayur-900 text-xs font-bold px-3.5 py-1.5 rounded-full shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-gold-600" />
              <span>AyurLLM Classical Medicine Platform & Hospital Network</span>
            </div>

            {/* Title */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-black text-ayur-950 tracking-tight leading-[1.15]">
              {t('hero.tagline')}
            </h1>

            {/* Subtitle */}
            <p className="text-base sm:text-lg text-slate-600 font-normal leading-relaxed">
              {t('hero.subtitle')}
            </p>

            {/* Main Search Bar */}
            <form onSubmit={handleSearch} className="relative max-w-2xl mx-auto shadow-xl rounded-2xl overflow-hidden border-2 border-ayur-300 focus-within:border-ayur-600 transition bg-white">
              <div className="flex items-center pl-4 pr-2 py-2">
                <Search className="w-5 h-5 text-slate-400 mr-2" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('hero.search_placeholder')}
                  className="w-full text-slate-900 placeholder:text-slate-400 text-sm sm:text-base outline-none bg-transparent"
                />
                <button
                  type="submit"
                  className="bg-ayur-800 hover:bg-ayur-900 text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center space-x-1.5 transition shrink-0 shadow-xs"
                >
                  <span>Search</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>

            {/* Popular quick tags */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs">
              <span className="text-slate-500 font-medium">Quick Classical Query:</span>
              {popularSearches.map((term) => (
                <button
                  key={term}
                  onClick={() => {
                    onSearchQuery(term);
                    setActiveTab('explorer');
                  }}
                  className="px-2.5 py-1 rounded-full bg-white hover:bg-ayur-50 border border-slate-200 text-ayur-900 font-semibold transition"
                >
                  {term}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Real Corpus Statistics */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-2xl border border-ayur-200 p-8 shadow-xs">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Ayurvedic Manuscript Corpus Benchmarks</h3>
              <p className="text-xs text-slate-500">Documented metrics across 7 scanned volumes and 8 classical treatise parsers</p>
            </div>
            <span className="text-xs font-bold text-ayur-700 bg-ayur-50 px-3 py-1 rounded-full border border-ayur-200">
              Corpus Status: 100% Ingested
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {stats.map((s, idx) => (
              <div key={idx} className="bg-parchment-50/70 p-4 rounded-xl border border-parchment-200 text-center">
                <span className="block text-2xl lg:text-3xl font-black text-ayur-900 font-display">{s.value}</span>
                <span className="block text-xs font-bold text-slate-800 mt-1">{s.label}</span>
                <span className="block text-[10px] text-slate-500 mt-0.5">{s.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 10-Step Interactive Workflow */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10 space-y-2">
          <div className="inline-flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-ayur-700">
            <Leaf className="w-3.5 h-3.5" />
            <span>End-to-End Hospital Architecture</span>
          </div>
          <h2 className="text-3xl font-display font-bold text-slate-900">
            Patient-to-Doctor Clinical Lifecycle
          </h2>
          <p className="text-sm text-slate-600">
            Backed by rule-based red-flag triage, hybrid search RAG, Bayesian doctor trust scoring, and Neo4j telemetry.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          {workflowSteps.map((step, idx) => (
            <div 
              key={idx}
              className={`p-4 rounded-xl border transition-all text-left relative overflow-hidden group hover:shadow-md ${
                step.highlight 
                  ? 'bg-rose-50/80 border-rose-300' 
                  : 'bg-white border-slate-200 hover:border-ayur-400'
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <span className={`text-xs font-black font-mono ${step.highlight ? 'text-rose-600' : 'text-ayur-700'}`}>
                  STEP {step.num}
                </span>
                {step.highlight && (
                  <span className="text-[10px] bg-red-600 text-white font-bold px-1.5 py-0.5 rounded">
                    112 / 108
                  </span>
                )}
              </div>
              <h4 className="text-sm font-bold text-slate-900 group-hover:text-ayur-800 transition">
                {step.title}
              </h4>
              <p className="text-xs text-slate-500 mt-1">
                {step.desc}
              </p>
            </div>
          ))}
        </div>

        {/* CTA Banner */}
        <div className="mt-8 bg-gradient-to-r from-ayur-900 via-ayur-800 to-ayur-950 rounded-2xl p-6 sm:p-8 text-white flex flex-col md:flex-row items-center justify-between shadow-lg gap-6">
          <div className="space-y-1 text-center md:text-left">
            <h3 className="text-xl font-bold font-display">Begin Clinical Prakriti & Symptom Intake</h3>
            <p className="text-xs text-ayur-200">Complete 5-minute Ayurvedic assessment and discover matched classical shlokas & verified Vaidyas.</p>
          </div>
          <button
            onClick={() => setActiveTab('intake')}
            className="bg-gold-500 hover:bg-gold-400 text-slate-950 px-6 py-3 rounded-xl font-bold text-sm shadow-md transition flex items-center space-x-2 shrink-0"
          >
            <span>Start Intake & Triage</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Classical Treatise Overview */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="border-t border-slate-200 pt-10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-bold font-display text-slate-900">Classical Ayurvedic Literature at a Glance</h3>
              <p className="text-xs text-slate-500">Chunk distribution and primary categories across the Brihat & Laghu Trayi</p>
            </div>
            <button
              onClick={() => setActiveTab('explorer')}
              className="text-xs font-bold text-ayur-700 hover:text-ayur-900 flex items-center space-x-1"
            >
              <span>Explore All Shlokas</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { name: 'Sharangadhara Samhita', chunks: '1,972 chunks', category: 'dravya_guna', desc: 'Highest chunk volume; polyherbal compounding and pharmaceutical calcination.' },
              { name: 'Bhavaprakasha (V1 & V2)', chunks: '3,010 chunks', category: 'pharmacology & properties', desc: 'Nighantu botanical monographs and therapeutic qualities of native herbs.' },
              { name: 'Charaka Samhita', chunks: '1,558 chunks', category: 'pharmacology & internal medicine', desc: 'The bedrock of Kayachikitsa, Tridosha physiology, and longevity rasayanas.' },
              { name: 'Madhava Nidana & Nam', chunks: '643 chunks', category: 'dosha & clinical diagnosis', desc: 'Pancha Nidana diagnostic pillars, disease staging, and prognosis.' },
            ].map((book, i) => (
              <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 hover:border-ayur-300 transition space-y-2">
                <span className="text-[10px] uppercase font-bold tracking-widest text-ayur-700 bg-ayur-50 px-2 py-0.5 rounded border border-ayur-200">
                  {book.category}
                </span>
                <h4 className="font-bold text-slate-900 text-sm mt-1">{book.name}</h4>
                <p className="text-xs font-semibold text-gold-700 font-mono">{book.chunks}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{book.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};
