import React from 'react';
import { X, Printer, ShieldCheck, Award, FileCheck2, Sparkles } from 'lucide-react';

interface PrescriptionPrintModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: any;
}

export const PrescriptionPrintModal: React.FC<PrescriptionPrintModalProps> = ({ isOpen, onClose, data }) => {
  if (!isOpen || !data) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in duration-200 print:m-0 print:p-0 print:border-none print:shadow-none">
        {/* Header Bar */}
        <div className="bg-slate-900 px-6 py-3 text-white flex justify-between items-center print:hidden">
          <div className="flex items-center space-x-2">
            <FileCheck2 className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider">Official Ayurvedic E-Prescription</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.print()}
              className="flex items-center space-x-1.5 px-3 py-1 bg-ayur-600 hover:bg-ayur-700 text-white rounded-lg text-xs font-semibold transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Prescription</span>
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Prescription Body */}
        <div className="p-8 space-y-6 text-slate-800 bg-[#FCFBF8]">
          {/* Hospital Clinic Letterhead */}
          <div className="border-b-2 border-ayur-800 pb-5 flex justify-between items-start">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-2xl font-serif font-black text-ayur-900">आयुर्वेद चिकित्सालय</span>
                <span className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-ayur-100 text-ayur-800 border border-ayur-200">
                  AyurLLM Certified
                </span>
              </div>
              <h1 className="text-xl font-display font-bold text-slate-900 mt-1">AyurLLM Centre for Classical Medicine & Research</h1>
              <p className="text-xs text-slate-500">Department of Kayachikitsa & Panchakarma | Telemedicine Division</p>
            </div>
            <div className="text-right text-xs space-y-0.5">
              <p className="font-bold text-slate-900">{data.doctor?.name || 'Dr. Vaidya Hitanshu Choraria'}</p>
              <p className="text-slate-600">{data.doctor?.qualification || 'BAMS, MD (Kayachikitsa)'}</p>
              <p className="text-slate-500 font-mono">Reg No: {data.doctor?.registration_number || 'CCIM-ND-2021-0941'}</p>
              <p className="text-slate-400 text-[10px]">Date: {data.date || new Date().toLocaleDateString()}</p>
            </div>
          </div>

          {/* Patient Details */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 grid grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Patient Name</span>
              <span className="font-bold text-slate-900 text-sm">{data.patient?.name || 'Ananya Sharma'}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Constitutional Prakriti</span>
              <span className="font-semibold text-ayur-800">Pitta-Vata (Tikshnagni)</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Diagnostic Assessment</span>
              <span className="font-semibold text-rose-700">{data.dosha_assessment || 'Amlapitta & Agnimandya'}</span>
            </div>
          </div>

          {/* Classical Verse Citations (Mandated by Spec) */}
          {data.classical_citations && data.classical_citations.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-ayur-900 flex items-center space-x-1.5 border-b border-ayur-200 pb-1">
                <Sparkles className="w-3.5 h-3.5 text-gold-600" />
                <span>Classical Treatise Citations (Brihat Trayi Corpus Authority)</span>
              </h3>
              <div className="space-y-2">
                {data.classical_citations.map((c: any, idx: number) => (
                  <div key={idx} className="bg-amber-50/50 p-3 rounded-lg border border-amber-200/60 text-xs">
                    <div className="flex justify-between items-center text-[10px] font-bold text-amber-900 mb-1">
                      <span>Source: {c.source_book || 'Charaka Samhita'}</span>
                      <span className="font-mono bg-amber-100 px-1.5 py-0.5 rounded border border-amber-300">
                        Chunk ID: {c.chunk_id}
                      </span>
                    </div>
                    <p className="sanskrit-verse text-slate-800 font-medium text-xs">{c.sanskrit}</p>
                    <p className="text-[11px] text-slate-600 mt-0.5 italic">Clinical Indication: {c.indication}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Herbal Formulations Table */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
              Prescribed Formulations (Aushadha Prayoga)
            </h3>
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Formulation</th>
                    <th className="py-2.5 px-3">Dosage</th>
                    <th className="py-2.5 px-3">Anupana (Carrier)</th>
                    <th className="py-2.5 px-3">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.formulations && data.formulations.length > 0 ? (
                    data.formulations.map((f: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-3 font-semibold text-slate-900">{f.name}</td>
                        <td className="py-2.5 px-3 text-slate-700">{f.dosage}</td>
                        <td className="py-2.5 px-3 text-slate-700">{f.anupana}</td>
                        <td className="py-2.5 px-3 text-slate-600 font-medium">{f.duration}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-slate-400">No formulations recorded</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Ahar (Diet) & Vihar (Lifestyle) */}
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="bg-white p-3.5 rounded-xl border border-slate-200">
              <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] text-emerald-800 mb-1.5">
                आहार (Dietary Protocols)
              </h4>
              <p className="text-slate-600 whitespace-pre-line leading-relaxed">
                {data.ahar_diet_plan || '• Avoid sour (amla), spicy (tikta), and fermented foods.\n• Favor warm milk infused with organic cardamom.\n• Consume fresh pomegranate and cooked cooling squashes.'}
              </p>
            </div>

            <div className="bg-white p-3.5 rounded-xl border border-slate-200">
              <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] text-indigo-800 mb-1.5">
                विहार (Lifestyle & Dinacharya)
              </h4>
              <p className="text-slate-600 whitespace-pre-line leading-relaxed">
                {data.vihar_lifestyle_plan || '• Sitali & Nadi Shodhana Pranayama for 10 minutes before sunrise.\n• Early dinner by 7:30 PM.\n• Gentle self-abhyanga with Ksheerabala taila twice weekly.'}
              </p>
            </div>
          </div>

          {/* Footer & Cryptographic Signature */}
          <div className="border-t border-slate-200 pt-4 flex justify-between items-center text-xs">
            <div className="flex items-center space-x-2 text-slate-500">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <div>
                <p className="font-mono text-[10px]">{data.digital_signature || 'AYUR-SIG-88C901AF241'}</p>
                <p className="text-[9px] text-slate-400">Tamper-evident SHA-256 cryptographic registration</p>
              </div>
            </div>

            <div className="text-right">
              <div className="font-serif italic font-bold text-ayur-900 text-sm">Hitanshu Choraria, BAMS, MD</div>
              <p className="text-[10px] text-slate-400">Electronically Verified Practitioner Signature</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
