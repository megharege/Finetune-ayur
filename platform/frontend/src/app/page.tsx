"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  BookOpen,
  Stethoscope,
  Search,
  Video,
  Network,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Pill,
  Brain,
  Heart,
  Activity,
  Leaf,
  ChevronRight,
  Star,
  Clock,
  CheckCircle2,
  Users,
  Zap,
} from "lucide-react";

/* ─── Feature Cards Data ─── */
const features = [
  {
    icon: BookOpen,
    title: "Classical Shloka Retrieval",
    desc: "Hybrid AI search across 8 verified Ayurvedic texts. Sanskrit originals with translations, grounded in authentic classical references.",
    color: "var(--ayur-emerald)",
    badge: "AI Powered",
  },
  {
    icon: Network,
    title: "Personal Knowledge Graph",
    desc: "Interactive Neo4j-powered visual network mapping your symptoms, doshas, treatments, and relevant Shlokas in real time.",
    color: "var(--ayur-gold)",
    badge: "Neo4j",
  },
  {
    icon: Stethoscope,
    title: "Verified Doctor Network",
    desc: "Search verified Ayurvedic practitioners by specialty, location, and ratings. Bayesian trust scoring ensures quality.",
    color: "#3b82f6",
    badge: "Trusted",
  },
  {
    icon: Video,
    title: "Teleconsultation",
    desc: "Book slots, join video consultations, receive e-prescriptions and SOAP notes — all within the platform.",
    color: "#8b5cf6",
    badge: "Live",
  },
  {
    icon: ShieldCheck,
    title: "Safety Triage Engine",
    desc: "Rule-based safety layer intercepts emergencies before LLM retrieval. Red-flag symptoms trigger immediate protocols.",
    color: "#ef4444",
    badge: "Critical",
  },
  {
    icon: Pill,
    title: "Hospital Management",
    desc: "Full OPD/IPD management, herbal pharmacy inventory, Panchakarma therapy bookings, and diet plan generation.",
    color: "#14b8a6",
    badge: "HIS",
  },
];

/* ─── Stats ─── */
const stats = [
  { value: "8", label: "Classical Texts", icon: BookOpen },
  { value: "10K+", label: "Shloka Verses", icon: Sparkles },
  { value: "500+", label: "Verified Doctors", icon: Users },
  { value: "98%", label: "Grounding Accuracy", icon: CheckCircle2 },
];

/* ─── Pipeline Steps ─── */
const pipeline = [
  {
    step: "01",
    title: "Patient Intake",
    desc: "Detailed symptoms, history, lifestyle & Prakriti assessment via guided multi-step form.",
    icon: Heart,
  },
  {
    step: "02",
    title: "Safety Triage",
    desc: "Rule engine checks for emergency red flags. Critical cases routed immediately.",
    icon: ShieldCheck,
  },
  {
    step: "03",
    title: "Hybrid Retrieval",
    desc: "Meilisearch queries the 8-book corpus with keyword + semantic vector search.",
    icon: Search,
  },
  {
    step: "04",
    title: "LLM Grounding",
    desc: "AI reranks chunks and formulates explanations strictly citing retrieved references.",
    icon: Brain,
  },
  {
    step: "05",
    title: "Knowledge Graph",
    desc: "Neo4j is updated asynchronously — linking patient to symptoms, doshas & Shlokas.",
    icon: Network,
  },
  {
    step: "06",
    title: "Clinical Insight",
    desc: "Doctors review grounded insights, prescribe treatments & manage patient holistically.",
    icon: Activity,
  },
];

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      {/* ═══ HERO SECTION ═══ */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
        {/* Ambient background */}
        <div className="absolute inset-0 gradient-mesh pointer-events-none" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-[var(--ayur-emerald)] opacity-[0.04] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-[var(--ayur-gold)] opacity-[0.03] rounded-full blur-[100px]" />

        {/* Floating decorative elements */}
        <div className="absolute top-32 left-[10%] w-2 h-2 rounded-full bg-[var(--ayur-emerald-light)] opacity-40 animate-float" />
        <div className="absolute top-52 right-[15%] w-1.5 h-1.5 rounded-full bg-[var(--ayur-gold)] opacity-30 animate-float delay-200" />
        <div className="absolute top-72 left-[25%] w-1 h-1 rounded-full bg-[var(--ayur-emerald)] opacity-50 animate-float delay-400" />

        <div className="container-app relative z-10">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            {/* Badge */}
            <div className="animate-fade-in-up inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm">
              <Sparkles className="w-4 h-4 text-[var(--ayur-gold)]" />
              <span className="text-[var(--foreground-muted)]">
                AI-Powered Ayurvedic Decision Support
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-[var(--foreground-dim)]" />
            </div>

            {/* Heading */}
            <h1 className="animate-fade-in-up delay-100 text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1]">
              Classical Wisdom,
              <br />
              <span className="gradient-text">Modern Intelligence</span>
            </h1>

            {/* Subheading */}
            <p className="animate-fade-in-up delay-200 text-lg md:text-xl text-[var(--foreground-muted)] max-w-2xl mx-auto leading-relaxed">
              AyurLLM Care bridges 5,000 years of Ayurvedic Shloka knowledge
              with cutting-edge AI — grounded retrieval, personal health graphs,
              and a complete hospital management platform.
            </p>

            {/* CTAs */}
            <div className="animate-fade-in-up delay-300 flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
              <Link href="/intake" className="btn btn-primary btn-lg group">
                Start Patient Intake
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link href="/search" className="btn btn-ghost btn-lg">
                <Search className="w-4 h-4" />
                Search Shlokas
              </Link>
            </div>

            {/* Disclaimer */}
            <p className="animate-fade-in-up delay-400 text-xs text-[var(--foreground-dim)] max-w-lg mx-auto">
              ⚕ Decision-support tool. Prescriptions & diagnoses are issued only
              by verified, registered Ayurvedic practitioners.
            </p>
          </div>
        </div>
      </section>

      {/* ═══ STATS BAR ═══ */}
      <section className="relative py-6 border-y border-[var(--border)]">
        <div className="container-app">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat, i) => (
              <div
                key={stat.label}
                className="animate-fade-in-up flex items-center gap-3 justify-center"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="w-10 h-10 rounded-lg bg-[var(--background-card)] flex items-center justify-center">
                  <stat.icon className="w-5 h-5 text-[var(--ayur-emerald-light)]" />
                </div>
                <div>
                  <div className="text-xl font-bold gradient-text-gold">
                    {stat.value}
                  </div>
                  <div className="text-xs text-[var(--foreground-dim)]">
                    {stat.label}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ FEATURES GRID ═══ */}
      <section className="section">
        <div className="container-app">
          <div className="text-center mb-14 space-y-4">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              Everything You Need,{" "}
              <span className="gradient-text">In One Platform</span>
            </h2>
            <p className="text-[var(--foreground-muted)] max-w-xl mx-auto">
              From AI-powered Shloka retrieval to complete hospital operations — a
              unified ecosystem for Ayurvedic care.
            </p>
          </div>

          <div className="grid-features stagger-children">
            {features.map((feat) => (
              <div key={feat.title} className="card p-6 space-y-4 group cursor-pointer">
                <div className="flex items-start justify-between">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
                    style={{
                      background: `${feat.color}15`,
                      border: `1px solid ${feat.color}30`,
                    }}
                  >
                    <feat.icon className="w-6 h-6" style={{ color: feat.color }} />
                  </div>
                  <span
                    className="badge text-[0.65rem]"
                    style={{
                      background: `${feat.color}12`,
                      color: feat.color,
                      border: `1px solid ${feat.color}25`,
                    }}
                  >
                    {feat.badge}
                  </span>
                </div>
                <h3 className="text-lg font-semibold">{feat.title}</h3>
                <p className="text-sm text-[var(--foreground-muted)] leading-relaxed">
                  {feat.desc}
                </p>
                <div className="flex items-center gap-1.5 text-sm font-medium text-[var(--foreground-dim)] group-hover:text-[var(--ayur-emerald-light)] transition-colors">
                  Learn more
                  <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ PIPELINE SECTION ═══ */}
      <section className="section bg-[var(--background-elevated)] border-y border-[var(--border)]">
        <div className="container-app">
          <div className="text-center mb-14 space-y-4">
            <span className="badge badge-gold">
              <Zap className="w-3 h-3" />
              How It Works
            </span>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              From Intake to{" "}
              <span className="gradient-text">Clinical Insight</span>
            </h2>
            <p className="text-[var(--foreground-muted)] max-w-xl mx-auto">
              A 6-step pipeline that transforms patient symptoms into grounded
              Ayurvedic insights with safety-first design.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
            {pipeline.map((step, i) => (
              <div key={step.step} className="card p-6 space-y-4 relative overflow-hidden">
                {/* Step number watermark */}
                <div className="absolute top-3 right-4 text-5xl font-black text-[var(--foreground)] opacity-[0.04]">
                  {step.step}
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center">
                    <step.icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <span className="text-xs text-[var(--foreground-dim)] font-mono">
                      STEP {step.step}
                    </span>
                    <h3 className="text-base font-semibold">{step.title}</h3>
                  </div>
                </div>
                <p className="text-sm text-[var(--foreground-muted)] leading-relaxed">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ CTA SECTION ═══ */}
      <section className="section relative overflow-hidden">
        <div className="absolute inset-0 gradient-mesh pointer-events-none" />
        <div className="container-app relative z-10">
          <div className="card p-10 md:p-16 text-center space-y-6 animate-pulse-glow">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-gold-dark)] flex items-center justify-center">
              <Leaf className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              Ready to Experience <span className="gradient-text">AyurLLM Care</span>?
            </h2>
            <p className="text-[var(--foreground-muted)] max-w-lg mx-auto">
              Start your Ayurvedic health journey with AI-powered insights
              grounded in classical wisdom. No hallucinations — only referenced
              Shloka knowledge.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
              <Link href="/register" className="btn btn-accent btn-lg group">
                Create Free Account
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link href="/doctors" className="btn btn-ghost btn-lg">
                <Stethoscope className="w-4 h-4" />
                Browse Doctors
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
