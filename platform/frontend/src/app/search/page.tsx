"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Search,
  BookOpen,
  Sparkles,
  ArrowRight,
  Copy,
  ExternalLink,
  BookMarked,
  ChevronRight,
  Loader2,
} from "lucide-react";

/* ─── Demo Shloka Results ─── */
const demoResults = [
  {
    id: "charaka_sutra_1_42",
    book: "Charaka Samhita",
    chapter: "Sutra Sthana",
    verse: "1.42",
    sanskrit:
      "रोगास्तु दोषवैषम्यं दोषसाम्यमरोगता। सारवत्तापरैर्दोषैः कर्तव्यं रक्षणं बलात्।।",
    translation:
      "Diseases arise from the imbalance of doshas; health is the equilibrium of doshas. One should protect this balance with strength through proper measures.",
    explanation:
      "This foundational verse establishes the central Ayurvedic principle: disease (Roga) is dosha imbalance, and health (Arogya) is dosha equilibrium. Treatment aims to restore this balance.",
    relevance: 0.96,
    tags: ["Dosha Balance", "Foundation", "Treatment Principle"],
  },
  {
    id: "sushruta_sutra_15_41",
    book: "Sushruta Samhita",
    chapter: "Sutra Sthana",
    verse: "15.41",
    sanskrit:
      "समदोषः समाग्निश्च समधातुमलक्रियः। प्रसन्नात्मेन्द्रियमनाः स्वस्थ इत्यभिधीयते।।",
    translation:
      "One whose doshas are balanced, whose Agni is balanced, whose Dhatus and Malas function properly, and whose Atma, Indriyas, and Manas are content — such a person is called Swastha (healthy).",
    explanation:
      "Sushruta's holistic definition of health encompasses not just physical balance but also mental and spiritual well-being — the true Swastha state.",
    relevance: 0.93,
    tags: ["Swastha", "Health Definition", "Holistic"],
  },
  {
    id: "ashtanga_hridaya_1_1",
    book: "Ashtanga Hridaya",
    chapter: "Sutra Sthana",
    verse: "1.1",
    sanskrit:
      "रागादिरोगान् सततानुषक्तान् अशेषकायप्रसृतानशेषान्। औत्सुक्यमोहारतिदान् जघान योऽपूर्ववैद्याय नमोऽस्तु तस्मै।।",
    translation:
      "Salutations to that unique physician who destroyed the diseases of the body — such as passion, delusion, and aversion — which are constantly attached and spread throughout the entire being.",
    explanation:
      "The opening verse of Ashtanga Hridaya draws a parallel between mental afflictions (Raga, Dvesha, Moha) and physical diseases, emphasizing that true healing addresses both dimensions.",
    relevance: 0.89,
    tags: ["Mental Health", "Opening Verse", "Philosophy"],
  },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(demoResults);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(true);

  const handleSearch = () => {
    if (!query.trim()) return;
    setIsSearching(true);
    // Simulate search delay
    setTimeout(() => {
      setIsSearching(false);
      setHasSearched(true);
      setResults(demoResults);
    }, 1500);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 pt-24 pb-16">
        <div className="container-app max-w-4xl">
          {/* Header */}
          <div className="text-center mb-10 space-y-3 animate-fade-in-up">
            <span className="badge badge-gold">
              <BookOpen className="w-3 h-3" />
              Hybrid Retrieval
            </span>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              Shloka <span className="gradient-text">Search</span>
            </h1>
            <p className="text-[var(--foreground-muted)] max-w-lg mx-auto text-sm">
              Query the 8-book verified Ayurvedic corpus. Hybrid keyword + semantic search
              with AI-grounded explanations.
            </p>
          </div>

          {/* Search Box */}
          <div className="card p-6 mb-8 animate-fade-in-up delay-100">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--foreground-dim)]" />
                <input
                  type="text"
                  className="input pl-11 text-base py-3.5"
                  placeholder="Search by symptom, disease, dosha, treatment, or Sanskrit term..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>
              <button
                onClick={handleSearch}
                className="btn btn-primary px-6"
                disabled={isSearching}
              >
                {isSearching ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Search
                  </>
                )}
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {["Joint Pain", "Vata Dosha", "Panchakarma", "Digestive Fire", "Rasayana"].map((tag) => (
                <button
                  key={tag}
                  onClick={() => { setQuery(tag); handleSearch(); }}
                  className="px-3 py-1 rounded-full text-xs bg-[var(--background-elevated)] border border-[var(--border)] text-[var(--foreground-muted)] hover:border-[var(--ayur-emerald)] hover:text-[var(--ayur-emerald-light)] transition-all cursor-pointer"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Loading State */}
          {isSearching && (
            <div className="space-y-4 animate-fade-in">
              {[1, 2, 3].map((i) => (
                <div key={i} className="card p-6 space-y-3">
                  <div className="skeleton h-4 w-1/3" />
                  <div className="skeleton h-3 w-full" />
                  <div className="skeleton h-3 w-4/5" />
                  <div className="skeleton h-3 w-2/3" />
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {!isSearching && hasSearched && (
            <div className="space-y-4 stagger-children">
              <div className="flex items-center justify-between text-sm mb-2">
                <p className="text-[var(--foreground-muted)]">
                  <span className="font-semibold text-[var(--foreground)]">{results.length}</span>{" "}
                  verses found
                </p>
                <span className="text-xs text-[var(--foreground-dim)]">
                  Ranked by relevance • Grounded citations
                </span>
              </div>

              {results.map((verse) => (
                <div key={verse.id} className="card p-6 space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--ayur-gold-dark)] to-[var(--ayur-gold)] flex items-center justify-center">
                        <BookMarked className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold">{verse.book}</h3>
                        <p className="text-xs text-[var(--foreground-dim)]">
                          {verse.chapter} • Verse {verse.verse}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="badge badge-emerald">
                        {Math.round(verse.relevance * 100)}% match
                      </span>
                      <button className="icon-btn" title="Copy citation">
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Sanskrit */}
                  <div className="p-4 rounded-lg bg-[var(--background-elevated)] border border-[var(--border)]">
                    <p className="text-base leading-relaxed font-medium text-[var(--ayur-gold-light)]" style={{ fontFamily: "serif" }}>
                      {verse.sanskrit}
                    </p>
                  </div>

                  {/* Translation */}
                  <div>
                    <h4 className="text-xs font-semibold text-[var(--foreground-dim)] uppercase tracking-wider mb-1.5">
                      Translation
                    </h4>
                    <p className="text-sm text-[var(--foreground)] leading-relaxed">
                      {verse.translation}
                    </p>
                  </div>

                  {/* AI Explanation */}
                  <div className="p-4 rounded-lg bg-[rgba(13,107,63,0.08)] border border-[rgba(13,107,63,0.2)]">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-[var(--ayur-emerald-light)]" />
                      <span className="text-xs font-semibold text-[var(--ayur-emerald-light)]">
                        AI-Grounded Explanation
                      </span>
                    </div>
                    <p className="text-sm text-[var(--foreground-muted)] leading-relaxed">
                      {verse.explanation}
                    </p>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-2">
                    {verse.tags.map((tag) => (
                      <span key={tag} className="badge badge-gold text-[0.65rem]">{tag}</span>
                    ))}
                  </div>

                  {/* Citation ID */}
                  <div className="flex items-center gap-2 text-xs text-[var(--foreground-dim)]">
                    <span className="font-mono bg-[var(--background-elevated)] px-2 py-0.5 rounded">
                      chunk_id: {verse.id}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
