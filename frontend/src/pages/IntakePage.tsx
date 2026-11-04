import React, { useState, useEffect } from 'react';
import { 
  Stethoscope, 
  Sparkles, 
  ShieldAlert, 
  CheckCircle2, 
  ArrowRight, 
  UserCheck, 
  BookOpen, 
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { getPrakritiQuiz, submitIntake } from '../api/client';
import { TriageResult, ShlokaChunk, Doctor } from '../types';
import { EmergencyModal } from '../components/triage/EmergencyModal';

interface IntakePageProps {
  setActiveTab: (tab: string) => void;
  onSelectDoctor: (doctor: Doctor) => void;
}

export const IntakePage: React.FC<IntakePageProps> = ({ setActiveTab, onSelectDoctor }) => {
  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [prakritiAnswers, setPrakritiAnswers] = useState<Record<number, string>>({});
  
  // Clinical inputs
  const [chiefComplaint, setChiefComplaint] = useState('Severe hyperacidity with sour belching and disrupted sleep');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>(['Acid reflux', 'Heartburn', 'Insomnia']);
  const [newSymptom, setNewSymptom] = useState('');
  const [severity, setSeverity] = useState<number>(4);
  const [durationDays, setDurationDays] = useState<number>(14);
  const [currentMeds, setCurrentMeds] = useState('');
  
  // Results
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{
    triage: TriageResult;
    prakriti: any;
    shlokas: ShlokaChunk[];
    matched_doctors: Doctor[];
  } | null>(null);
  
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);

  useEffect(() => {
    getPrakritiQuiz()
      .then((data) => {
        if (data && data.questions) {
          setQuizQuestions(data.questions);
          // Set default selections
          const initial: Record<number, string> = {};
          data.questions.forEach((q: any, i: number) => {
            initial[q.id] = i % 2 === 0 ? 'pitta' : 'vata';
          });
          setPrakritiAnswers(initial);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  const handleAddSymptom = (e: React.FormEvent) => {
    e.preventDefault();
    if (newSymptom.trim() && !selectedSymptoms.includes(newSymptom.trim())) {
      setSelectedSymptoms([...selectedSymptoms, newSymptom.trim()]);
      setNewSymptom('');
    }
  };

  const handleRemoveSymptom = (sym: string) => {
    setSelectedSymptoms(selectedSymptoms.filter((s) => s !== sym));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const answersList = Object.entries(prakritiAnswers).map(([qid, opt]) => ({
        question_id: Number(qid),
        selected_option: opt,
      }));

      const res = await submitIntake({
        chief_complaint: chiefComplaint,
        symptoms: selectedSymptoms,
        severity_level: severity,
        duration_days: durationDays,
        current_medications: currentMeds,
        prakriti_answers: answersList,
      });

      setResults(res);
      if (res.triage && res.triage.is_red_flag) {
        setShowEmergencyModal(true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Title */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <span className="text-xs uppercase tracking-widest font-bold text-ayur-700 bg-ayur-50 px-3 py-1 rounded-full border border-ayur-200">
          Step 2 & 3: Clinical Intake & Red-Flag Triage
        </span>
        <h1 className="text-3xl font-display font-bold text-slate-900">
          Ayurvedic Constitutional & Symptom Assessment
        </h1>
        <p className="text-xs sm:text-sm text-slate-600">
          Evaluates your Prakriti (Dosha ratio) and screens complaints against emergency clinical safety rules before retrieving classical Shloka RAG insights.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Form Inputs */}
        <div className="lg:col-span-7 space-y-8">
          {/* 1. Chief Complaint & Symptoms */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2 border-b border-slate-100 pb-2">
              <Stethoscope className="w-4 h-4 text-ayur-700" />
              <span>1. Presenting Clinical Complaints</span>
            </h3>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Primary Health Concern / Chief Complaint
              </label>
              <textarea
                value={chiefComplaint}
                onChange={(e) => setChiefComplaint(e.target.value)}
                rows={2}
                placeholder="e.g., Persistent hyperacidity after spicy meals, sour regurgitation..."
                className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:border-ayur-500 focus:ring-1 focus:ring-ayur-500 outline-none"
              />
            </div>

            {/* Symptoms Tags */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Associated Symptoms
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {selectedSymptoms.map((sym) => (
                  <span
                    key={sym}
                    className="inline-flex items-center space-x-1 text-xs bg-ayur-50 border border-ayur-200 text-ayur-900 px-2.5 py-1 rounded-lg font-medium"
                  >
                    <span>{sym}</span>
                    <button
                      onClick={() => handleRemoveSymptom(sym)}
                      className="text-ayur-600 hover:text-red-600 ml-1 font-bold"
                    >
                      ✕
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newSymptom}
                  onChange={(e) => setNewSymptom(e.target.value)}
                  placeholder="Add another symptom and press enter..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 outline-none"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSymptom(e);
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={handleAddSymptom}
                  className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
                >
                  Add
                </button>
              </div>

              {/* Sample emergency trigger helper */}
              <div className="mt-2 text-[11px] text-slate-400 flex items-center space-x-1">
                <span className="font-semibold text-slate-500">Test red-flag rule:</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedSymptoms(['Crushing chest pain radiating to left arm', 'Shortness of breath']);
                    setChiefComplaint('Sudden chest tightness');
                    setSeverity(9);
                  }}
                  className="text-red-600 underline font-medium hover:text-red-700"
                >
                  Click to simulate cardiac red-flag
                </button>
              </div>
            </div>

            {/* Severity Slider */}
            <div className="pt-2">
              <div className="flex justify-between text-xs mb-1">
                <span className="font-semibold text-slate-700">Self-Perceived Severity (1 - 10)</span>
                <span className={`font-bold ${severity >= 8 ? 'text-red-600' : 'text-ayur-700'}`}>
                  {severity} / 10 {severity >= 8 ? '(Critical)' : '(Mild/Moderate)'}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={severity}
                onChange={(e) => setSeverity(Number(e.target.value))}
                className="w-full accent-ayur-700 cursor-pointer"
              />
            </div>
          </div>

          {/* 2. Prakriti Quiz Matrix */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-gold-600" />
                <span>2. Classical Prakriti Diagnostic Matrix</span>
              </h3>
              <span className="text-[10px] text-slate-500 font-medium">5 Core Diagnostic Pillars</span>
            </div>

            <div className="space-y-4">
              {quizQuestions.map((q) => (
                <div key={q.id} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-900">{q.category}</span>
                    <span className="text-[10px] uppercase font-bold text-ayur-700">Q{q.id}</span>
                  </div>
                  <p className="text-xs text-slate-600">{q.question}</p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                    {q.options.map((opt: any) => {
                      const isSelected = prakritiAnswers[q.id] === opt.type;
                      return (
                        <button
                          key={opt.type}
                          type="button"
                          onClick={() => setPrakritiAnswers({ ...prakritiAnswers, [q.id]: opt.type })}
                          className={`p-2 rounded-lg text-left text-xs transition border ${
                            isSelected
                              ? 'bg-ayur-800 text-white border-ayur-900 shadow-xs'
                              : 'bg-white text-slate-700 border-slate-200 hover:border-ayur-300'
                          }`}
                        >
                          <span className="block font-bold uppercase text-[9px] tracking-wider opacity-80">
                            {opt.type}
                          </span>
                          <span className="line-clamp-2 leading-snug">{opt.text}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full py-3.5 bg-ayur-800 hover:bg-ayur-900 text-white text-sm font-bold rounded-xl shadow-md transition flex items-center justify-center space-x-2"
            >
              <span>{loading ? 'Evaluating Triage & Prakriti...' : 'Run Clinical Triage & Retrieve Shlokas'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Right Column: Triage Status & Results Preview */}
        <div className="lg:col-span-5 space-y-6">
          {results ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
              {/* Triage Banner */}
              <div
                className={`p-5 rounded-2xl border ${
                  results.triage.is_red_flag
                    ? 'bg-red-50 border-red-300 text-red-950'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-950'
                }`}
              >
                <div className="flex items-center space-x-2 mb-2">
                  {results.triage.is_red_flag ? (
                    <ShieldAlert className="w-5 h-5 text-red-600 animate-bounce" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  )}
                  <h4 className="text-sm font-bold uppercase tracking-wider">
                    {results.triage.status}
                  </h4>
                </div>
                <p className="text-xs leading-relaxed">{results.triage.clinical_disclaimer}</p>
                {results.triage.is_red_flag && (
                  <button
                    onClick={() => setShowEmergencyModal(true)}
                    className="mt-3 w-full py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-lg transition"
                  >
                    View Emergency Dispatch (112/108)
                  </button>
                )}
              </div>

              {/* Calculated Prakriti Score Card */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Constitutional Prakriti Ratio
                  </h4>
                  <span className="text-xs font-black px-2.5 py-0.5 rounded-full bg-ayur-100 text-ayur-900 font-serif">
                    {results.prakriti?.name}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="font-semibold text-blue-700">Vata (Ether + Air)</span>
                      <span className="font-bold">{results.prakriti?.vata}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-blue-600 h-full rounded-full" style={{ width: `${results.prakriti?.vata}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="font-semibold text-rose-700">Pitta (Fire + Water)</span>
                      <span className="font-bold">{results.prakriti?.pitta}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-rose-600 h-full rounded-full" style={{ width: `${results.prakriti?.pitta}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="font-semibold text-emerald-700">Kapha (Water + Earth)</span>
                      <span className="font-bold">{results.prakriti?.kapha}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div className="bg-emerald-600 h-full rounded-full" style={{ width: `${results.prakriti?.kapha}%` }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Matched Classical Shlokas */}
              {results.shlokas && results.shlokas.length > 0 && (
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center space-x-1.5">
                      <BookOpen className="w-4 h-4 text-ayur-700" />
                      <span>Matched Treatise Verses (RAG)</span>
                    </h4>
                    <button
                      onClick={() => setActiveTab('explorer')}
                      className="text-xs font-semibold text-ayur-700 hover:text-ayur-900"
                    >
                      View All
                    </button>
                  </div>

                  <div className="space-y-2.5">
                    {results.shlokas.slice(0, 2).map((s) => (
                      <div key={s.chunk_id} className="p-3 bg-amber-50/40 rounded-xl border border-amber-200/60 text-xs">
                        <div className="flex justify-between items-center text-[10px] font-bold text-amber-900 mb-1">
                          <span>{s.source_file}</span>
                          <span className="font-mono bg-amber-100 px-1 py-0.5 rounded">{s.chunk_id}</span>
                        </div>
                        <p className="sanskrit-verse font-medium text-slate-900 text-xs">{s.sanskrit}</p>
                        <p className="text-[11px] text-slate-600 mt-1 italic">{s.clinical_principle}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Matched Doctors */}
              {results.matched_doctors && results.matched_doctors.length > 0 && (
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center space-x-1.5">
                    <UserCheck className="w-4 h-4 text-ayur-700" />
                    <span>Recommended Verified Vaidyas</span>
                  </h4>

                  <div className="space-y-2">
                    {results.matched_doctors.slice(0, 2).map((doc) => (
                      <div
                        key={doc.id}
                        className="p-3 rounded-xl border border-slate-200 hover:border-ayur-300 transition flex items-center justify-between text-xs"
                      >
                        <div>
                          <p className="font-bold text-slate-900">{doc.name}</p>
                          <p className="text-[11px] text-slate-500">{doc.specialty}</p>
                          <span className="text-[10px] text-gold-700 font-bold">
                            Trust Score: {doc.trust_score} / 100
                          </span>
                        </div>
                        <button
                          onClick={() => {
                            onSelectDoctor(doc);
                            setActiveTab('doctors');
                          }}
                          className="px-3 py-1.5 bg-ayur-800 hover:bg-ayur-900 text-white rounded-lg text-xs font-semibold transition"
                        >
                          Consult
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 bg-white rounded-2xl border border-dashed border-slate-300 text-center text-slate-500 space-y-3">
              <div className="w-12 h-12 rounded-full bg-ayur-50 text-ayur-700 flex items-center justify-center mx-auto">
                <Stethoscope className="w-6 h-6" />
              </div>
              <h4 className="font-bold text-slate-800 text-sm">Ready for Diagnostic Intake</h4>
              <p className="text-xs leading-relaxed">
                Fill in your symptoms and answer the Prakriti questions on the left. Click <strong>"Run Clinical Triage"</strong> to verify safety rules and retrieve classical shlokas.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Emergency Modal */}
      <EmergencyModal
        isOpen={showEmergencyModal}
        onClose={() => setShowEmergencyModal(false)}
        triageData={results?.triage}
      />
    </div>
  );
};
