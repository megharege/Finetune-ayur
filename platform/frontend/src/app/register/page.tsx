"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Leaf,
  User,
  Phone,
  ShieldCheck,
} from "lucide-react";

const roles = [
  { value: "patient", label: "Patient", desc: "Access intake forms and health insights" },
  { value: "doctor", label: "Doctor", desc: "Manage patients and consultations" },
  { value: "admin", label: "Admin", desc: "Full platform administration" },
];

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState("patient");

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 flex items-center justify-center pt-24 pb-16 relative overflow-hidden">
        <div className="absolute inset-0 gradient-mesh pointer-events-none" />
        <div className="absolute top-1/3 right-1/4 w-[400px] h-[400px] bg-[var(--ayur-emerald)] opacity-[0.04] rounded-full blur-[120px]" />

        <div className="container-app max-w-md relative z-10">
          <div className="card p-8 md:p-10 space-y-8 animate-fade-in-up">
            <div className="text-center space-y-3">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-[var(--ayur-gold-dark)] to-[var(--ayur-gold)] flex items-center justify-center">
                <Leaf className="w-7 h-7 text-white" />
              </div>
              <h1 className="text-2xl font-bold">Create Account</h1>
              <p className="text-sm text-[var(--foreground-muted)]">
                Join AyurLLM Care for personalized Ayurvedic insights
              </p>
            </div>

            {/* Role Selector */}
            <div className="space-y-2">
              <label className="text-sm text-[var(--foreground-muted)]">I am a</label>
              <div className="grid grid-cols-3 gap-2">
                {roles.map((role) => (
                  <button
                    key={role.value}
                    onClick={() => setSelectedRole(role.value)}
                    className={`p-3 rounded-lg text-center transition-all text-sm
                      ${selectedRole === role.value
                        ? "bg-[var(--ayur-emerald)] bg-opacity-15 border-2 border-[var(--ayur-emerald)] text-[var(--ayur-emerald-light)]"
                        : "bg-[var(--background-elevated)] border border-[var(--border)] text-[var(--foreground-muted)] hover:border-[var(--border-hover)]"
                      }`}
                  >
                    <div className="font-semibold">{role.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
              <div className="space-y-2">
                <label className="text-sm text-[var(--foreground-muted)]">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                  <input type="email" className="input pl-10" placeholder="you@example.com" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-[var(--foreground-muted)]">Phone (Optional)</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                  <input type="tel" className="input pl-10" placeholder="+91 XXXXX XXXXX" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-[var(--foreground-muted)]">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                  <input
                    type={showPassword ? "text" : "password"}
                    className="input pl-10 pr-10"
                    placeholder="Min. 8 characters"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--foreground-dim)] hover:text-[var(--foreground-muted)] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-[rgba(13,107,63,0.08)] border border-[rgba(13,107,63,0.2)]">
                <ShieldCheck className="w-4 h-4 text-[var(--ayur-emerald-light)] flex-shrink-0 mt-0.5" />
                <p className="text-xs text-[var(--foreground-muted)]">
                  Your data is encrypted with AES-256 and stored securely. We follow healthcare-grade
                  privacy standards.
                </p>
              </div>

              <button type="submit" className="btn btn-accent btn-lg w-full group">
                Create Account
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>
            </form>

            <p className="text-center text-sm text-[var(--foreground-muted)]">
              Already have an account?{" "}
              <Link href="/login" className="text-[var(--ayur-emerald-light)] font-medium hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
