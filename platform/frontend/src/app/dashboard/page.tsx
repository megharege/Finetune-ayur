"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Activity,
  Calendar,
  FileText,
  Clock,
  TrendingUp,
  Settings,
  Bell,
  Search,
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="flex flex-col min-h-screen bg-[var(--background)]">
      <Navbar />

      <main className="flex-1 pt-24 pb-16">
        <div className="container-app">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold">Welcome, John</h1>
              <p className="text-[var(--foreground-muted)]">Here's your Ayurvedic health overview.</p>
            </div>
            <div className="flex items-center gap-3">
              <button className="icon-btn bg-[var(--background-card)] border border-[var(--border)]">
                <Search className="w-4 h-4" />
              </button>
              <button className="icon-btn bg-[var(--background-card)] border border-[var(--border)] relative">
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
              <button className="icon-btn bg-[var(--background-card)] border border-[var(--border)]">
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Main Content (Left Col) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Quick Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="card p-4">
                  <Activity className="w-5 h-5 text-[var(--ayur-emerald)] mb-2" />
                  <div className="text-2xl font-bold">4</div>
                  <div className="text-xs text-[var(--foreground-muted)]">Consultations</div>
                </div>
                <div className="card p-4">
                  <FileText className="w-5 h-5 text-[var(--ayur-gold)] mb-2" />
                  <div className="text-2xl font-bold">2</div>
                  <div className="text-xs text-[var(--foreground-muted)]">Prescriptions</div>
                </div>
                <div className="card p-4">
                  <TrendingUp className="w-5 h-5 text-blue-500 mb-2" />
                  <div className="text-2xl font-bold">85%</div>
                  <div className="text-xs text-[var(--foreground-muted)]">Health Score</div>
                </div>
                <div className="card p-4">
                  <Calendar className="w-5 h-5 text-purple-500 mb-2" />
                  <div className="text-2xl font-bold">1</div>
                  <div className="text-xs text-[var(--foreground-muted)]">Upcoming Appt.</div>
                </div>
              </div>

              {/* Knowledge Graph Preview */}
              <div className="card p-6 border border-[var(--ayur-gold)]/20 shadow-[0_0_20px_rgba(212,168,67,0.05)]">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--ayur-gold)]"></span>
                    Your Health Graph
                  </h3>
                  <button className="text-sm text-[var(--ayur-gold-light)] hover:underline">Expand View</button>
                </div>
                
                <div className="bg-[var(--background-elevated)] rounded-xl h-[300px] flex flex-col items-center justify-center border border-[var(--border)] relative overflow-hidden">
                   <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5"></div>
                   <Activity className="w-12 h-12 text-[var(--foreground-dim)] mb-4" />
                   <p className="text-[var(--foreground-muted)] text-sm mb-2">Interactive Neo4j graph visualization goes here.</p>
                   <p className="text-xs text-[var(--foreground-dim)] max-w-xs text-center">Shows links between your symptoms, Vata/Pitta doshas, and retrieved Shlokas.</p>
                </div>
              </div>

              {/* Recent Insights */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold mb-4">Recent AI Insights</h3>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-[rgba(13,107,63,0.1)] border border-[rgba(13,107,63,0.2)]">
                    <h4 className="font-semibold text-[var(--ayur-emerald-light)] mb-1">Vata Aggravation Detected</h4>
                    <p className="text-sm text-[var(--foreground-muted)]">Based on your recent intake regarding joint pain and sleep disturbance, there is a strong indication of Vata imbalance.</p>
                  </div>
                </div>
              </div>

            </div>

            {/* Sidebar (Right Col) */}
            <div className="space-y-6">
              
              {/* Upcoming */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold mb-4">Upcoming Schedule</h3>
                <div className="space-y-3">
                  <div className="p-3 rounded-lg border border-[var(--border)] flex items-start gap-3 hover:border-[var(--ayur-emerald)] transition-colors">
                     <div className="w-10 h-10 rounded-lg bg-[var(--background-elevated)] flex items-center justify-center flex-shrink-0">
                        <Clock className="w-5 h-5 text-[var(--foreground-dim)]" />
                     </div>
                     <div>
                        <h4 className="text-sm font-semibold">Consultation</h4>
                        <p className="text-xs text-[var(--foreground-muted)]">Dr. Ananya Sharma • Video Call</p>
                        <p className="text-xs text-[var(--ayur-emerald-light)] font-medium mt-1">Today, 4:00 PM</p>
                     </div>
                  </div>
                </div>
                <button className="w-full btn btn-ghost btn-sm mt-4">View All</button>
              </div>

              {/* Prakriti Info */}
              <div className="card p-6 bg-gradient-to-br from-[var(--background-card)] to-[#1a1f1d]">
                <h3 className="text-sm font-semibold text-[var(--foreground-muted)] uppercase tracking-wider mb-2">Your Constitution</h3>
                <div className="flex items-end gap-3 mb-4">
                   <div className="text-3xl font-bold gradient-text">Vata-Pitta</div>
                </div>
                <p className="text-sm text-[var(--foreground-muted)] leading-relaxed mb-4">
                  Air and Fire dominant. Focus on grounding foods, routine, and avoiding extreme heat or dryness.
                </p>
                <Link href="/intake" className="text-sm text-[var(--ayur-emerald-light)] hover:underline block text-center">
                  Retake Assessment
                </Link>
              </div>

            </div>

          </div>

        </div>
      </main>
      
      <Footer />
    </div>
  );
}
