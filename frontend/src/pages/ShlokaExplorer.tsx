import React, { useState, useEffect } from 'react';
import { 
  Search, 
  BookOpen, 
  Filter, 
  Copy, 
  Check, 
  Sparkles, 
  Share2, 
  BookMarked,
  Layers,
  ChevronDown
} from 'lucide-react';
import { searchShlokas, getAllShlokas } from '../api/client';
import { ShlokaChunk } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface ShlokaExplorerProps {
  initialQuery?: string;
}

export const ShlokaExplorer: React.FC<ShlokaExplorerProps> = ({ initialQuery = '' }) => {
  const { t } = useLanguage();
  const [query, setQuery] = useState(initialQuery || 'Triphala');
  const [selectedBook, setSelectedBook] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [results, setResults] = useState<ShlokaChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const books = [
    'all',
    'Charaka Samhita',
    'Sushruta Samhita',
    'Astanga Hridaya',
    'Sharangadhara',
    'Bhavaprakasha V1',
    'Madhava Nidana'
  ];

  const categories = [
    'all',
    'pharmacology',
    'diagnosis',
    'dosha',
    'dravya_guna',
    'properties'
  ];

  const fetchResults = async () => {
    setLoading(true);
    try {
      const sthanaParam = selectedBook === 'all' ? undefined : selectedBook;
      const catParam = selectedCategory === 'all' ? undefined : selectedCategory;
      const res = await searchShlokas(query, sthanaParam, catParam, 8);
      if (res && res.results) {
        setResults(res.results);
      } else if (Array.isArray(res)) {
        setResults(res);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [selectedBook, selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchResults();
  };

  const copyChunk = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto space-y-2">
        <span className="text-xs uppercase tracking-widest font-bold text-ayur-700 bg-ayur-50 px-3 py-1 rounded-full border border-ayur-200">
          Step 4 & 5: Hybrid Search & Shloka Insights
        </span>
        <h1 className="text-3xl sm:text-4xl font-display font-bold text-slate-900">
          Classical Treatise Shloka RAG Engine
        </h1>
        <p className="text-xs sm:text-sm text-slate-600">
          Verified doctor-facing semantic retrieval over 7,549 verified Sanskrit chunks from Brihat & Laghu Trayi. Every insight cites its verifiable MD5 chunk source.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by symptom, concept, herb (e.g. Triphala, Jwara, Svastha, Langhana, Withania)..."
              className="w-full text-sm pl-11 pr-4 py-3 rounded-xl border border-slate-200 focus:border-ayur-500 focus:ring-1 focus:ring-ayur-500 outline-none"
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-ayur-800 hover:bg-ayur-900 text-white text-sm font-semibold rounded-xl transition shadow-xs flex items-center space-x-1.5 shrink-0"
          >
            <Sparkles className="w-4 h-4 text-gold-300" />
            <span>Hybrid Search</span>
          </button>
        </form>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs border-t border-slate-100">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1">
              <BookMarked className="w-3.5 h-3.5" />
              <span>Treatise:</span>
            </span>
            {books.map((b) => (
              <button
                key={b}
                onClick={() => setSelectedBook(b)}
                className={`px-2.5 py-1 rounded-lg font-medium transition capitalize ${
                  selectedBook === b
                    ? 'bg-ayur-800 text-white font-bold'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                {b}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1">
              <Layers className="w-3.5 h-3.5" />
              <span>Category:</span>
            </span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 font-medium outline-none"
            >
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results Grid */}
      <div className="space-y-6">
        <div className="flex justify-between items-center text-xs text-slate-500">
          <span>Found {results.length} classical verse records with verified Sanskrit & commentary</span>
          <span className="font-mono text-[11px]">Re-ranking: Hybrid BM25 + e5-small (384-d)</span>
        </div>

        {loading ? (
          <div className="py-20 text-center text-slate-400">
            <Sparkles className="w-8 h-8 mx-auto animate-spin text-ayur-600 mb-2" />
            <p className="text-sm font-medium">Re-ranking classical chunks from Brihat Trayi...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {results.map((chunk) => (
              <div
                key={chunk.chunk_id}
                className="bg-white rounded-2xl border border-slate-200/90 hover:border-ayur-400 shadow-xs hover:shadow-md transition flex flex-col justify-between overflow-hidden group"
              >
                {/* Card Top Meta */}
                <div className="px-5 py-3.5 bg-gradient-to-r from-parchment-50 to-white border-b border-parchment-200 flex justify-between items-center text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-ayur-950 font-serif">{chunk.source_file}</span>
                    <span className="text-slate-400">•</span>
                    <span className="text-slate-600">{chunk.sthana} (Ch. {chunk.chapter})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] bg-ayur-50 text-ayur-800 border border-ayur-200 px-2 py-0.5 rounded font-bold">
                      {chunk.chunk_id}
                    </span>
                    <button
                      onClick={() => copyChunk(`${chunk.sanskrit}\n${chunk.english_translation}`, chunk.chunk_id)}
                      className="text-slate-400 hover:text-slate-600 p-1 rounded transition"
                      title="Copy Shloka & Translation"
                    >
                      {copiedId === chunk.chunk_id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-5 space-y-4 flex-1">
                  {/* Sanskrit Verse in Devanagari */}
                  <div className="bg-amber-50/40 p-4 rounded-xl border border-amber-200/50">
                    <p className="sanskrit-verse text-base sm:text-lg text-slate-900 font-medium leading-loose text-center">
                      {chunk.sanskrit}
                    </p>
                  </div>

                  {/* Transliteration */}
                  <div className="text-xs text-slate-500 italic font-serif">
                    {chunk.transliteration}
                  </div>

                  {/* English Translation & Clinical Principle */}
                  <div className="space-y-1.5 text-xs">
                    <p className="font-semibold text-slate-900 leading-relaxed">
                      {chunk.english_translation}
                    </p>
                    <div className="text-ayur-800 font-medium text-[11px] bg-ayur-50 p-2 rounded-lg border border-ayur-100 flex items-start space-x-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-ayur-600 shrink-0 mt-0.5" />
                      <span><strong>Clinical Principle:</strong> {chunk.clinical_principle}</span>
                    </div>
                  </div>

                  {/* Hindi Commentary from Gemini 2.5 Pro */}
                  {chunk.hindi_commentary && (
                    <div className="border-t border-slate-100 pt-3 text-xs text-slate-700">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        हिन्दी व्याख्या (टीका)
                      </span>
                      <p className="font-sanskrit text-slate-800 leading-relaxed">
                        {chunk.hindi_commentary}
                      </p>
                    </div>
                  )}

                  {/* Indications & Recommended Herbs */}
                  <div className="border-t border-slate-100 pt-3 space-y-2">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Therapeutic Indications
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {chunk.indications.map((ind, i) => (
                          <span key={i} className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
                            {ind}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Classical Herb Formulations
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {chunk.recommended_herbs.map((herb, i) => (
                          <span key={i} className="text-[11px] bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded font-semibold">
                            {herb}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Footer */}
                <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-[11px]">
                  <span className="text-slate-500 font-medium">
                    Dosha Affinity: <strong className="text-slate-800">{chunk.dosha_affinity}</strong>
                  </span>
                  <span className="text-[10px] uppercase font-bold text-ayur-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {chunk.primary_category}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
