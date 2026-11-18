"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Search,
  Star,
  MapPin,
  Award,
  Phone,
  ShieldCheck,
  Filter,
  ChevronDown,
  Clock,
  IndianRupee,
  Users,
  BadgeCheck,
  Stethoscope,
} from "lucide-react";

/* ─── Demo Doctors ─── */
const doctors = [
  {
    id: 1,
    name: "Dr. Ananya Sharma",
    specialty: "Panchakarma & Detox",
    qualifications: "BAMS, MD (Ayurveda)",
    experience: 14,
    city: "Jaipur",
    state: "Rajasthan",
    clinic: "Arogya Ayurved Clinic",
    fee: 800,
    rating: 4.8,
    reviews: 234,
    verified: true,
    languages: ["Hindi", "English", "Sanskrit"],
    available: true,
    trustScore: 92,
  },
  {
    id: 2,
    name: "Dr. Rajesh Menon",
    specialty: "Rasayana & Geriatrics",
    qualifications: "BAMS, PhD (Rasashastra)",
    experience: 22,
    city: "Kochi",
    state: "Kerala",
    clinic: "Kerala Ayurveda Centre",
    fee: 1200,
    rating: 4.9,
    reviews: 412,
    verified: true,
    languages: ["Malayalam", "English", "Hindi"],
    available: true,
    trustScore: 97,
  },
  {
    id: 3,
    name: "Dr. Priya Nair",
    specialty: "Stree Roga (Gynecology)",
    qualifications: "BAMS, MS (Ayurveda)",
    experience: 9,
    city: "Pune",
    state: "Maharashtra",
    clinic: "Dhanvantari Women's Clinic",
    fee: 600,
    rating: 4.6,
    reviews: 156,
    verified: true,
    languages: ["Marathi", "Hindi", "English"],
    available: false,
    trustScore: 85,
  },
  {
    id: 4,
    name: "Dr. Vikram Joshi",
    specialty: "Kaya Chikitsa (Internal Medicine)",
    qualifications: "BAMS, MD (Kayachikitsa)",
    experience: 18,
    city: "Varanasi",
    state: "Uttar Pradesh",
    clinic: "Charak Ayurveda Hospital",
    fee: 500,
    rating: 4.7,
    reviews: 321,
    verified: true,
    languages: ["Hindi", "Sanskrit", "English"],
    available: true,
    trustScore: 90,
  },
  {
    id: 5,
    name: "Dr. Lakshmi Devi",
    specialty: "Bala Roga (Pediatrics)",
    qualifications: "BAMS, MD (Bal Roga)",
    experience: 11,
    city: "Chennai",
    state: "Tamil Nadu",
    clinic: "Siddha Ayurveda Clinic",
    fee: 700,
    rating: 4.5,
    reviews: 189,
    verified: false,
    languages: ["Tamil", "English"],
    available: true,
    trustScore: 78,
  },
  {
    id: 6,
    name: "Dr. Arun Kumar",
    specialty: "Shalya Tantra (Surgery)",
    qualifications: "BAMS, MS (Shalya)",
    experience: 16,
    city: "Bengaluru",
    state: "Karnataka",
    clinic: "Ashwini Ayurveda Institute",
    fee: 1000,
    rating: 4.8,
    reviews: 267,
    verified: true,
    languages: ["Kannada", "Hindi", "English"],
    available: true,
    trustScore: 94,
  },
];

const specialties = [
  "All Specialties",
  "Panchakarma & Detox",
  "Rasayana & Geriatrics",
  "Stree Roga (Gynecology)",
  "Kaya Chikitsa (Internal Medicine)",
  "Bala Roga (Pediatrics)",
  "Shalya Tantra (Surgery)",
];

export default function DoctorsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpecialty, setSelectedSpecialty] = useState("All Specialties");

  const filtered = doctors.filter((d) => {
    const matchesSearch =
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.city.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.specialty.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSpecialty =
      selectedSpecialty === "All Specialties" || d.specialty === selectedSpecialty;
    return matchesSearch && matchesSpecialty;
  });

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 pt-24 pb-16">
        <div className="container-app">
          {/* Header */}
          <div className="text-center mb-10 space-y-3 animate-fade-in-up">
            <span className="badge badge-emerald">
              <Stethoscope className="w-3 h-3" />
              Verified Network
            </span>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              Find Ayurvedic <span className="gradient-text">Doctors</span>
            </h1>
            <p className="text-[var(--foreground-muted)] max-w-lg mx-auto text-sm">
              Browse verified practitioners with Bayesian trust scoring. Book consultations directly.
            </p>
          </div>

          {/* Filters */}
          <div className="card p-4 mb-8 animate-fade-in-up delay-100">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-dim)]" />
                <input
                  type="text"
                  className="input pl-10"
                  placeholder="Search by name, city, or specialty..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="relative">
                <select
                  className="input pr-10 min-w-[220px]"
                  value={selectedSpecialty}
                  onChange={(e) => setSelectedSpecialty(e.target.value)}
                >
                  {specialties.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Results Count */}
          <div className="flex items-center justify-between mb-6 text-sm">
            <p className="text-[var(--foreground-muted)]">
              <span className="font-semibold text-[var(--foreground)]">{filtered.length}</span>{" "}
              doctors found
            </p>
            <div className="flex items-center gap-2 text-[var(--foreground-dim)]">
              <Filter className="w-3.5 h-3.5" />
              Sorted by Trust Score
            </div>
          </div>

          {/* Doctor Cards */}
          <div className="space-y-4 stagger-children">
            {filtered.map((doc) => (
              <div key={doc.id} className="card p-6 flex flex-col lg:flex-row gap-6">
                {/* Avatar */}
                <div className="flex-shrink-0">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center text-white text-2xl font-bold">
                    {doc.name.split(" ").slice(1).map(n => n[0]).join("")}
                  </div>
                </div>

                {/* Info */}
                <div className="flex-1 space-y-3">
                  <div className="flex items-start justify-between flex-wrap gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold">{doc.name}</h3>
                        {doc.verified && (
                          <BadgeCheck className="w-5 h-5 text-[var(--ayur-emerald-light)]" />
                        )}
                      </div>
                      <p className="text-sm text-[var(--ayur-gold)]">{doc.specialty}</p>
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--background-elevated)]">
                      <Star className="w-4 h-4 text-[var(--ayur-gold)] fill-[var(--ayur-gold)]" />
                      <span className="font-semibold text-sm">{doc.rating}</span>
                      <span className="text-xs text-[var(--foreground-dim)]">({doc.reviews})</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-[var(--foreground-muted)]">
                    <span className="flex items-center gap-1.5">
                      <Award className="w-3.5 h-3.5" />
                      {doc.qualifications}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {doc.experience} yrs experience
                    </span>
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5" />
                      {doc.city}, {doc.state}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <IndianRupee className="w-3.5 h-3.5" />
                      ₹{doc.fee} / consult
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {doc.languages.map((lang) => (
                      <span key={lang} className="badge badge-emerald text-[0.65rem]">{lang}</span>
                    ))}
                    <span
                      className={`badge text-[0.65rem] ${doc.available ? "badge-emerald" : "badge-red"}`}
                    >
                      {doc.available ? "● Available Now" : "● Unavailable"}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 justify-center min-w-[160px]">
                  <div className="text-center mb-2">
                    <div className="text-xs text-[var(--foreground-dim)]">Trust Score</div>
                    <div className="text-2xl font-bold gradient-text">{doc.trustScore}%</div>
                  </div>
                  <button className="btn btn-primary btn-sm w-full" disabled={!doc.available}>
                    Book Consultation
                  </button>
                  <button className="btn btn-ghost btn-sm w-full">
                    View Profile
                  </button>
                </div>
              </div>
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="card p-12 text-center">
              <Users className="w-12 h-12 mx-auto text-[var(--foreground-dim)] mb-4" />
              <h3 className="text-lg font-semibold mb-2">No doctors found</h3>
              <p className="text-sm text-[var(--foreground-muted)]">
                Try adjusting your search query or filters.
              </p>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
