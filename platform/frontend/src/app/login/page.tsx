"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  LogIn,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Leaf,
  Sparkles,
} from "lucide-react";

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 flex items-center justify-center pt-24 pb-16 relative overflow-hidden">
        {/* Ambient */}
        <div className="absolute inset-0 gradient-mesh pointer-events-none" />
        <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-[var(--ayur-emerald)] opacity-[0.04] rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-[var(--ayur-gold)] opacity-[0.03] rounded-full blur-[100px]" />

        <div className="container-app max-w-md relative z-10">
          <div className="card p-8 md:p-10 space-y-8 animate-fade-in-up">
            {/* Header */}
            <div className="text-center space-y-3">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center">
                <Leaf className="w-7 h-7 text-white" />
              </div>
              <h1 className="text-2xl font-bold">Welcome Back</h1>
              <p className="text-sm text-[var(--foreground-muted)]">
                Sign in to your AyurLLM Care account
              </p>
            </div>

            {/* Form */}
            <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
              <div className="space-y-2">
                <label className="text-sm text-[var(--foreground-muted)]">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                  <input
                    type="email"
                    className="input pl-10"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--foreground-muted)]">Password</label>
                  <Link href="#" className="text-xs text-[var(--ayur-emerald-light)] hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                  <input
                    type={showPassword ? "text" : "password"}
                    className="input pl-10 pr-10"
                    placeholder="••••••••"
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

              <button type="submit" className="btn btn-primary btn-lg w-full group">
                Sign In
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 divider" />
              <span className="text-xs text-[var(--foreground-dim)]">or</span>
              <div className="flex-1 divider" />
            </div>

            {/* Register Link */}
            <p className="text-center text-sm text-[var(--foreground-muted)]">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-[var(--ayur-emerald-light)] font-medium hover:underline">
                Create Account
              </Link>
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
