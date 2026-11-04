import React from 'react';
import { AlertOctagon, PhoneCall, ShieldAlert, X, HeartPulse, Stethoscope } from 'lucide-react';
import { TriageResult } from '../../types';

interface EmergencyModalProps {
  isOpen: boolean;
  onClose: () => void;
  triageData?: TriageResult | null;
}

export const EmergencyModal: React.FC<EmergencyModalProps> = ({ isOpen, onClose, triageData }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl max-w-xl w-full shadow-2xl border-4 border-red-500 overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Banner */}
        <div className="bg-gradient-to-r from-red-600 to-rose-700 p-6 text-white text-center relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white bg-black/20 hover:bg-black/30 p-1.5 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="w-16 h-16 rounded-full bg-white/20 mx-auto flex items-center justify-center mb-3">
            <AlertOctagon className="w-10 h-10 text-white animate-bounce" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">CRITICAL RED-FLAG TRIAGE ALERT</h2>
          <p className="text-sm text-red-100 mt-1 font-medium">
            Immediate Emergency Allopathic Care Required
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Emergency Hotlines */}
          <div className="grid grid-cols-2 gap-4">
            <a 
              href="tel:112"
              className="flex items-center justify-center space-x-3 bg-red-600 hover:bg-red-700 text-white p-4 rounded-xl shadow-md transition group"
            >
              <PhoneCall className="w-6 h-6 text-yellow-300 group-hover:scale-110 transition-transform" />
              <div className="text-left">
                <span className="text-xs uppercase tracking-wider text-red-100 font-bold">National Emergency</span>
                <p className="text-2xl font-black">112</p>
              </div>
            </a>

            <a 
              href="tel:108"
              className="flex items-center justify-center space-x-3 bg-amber-600 hover:bg-amber-700 text-white p-4 rounded-xl shadow-md transition group"
            >
              <HeartPulse className="w-6 h-6 text-yellow-200 group-hover:scale-110 transition-transform" />
              <div className="text-left">
                <span className="text-xs uppercase tracking-wider text-amber-100 font-bold">Ambulance Dispatch</span>
                <p className="text-2xl font-black">108</p>
              </div>
            </a>
          </div>

          {/* Triggered Reasons */}
          {triageData && triageData.matched_reasons.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <h4 className="text-xs font-bold text-red-900 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
                <ShieldAlert className="w-4 h-4 text-red-600" />
                <span>Triggered Clinical Rule Indicators</span>
              </h4>
              <ul className="space-y-1.5">
                {triageData.matched_reasons.map((reason, idx) => (
                  <li key={idx} className="text-xs text-red-800 flex items-start space-x-2">
                    <span className="text-red-500 font-bold">•</span>
                    <div>
                      <strong className="font-semibold">{reason.category}:</strong> {reason.advice}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Clinical Protocol Statement */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-700 space-y-2">
            <div className="flex items-center space-x-2 text-slate-900 font-bold">
              <Stethoscope className="w-4 h-4 text-ayur-600" />
              <span>AyurLLM Patient Safety Directive (Section B)</span>
            </div>
            <p>
              Classical Ayurvedic medicine excels in chronic systemic balance, metabolic rehabilitation, and preventive longevity. However, <strong>acute emergency symptoms</strong> (such as myocardial infarction, acute ischemic stroke, severe respiratory failure, or internal trauma) require immediate emergency room triage.
            </p>
            <p className="text-slate-500 italic">
              Automated shloka retrieval is paused for your safety until emergency clearance.
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold rounded-xl transition"
          >
            I Acknowledge and will Seek Immediate Care
          </button>
        </div>
      </div>
    </div>
  );
};
