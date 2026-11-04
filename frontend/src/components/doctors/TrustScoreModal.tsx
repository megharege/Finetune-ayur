import React from 'react';
import { ShieldCheck, Award, X, HelpCircle, CheckCircle, AlertCircle, BarChart3 } from 'lucide-react';
import { Doctor } from '../../types';

interface TrustScoreModalProps {
  doctor: Doctor | null;
  onClose: () => void;
}

export const TrustScoreModal: React.FC<TrustScoreModalProps> = ({ doctor, onClose }) => {
  if (!doctor) return null;

  const breakdown = doctor.trust_breakdown || {};

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-150">
        {/* Header */}
        <div className="bg-gradient-to-r from-ayur-900 to-ayur-800 p-6 text-white relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 p-1.5 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-gold-500/20 border border-gold-400/40 flex items-center justify-center text-gold-300 font-bold text-lg">
              {doctor.trust_score}
            </div>
            <div>
              <h3 className="text-xl font-bold">{doctor.name}</h3>
              <p className="text-xs text-ayur-200">
                Official AyurLLM Bayesian Trust Score Audit
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 text-xs text-slate-700">
          {/* Formula summary */}
          <div className="bg-ayur-50/70 border border-ayur-200 rounded-xl p-3.5 space-y-1.5">
            <span className="font-bold text-ayur-950 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
              <BarChart3 className="w-4 h-4 text-ayur-700" />
              <span>AyurLLM Section C Weighted Algorithmic Formula</span>
            </span>
            <p className="font-mono text-[11px] text-ayur-900 bg-white/80 p-2 rounded-lg border border-ayur-200">
              Trust Score = 40% Rating + 20% Verification + 15% Experience + 10% Completion + 10% Response + 5% Profile
            </p>
          </div>

          {/* Breakdown Rows */}
          <div className="space-y-3">
            {/* 1. Rating */}
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-slate-800">1. Bayesian Rating (Weight: 40%)</span>
                <span className="font-bold text-ayur-700">+{breakdown.bayesian_rating?.contribution || '28.0'} pts</span>
              </div>
              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-ayur-600 h-full rounded-full" 
                  style={{ width: `${(doctor.bayesian_rating / 5) * 100}%` }}
                />
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                Bayesian score: <strong>{doctor.bayesian_rating} / 5.0</strong> based on {doctor.total_reviews} verified reviews.
                Uses prior <em>C=5, m=3.5</em> so low-sample outliers cannot game the rank.
              </p>
            </div>

            {/* 2. Verification */}
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-slate-800">2. State Council Verification (Weight: 20%)</span>
                <span className="font-bold text-ayur-700">+{breakdown.verification?.contribution || (doctor.is_verified ? '20.0' : '2.0')} pts</span>
              </div>
              <div className="flex items-center space-x-1.5 mt-1">
                {doctor.is_verified ? (
                  <span className="text-emerald-700 font-bold flex items-center space-x-1 text-[11px]">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Verified against {doctor.state_council || 'Central Council'}</span>
                  </span>
                ) : (
                  <span className="text-amber-700 font-bold flex items-center space-x-1 text-[11px]">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                    <span>Unverified Dataset Seed (Doctor must submit credentials for +20 pts)</span>
                  </span>
                )}
              </div>
            </div>

            {/* 3. Experience */}
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-slate-800">3. Clinical Experience (Weight: 15%)</span>
                <span className="font-bold text-ayur-700">+{breakdown.experience?.contribution || '12.0'} pts</span>
              </div>
              <p className="text-[10px] text-slate-500">
                <strong>{doctor.experience_years} years</strong> of documented active Ayurvedic practice (benchmark 20 years = 100%).
              </p>
            </div>

            {/* 4. Completion & Response */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="font-semibold text-slate-800 block text-[11px]">Consult Completion (10%)</span>
                <span className="text-xs font-bold text-slate-900 mt-0.5 block">98% completed</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="font-semibold text-slate-800 block text-[11px]">Avg Response Time (10%)</span>
                <span className="text-xs font-bold text-slate-900 mt-0.5 block">&lt; 1.5 hours</span>
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full py-2.5 bg-ayur-800 hover:bg-ayur-900 text-white font-semibold rounded-xl transition"
          >
            Close Audit Breakdown
          </button>
        </div>
      </div>
    </div>
  );
};
