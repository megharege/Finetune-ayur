"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Leaf,
  Menu,
  X,
  Search,
  Stethoscope,
  BookOpen,
  Video,
  LayoutDashboard,
  LogIn,
} from "lucide-react";

const navLinks = [
  { href: "/intake", label: "Patient Intake", icon: BookOpen },
  { href: "/doctors", label: "Find Doctors", icon: Stethoscope },
  { href: "/search", label: "Shloka Search", icon: Search },
  { href: "/consultation", label: "Teleconsult", icon: Video },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="container-app">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center transition-transform group-hover:scale-110">
              <Leaf className="w-5 h-5 text-white" />
              <div className="absolute inset-0 rounded-lg bg-[var(--ayur-emerald-light)] opacity-0 group-hover:opacity-20 transition-opacity" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight">
                Ayur<span className="gradient-text">LLM</span>
              </span>
              <span className="text-[var(--foreground-dim)] text-xs ml-1.5 font-medium">
                Care
              </span>
            </div>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (pathname.startsWith(link.href) && link.href !== "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`nav-link flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors ${
                    isActive ? "bg-[var(--background-card)] text-[var(--ayur-emerald-light)] font-semibold" : "hover:bg-[var(--background-card)]"
                  }`}
                >
                  <link.icon className="w-3.5 h-3.5" />
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="/login" className="btn btn-ghost btn-sm">
              <LogIn className="w-4 h-4" />
              Sign In
            </Link>
            <Link href="/register" className="btn btn-primary btn-sm">
              Get Started
            </Link>
          </div>

          {/* Mobile Toggle */}
          <button
            className="md:hidden icon-btn"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle menu"
          >
            {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden animate-fade-in border-t border-[var(--border)]">
          <div className="container-app py-4 space-y-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (pathname.startsWith(link.href) && link.href !== "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`nav-link flex items-center gap-2.5 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive ? "bg-[var(--background-card)] text-[var(--ayur-emerald-light)] font-semibold" : "hover:bg-[var(--background-card)]"
                  }`}
                  onClick={() => setIsOpen(false)}
                >
                  <link.icon className="w-4 h-4" />
                  {link.label}
                </Link>
              );
            })}
            <div className="pt-3 flex flex-col gap-2">
              <Link
                href="/login"
                className="btn btn-ghost btn-sm w-full"
                onClick={() => setIsOpen(false)}
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="btn btn-primary btn-sm w-full"
                onClick={() => setIsOpen(false)}
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
