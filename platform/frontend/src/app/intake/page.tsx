"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Heart,
  Brain,
  Wind,
  Flame,
  Droplets,
  User,
  Stethoscope,
  ClipboardList,
} from "lucide-react";

const steps = [
  { id: 1, title: "Basic Info", icon: User },
  { id: 2, title: "Symptoms", icon: ClipboardList },
  { id: 3, title: "Health History", icon: Heart },
  { id: 4, title: "Prakriti Assessment", icon: Brain },
  { id: 5, title: "Review & Submit", icon: CheckCircle2 },
];

const doshaInfo = [
  { name: "Vata", icon: Wind, color: "#8b5cf6", desc: "Air & Space — Movement, creativity, flexibility" },
  { name: "Pitta", icon: Flame, color: "#ef4444", desc: "Fire & Water — Digestion, metabolism, intelligence" },
  { name: "Kapha", icon: Droplets, color: "#3b82f6", desc: "Water & Earth — Structure, lubrication, stability" },
];

const symptomOptions = [
  "Joint pain", "Digestive issues", "Skin disorders", "Respiratory problems",
  "Sleep disturbance", "Anxiety / Stress", "Hair loss", "Weight management",
  "Chronic fatigue", "Headache / Migraine", "Urinary issues", "Menstrual irregularity",
  "Allergies", "Eye problems", "Liver disorders", "Blood pressure",
];

export default function IntakePage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [severity, setSeverity] = useState(5);
  const [selectedDosha, setSelectedDosha] = useState<string | null>(null);

  const toggleSymptom = (s: string) => {
    setSelectedSymptoms((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 pt-24 pb-16">
        <div className="container-app max-w-4xl">
          {/* Header */}
          <div className="text-center mb-10 space-y-3 animate-fade-in-up">
            <span className="badge badge-emerald">
              <ClipboardList className="w-3 h-3" />
              Patient Intake
            </span>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              Tell Us About Your <span className="gradient-text">Health</span>
            </h1>
            <p className="text-[var(--foreground-muted)] max-w-lg mx-auto text-sm">
              Complete this guided form for a personalized Ayurvedic assessment.
              Your data powers grounded Shloka retrieval.
            </p>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center justify-center gap-0 mb-12 overflow-x-auto pb-2">
            {steps.map((step, i) => (
              <div key={step.id} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(step.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all
                    ${currentStep === step.id
                      ? "bg-gradient-to-r from-[var(--ayur-emerald)] to-[var(--ayur-emerald-light)] text-white shadow-lg"
                      : currentStep > step.id
                      ? "bg-[var(--background-card)] text-[var(--ayur-emerald-light)] border border-[var(--ayur-emerald)]"
                      : "bg-[var(--background-card)] text-[var(--foreground-dim)] border border-[var(--border)]"
                    }`}
                >
                  {currentStep > step.id ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <step.icon className="w-4 h-4" />
                  )}
                  <span className="hidden sm:inline">{step.title}</span>
                  <span className="sm:hidden">{step.id}</span>
                </button>
                {i < steps.length - 1 && (
                  <div
                    className={`w-8 h-0.5 mx-1 rounded transition-colors ${
                      currentStep > step.id
                        ? "bg-[var(--ayur-emerald)]"
                        : "bg-[var(--border)]"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Step Content */}
          <div className="card p-8 md:p-10 animate-fade-in">
            {/* Step 1: Basic Info */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Basic Information</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Full Name</label>
                    <input type="text" className="input" placeholder="Enter your full name" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Age</label>
                    <input type="number" className="input" placeholder="Your age" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Sex</label>
                    <select className="input">
                      <option value="">Select</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">City / State</label>
                    <input type="text" className="input" placeholder="e.g., Jaipur, Rajasthan" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Height (cm)</label>
                    <input type="number" className="input" placeholder="170" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Weight (kg)</label>
                    <input type="number" className="input" placeholder="65" />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Preferred Language</label>
                  <select className="input max-w-sm">
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="sa">Sanskrit</option>
                    <option value="ta">Tamil</option>
                    <option value="ml">Malayalam</option>
                  </select>
                </div>
              </div>
            )}

            {/* Step 2: Symptoms */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Symptoms & Complaints</h2>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Primary Disease / Chief Complaint</label>
                  <input type="text" className="input" placeholder="e.g., Chronic joint pain in knees" />
                </div>

                <div className="space-y-3">
                  <label className="text-sm text-[var(--foreground-muted)]">Select all applicable symptoms</label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {symptomOptions.map((s) => (
                      <button
                        key={s}
                        onClick={() => toggleSymptom(s)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium transition-all text-left
                          ${selectedSymptoms.includes(s)
                            ? "bg-[var(--ayur-emerald)] bg-opacity-20 border border-[var(--ayur-emerald)] text-[var(--ayur-emerald-light)]"
                            : "bg-[var(--background-elevated)] border border-[var(--border)] text-[var(--foreground-muted)] hover:border-[var(--border-hover)]"
                          }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="text-sm text-[var(--foreground-muted)]">
                    Severity: <span className="font-bold text-[var(--foreground)]">{severity}/10</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={severity}
                    onChange={(e) => setSeverity(Number(e.target.value))}
                    className="w-full accent-[var(--ayur-emerald)]"
                  />
                  <div className="flex justify-between text-xs text-[var(--foreground-dim)]">
                    <span>Mild</span><span>Moderate</span><span>Severe</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Onset Date</label>
                    <input type="date" className="input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Duration</label>
                    <select className="input">
                      <option value="">Select duration</option>
                      <option value="days">A few days</option>
                      <option value="weeks">A few weeks</option>
                      <option value="months">Months</option>
                      <option value="years">Years</option>
                    </select>
                  </div>
                </div>

                {severity >= 8 && (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.3)]">
                    <AlertTriangle className="w-5 h-5 text-[#ef4444] flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-[#f87171]">High Severity Detected</p>
                      <p className="text-xs text-[var(--foreground-muted)] mt-1">
                        The safety triage engine will prioritize your case. If symptoms are acute,
                        please seek immediate in-person medical attention.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Health History */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Health History & Lifestyle</h2>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Past Medical History</label>
                  <textarea className="input min-h-[100px]" placeholder="Any previous conditions, surgeries, allergies..." />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Current Medications</label>
                  <textarea className="input min-h-[80px]" placeholder="List any current Ayurvedic or allopathic medications..." />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Diet Type</label>
                    <select className="input">
                      <option value="">Select</option>
                      <option value="vegetarian">Vegetarian</option>
                      <option value="vegan">Vegan</option>
                      <option value="non-veg">Non-Vegetarian</option>
                      <option value="sattvic">Sattvic</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Sleep Pattern</label>
                    <select className="input">
                      <option value="">Select</option>
                      <option value="good">Good (7-8 hrs)</option>
                      <option value="moderate">Moderate (5-6 hrs)</option>
                      <option value="poor">Poor (less than 5 hrs)</option>
                      <option value="irregular">Irregular</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Exercise Level</label>
                    <select className="input">
                      <option value="">Select</option>
                      <option value="sedentary">Sedentary</option>
                      <option value="light">Light</option>
                      <option value="moderate">Moderate</option>
                      <option value="active">Very Active</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-[var(--foreground-muted)]">Stress Level</label>
                    <select className="input">
                      <option value="">Select</option>
                      <option value="low">Low</option>
                      <option value="moderate">Moderate</option>
                      <option value="high">High</option>
                      <option value="severe">Severe</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Aggravating Factors</label>
                  <input className="input" placeholder="What makes symptoms worse? e.g., cold weather, spicy food" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-[var(--foreground-muted)]">Relieving Factors</label>
                  <input className="input" placeholder="What helps? e.g., warm oil massage, rest" />
                </div>
              </div>
            )}

            {/* Step 4: Prakriti */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Prakriti Assessment</h2>
                <p className="text-sm text-[var(--foreground-muted)]">
                  Select the dominant constitution (Dosha) that best describes your natural tendencies.
                  This helps the system personalize Shloka retrieval.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {doshaInfo.map((dosha) => (
                    <button
                      key={dosha.name}
                      onClick={() => setSelectedDosha(dosha.name)}
                      className={`card p-6 text-left space-y-3 cursor-pointer transition-all
                        ${selectedDosha === dosha.name
                          ? "border-2"
                          : "hover:border-[var(--border-hover)]"
                        }`}
                      style={{
                        borderColor: selectedDosha === dosha.name ? dosha.color : undefined,
                        boxShadow: selectedDosha === dosha.name ? `0 0 30px ${dosha.color}20` : undefined,
                      }}
                    >
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ background: `${dosha.color}15`, border: `1px solid ${dosha.color}30` }}
                      >
                        <dosha.icon className="w-6 h-6" style={{ color: dosha.color }} />
                      </div>
                      <h3 className="text-lg font-semibold">{dosha.name}</h3>
                      <p className="text-sm text-[var(--foreground-muted)]">{dosha.desc}</p>
                      {selectedDosha === dosha.name && (
                        <div className="flex items-center gap-1.5 text-sm font-medium" style={{ color: dosha.color }}>
                          <CheckCircle2 className="w-4 h-4" />
                          Selected
                        </div>
                      )}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-[var(--foreground-dim)]">
                  A full Prakriti questionnaire with body constitution, mental tendencies,
                  and digestive characteristics will be available in the detailed assessment.
                </p>
              </div>
            )}

            {/* Step 5: Review */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Review & Submit</h2>
                <div className="space-y-4">
                  <div className="card p-5 space-y-2">
                    <h3 className="text-sm font-semibold text-[var(--foreground-muted)]">Selected Symptoms</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedSymptoms.length > 0 ? selectedSymptoms.map((s) => (
                        <span key={s} className="badge badge-emerald">{s}</span>
                      )) : (
                        <span className="text-sm text-[var(--foreground-dim)]">No symptoms selected</span>
                      )}
                    </div>
                  </div>
                  <div className="card p-5 space-y-2">
                    <h3 className="text-sm font-semibold text-[var(--foreground-muted)]">Severity</h3>
                    <p className="text-lg font-bold gradient-text">{severity}/10</p>
                  </div>
                  <div className="card p-5 space-y-2">
                    <h3 className="text-sm font-semibold text-[var(--foreground-muted)]">Prakriti</h3>
                    <p className="text-lg font-bold gradient-text-gold">{selectedDosha || "Not selected"}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-lg bg-[rgba(59,130,246,0.1)] border border-[rgba(59,130,246,0.3)]">
                  <Stethoscope className="w-5 h-5 text-[#3b82f6] flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-[#60a5fa]">What Happens Next</p>
                    <p className="text-xs text-[var(--foreground-muted)] mt-1">
                      Your intake will be processed through the Safety Triage → Hybrid Retrieval →
                      LLM Grounding pipeline. You will receive a grounded Shloka insight report.
                    </p>
                  </div>
                </div>

                <button className="btn btn-accent btn-lg w-full group">
                  Submit Intake & Get Insights
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-[var(--border)]">
              <button
                onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
                disabled={currentStep === 1}
                className="btn btn-ghost btn-sm disabled:opacity-30"
              >
                <ArrowLeft className="w-4 h-4" />
                Previous
              </button>
              {currentStep < 5 && (
                <button
                  onClick={() => setCurrentStep(Math.min(5, currentStep + 1))}
                  className="btn btn-primary btn-sm"
                >
                  Next Step
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
