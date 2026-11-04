import React, { useState, useEffect } from 'react';
import { 
  UserCheck, 
  ShieldCheck, 
  Award, 
  Star, 
  Clock, 
  Calendar, 
  CreditCard, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle,
  Search,
  Sparkles,
  Lock
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { getDoctors, getDoctorSlots, bookAppointment } from '../api/client';
import { Doctor } from '../types';
import { TrustScoreModal } from '../components/doctors/TrustScoreModal';
import { useLanguage } from '../context/LanguageContext';

interface DoctorsPageProps {
  selectedDoctor?: Doctor | null;
  onBookSuccess: (appointmentId: number, roomId: string) => void;
}

export const DoctorsPage: React.FC<DoctorsPageProps> = ({ selectedDoctor: initialDoc, onBookSuccess }) => {
  const { t } = useLanguage();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(false);
  const [specialtyFilter, setSpecialtyFilter] = useState('all');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [search, setSearch] = useState('');
  
  // Modals & Booking
  const [auditDoc, setAuditDoc] = useState<Doctor | null>(null);
  const [bookingDoc, setBookingDoc] = useState<Doctor | null>(initialDoc || null);
  const [slots, setSlots] = useState<any[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<string>('');
  const [bookingLoading, setBookingLoading] = useState(false);
  const [paymentStep, setPaymentStep] = useState(false);

  const fetchDoctorsList = async () => {
    setLoading(true);
    try {
      const data = await getDoctors({
        specialty: specialtyFilter === 'all' ? undefined : specialtyFilter,
        verified_only: verifiedOnly,
        search: search.trim() || undefined,
      });
      setDoctors(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctorsList();
  }, [specialtyFilter, verifiedOnly]);

  useEffect(() => {
    if (bookingDoc) {
      getDoctorSlots(bookingDoc.id)
        .then((res) => {
          if (res && res.slots) {
            setSlots(res.slots);
            if (res.slots.length > 0) setSelectedSlot(res.slots[0].iso_time);
          }
        })
        .catch((err) => console.error(err));
    }
  }, [bookingDoc]);

  const handleBookSubmit = async () => {
    if (!bookingDoc || !selectedSlot) return;
    setBookingLoading(true);
    try {
      const res = await bookAppointment({
        doctor_id: bookingDoc.id,
        slot_time: selectedSlot,
        chief_complaint: 'Digestive imbalance and constitutional optimization',
        symptoms: ['Acid reflux', 'Agnimandya'],
      });

      confetti({
        particleCount: 80,
        spread: 60,
        origin: { y: 0.6 }
      });

      setTimeout(() => {
        setBookingDoc(null);
        setPaymentStep(false);
        onBookSuccess(res.appointment_id, res.room_id);
      }, 1500);
    } catch (err) {
      console.error(err);
    } finally {
      setBookingLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Title */}
      <div className="text-center max-w-3xl mx-auto space-y-2">
        <span className="text-xs uppercase tracking-widest font-bold text-ayur-700 bg-ayur-50 px-3 py-1 rounded-full border border-ayur-200">
          Step 6 & 7: Doctor Match & Bayesian Trust Scoring
        </span>
        <h1 className="text-3xl sm:text-4xl font-display font-bold text-slate-900">
          Verified Ayurvedic Vaidya Network
        </h1>
        <p className="text-xs sm:text-sm text-slate-600">
          Ranked using the documented <strong>Bayesian Trust Score formula</strong>. Seeded practitioners from Kaggle are explicitly labeled as Unverified until official state register authentication.
        </p>
      </div>

      {/* Filter Header */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchDoctorsList()}
            placeholder="Search doctors by name or specialty..."
            className="w-full text-xs outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <select
            value={specialtyFilter}
            onChange={(e) => setSpecialtyFilter(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 font-medium outline-none"
          >
            <option value="all">All Specialties</option>
            <option value="Kayachikitsa">Kayachikitsa (Internal Medicine)</option>
            <option value="Shalakya">Shalakya & Panchakarma (ENT/Detox)</option>
            <option value="Dravya Guna">Dravya Guna (Pharmacology)</option>
            <option value="Prasuti">Prasuti Tantra (Women's Health)</option>
          </select>

          <label className="flex items-center space-x-2 cursor-pointer font-semibold text-slate-700 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded accent-ayur-700"
            />
            <span>Council Verified Only</span>
          </label>
        </div>
      </div>

      {/* Doctor Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {doctors.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-2xl border border-slate-200 hover:border-ayur-400 shadow-xs hover:shadow-md transition flex flex-col justify-between overflow-hidden"
          >
            <div className="p-5 space-y-4">
              {/* Doctor Header */}
              <div className="flex items-start space-x-3.5">
                <img
                  src={doc.avatar_url || 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=200&auto=format&fit=crop&q=80'}
                  alt={doc.name}
                  className="w-14 h-14 rounded-2xl object-cover border-2 border-ayur-100 shadow-xs shrink-0"
                />
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center space-x-1.5">
                    <h3 className="font-bold text-slate-900 text-sm truncate">{doc.name}</h3>
                    {doc.is_verified ? (
                      <span title="Council Verified" className="shrink-0 text-emerald-600">
                        <CheckCircle2 className="w-4 h-4 fill-emerald-100" />
                      </span>
                    ) : (
                      <span title="Unverified Seed" className="shrink-0 text-amber-500">
                        <AlertCircle className="w-4 h-4 fill-amber-100" />
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 truncate">{doc.qualification}</p>
                  <span className="inline-block text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-ayur-50 text-ayur-800 border border-ayur-100">
                    {doc.specialty}
                  </span>
                </div>
              </div>

              {/* Verification & Trust Badge Pill */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Trust Score (0-100)
                  </span>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span className="text-lg font-black text-ayur-900 font-display">{doc.trust_score}</span>
                    <button
                      onClick={() => setAuditDoc(doc)}
                      className="text-[10px] text-ayur-700 underline font-semibold flex items-center space-x-0.5 hover:text-ayur-900"
                    >
                      <HelpCircle className="w-3 h-3" />
                      <span>Audit Breakdown</span>
                    </button>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Bayesian Rating
                  </span>
                  <span className="font-bold text-slate-800 text-xs flex items-center justify-end space-x-1 mt-0.5">
                    <Star className="w-3.5 h-3.5 fill-gold-400 text-gold-500" />
                    <span>{doc.bayesian_rating} ({doc.total_reviews})</span>
                  </span>
                </div>
              </div>

              {/* Bio & Details */}
              <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                {doc.bio}
              </p>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100">
                <span>Experience: <strong className="text-slate-800">{doc.experience_years} yrs</strong></span>
                <span>Fee: <strong className="text-slate-900 font-bold">₹{doc.consultation_fee}</strong></span>
              </div>
            </div>

            {/* Action Bar */}
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                {doc.is_verified ? 'Verified Practitioner' : 'Awaiting Profile Claim'}
              </span>
              <button
                onClick={() => setBookingDoc(doc)}
                className="px-4 py-2 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl text-xs font-bold transition shadow-xs flex items-center space-x-1.5"
              >
                <Calendar className="w-3.5 h-3.5" />
                <span>Book Slot</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Trust Score Breakdown Modal */}
      <TrustScoreModal
        doctor={auditDoc}
        onClose={() => setAuditDoc(null)}
      />

      {/* Booking & Razorpay Modal */}
      {bookingDoc && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="relative bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="bg-ayur-900 p-5 text-white">
              <h3 className="font-bold text-lg">Book Teleconsultation</h3>
              <p className="text-xs text-ayur-200">Consult with {bookingDoc.name}</p>
            </div>

            <div className="p-6 space-y-4 text-xs">
              {!paymentStep ? (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-2">
                      Select Available Slot Time (Next 3 Days)
                    </label>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {slots.map((s) => (
                        <button
                          key={s.slot_id}
                          type="button"
                          onClick={() => setSelectedSlot(s.iso_time)}
                          className={`w-full p-2.5 rounded-xl border text-left flex justify-between items-center transition ${
                            selectedSlot === s.iso_time
                              ? 'bg-ayur-800 text-white border-ayur-900 font-bold'
                              : 'bg-slate-50 text-slate-800 border-slate-200 hover:border-ayur-300'
                          }`}
                        >
                          <span>{s.formatted}</span>
                          <Clock className="w-3.5 h-3.5" />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Consultation Fee</span>
                      <span className="font-bold text-slate-900">₹{bookingDoc.consultation_fee}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Platform & Telehealth Fee</span>
                      <span className="font-bold text-emerald-700">FREE</span>
                    </div>
                  </div>

                  <div className="flex space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setBookingDoc(null)}
                      className="w-1/2 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => setPaymentStep(true)}
                      className="w-1/2 py-2.5 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl font-bold transition shadow-xs"
                    >
                      Proceed to Pay
                    </button>
                  </div>
                </>
              ) : (
                /* Razorpay Mock Checkout Step */
                <div className="space-y-4">
                  <div className="bg-slate-900 text-white p-4 rounded-xl space-y-2 border border-slate-800">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center space-x-1.5 font-bold text-sm">
                        <CreditCard className="w-4 h-4 text-blue-400" />
                        <span>Razorpay Payment Gateway</span>
                      </div>
                      <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded font-mono">
                        Test Mode
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Merchant</span>
                      <span>AyurLLM Telehealth Hospital</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Total Payable</span>
                      <span className="text-base font-bold text-emerald-400">₹{bookingDoc.consultation_fee}</span>
                    </div>
                  </div>

                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs flex items-center space-x-2">
                    <Lock className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>256-bit TLS encrypted transaction compliant with Ayush Telemedicine guidelines.</span>
                  </div>

                  <div className="flex space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setPaymentStep(false)}
                      className="w-1/3 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold transition"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleBookSubmit}
                      disabled={bookingLoading}
                      className="w-2/3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition shadow-md flex items-center justify-center space-x-1.5"
                    >
                      <span>{bookingLoading ? 'Securing Transaction...' : `Pay ₹${bookingDoc.consultation_fee}`}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
