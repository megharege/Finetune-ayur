import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Calendar, 
  Sparkles, 
  Clock, 
  Printer, 
  Bell, 
  CheckCircle2, 
  ShieldCheck, 
  Heart, 
  User 
} from 'lucide-react';
import { getPatientPrescriptions, getPrescription } from '../api/client';
import { PrescriptionPrintModal } from '../components/prescription/PrescriptionPrintModal';

export const PatientPortalPage: React.FC = () => {
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [selectedRx, setSelectedRx] = useState<any>(null);
  const [showPrintModal, setShowPrintModal] = useState(false);

  useEffect(() => {
    getPatientPrescriptions(1)
      .then((data) => {
        setPrescriptions(data || []);
      })
      .catch((err) => console.error(err));
  }, []);

  const handleOpenPrescription = async (id: number) => {
    try {
      const fullRx = await getPrescription(id);
      setSelectedRx(fullRx);
      setShowPrintModal(true);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="inline-flex items-center space-x-2 bg-ayur-100 text-ayur-900 text-xs font-bold px-3 py-1 rounded-full mb-1">
            <User className="w-3.5 h-3.5 text-ayur-700" />
            <span>Step 10: Patient Health Records & Follow-Up Reminders</span>
          </div>
          <h1 className="text-3xl font-display font-bold text-slate-900">
            Personal Ayurvedic Health Portal (EHR)
          </h1>
          <p className="text-xs text-slate-500">
            Digitally signed clinical prescriptions, Prakriti balance tracking, and dietary adherence timeline.
          </p>
        </div>

        {/* Patient Profile Card */}
        <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-xs flex items-center space-x-3 text-xs">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ayur-800 to-ayur-600 text-white font-bold flex items-center justify-center">
            AS
          </div>
          <div>
            <h4 className="font-bold text-slate-900">Ananya Sharma</h4>
            <span className="text-[10px] text-ayur-700 font-semibold bg-ayur-50 px-2 py-0.5 rounded border border-ayur-200">
              Prakriti: Pitta-Vata (Tikshnagni)
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Prescriptions & Care Plan (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
                <FileText className="w-4 h-4 text-ayur-700" />
                <span>Verified E-Prescriptions & Formulation Regimens</span>
              </h3>
              <span className="text-xs text-slate-500">Encrypted Clinical Records</span>
            </div>

            {prescriptions.length > 0 ? (
              <div className="space-y-3">
                {prescriptions.map((rx) => (
                  <div
                    key={rx.id}
                    className="p-4 rounded-xl border border-slate-200 hover:border-ayur-300 transition bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900 text-sm">{rx.doctor_name}</span>
                        <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-500">
                          {rx.signature}
                        </span>
                      </div>
                      <p className="text-slate-500">
                        Date: {rx.date} • {rx.formulations_count} Classical Formulations • {rx.citations_count} Brihat Trayi Citations
                      </p>
                      <p className="text-[11px] text-slate-600 italic">
                        Diet: {rx.ahar_diet_preview}
                      </p>
                    </div>

                    <button
                      onClick={() => handleOpenPrescription(rx.id)}
                      className="px-4 py-2 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl font-bold transition flex items-center justify-center space-x-1.5 shrink-0 shadow-xs"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      <span>View & Print</span>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              /* Fallback preview sample prescription */
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900 text-sm">Dr. Vaidya Hitanshu Choraria</span>
                    <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-500">
                      AYUR-SIG-88C901AF241
                    </span>
                  </div>
                  <p className="text-slate-500">
                    Date: Today • 2 Formulations (Triphala & Ashwagandha) • 2 Brihat Trayi Citations
                  </p>
                  <p className="text-[11px] text-slate-600 italic">
                    Diet: Cooling Pitta-Shamaka diet, avoiding sour and pungent condiments.
                  </p>
                </div>

                <button
                  onClick={() => {
                    setSelectedRx({
                      id: 1,
                      date: new Date().toLocaleDateString(),
                      digital_signature: 'AYUR-SIG-88C901AF241',
                      doctor: {
                        name: 'Dr. Vaidya Hitanshu Choraria',
                        registration_number: 'CCIM-ND-2021-0941',
                        qualification: 'BAMS, MD (Kayachikitsa)'
                      },
                      patient: { name: 'Ananya Sharma' },
                      classical_citations: [
                        {
                          chunk_id: 'CS-SU-01-042',
                          source_book: 'Charaka Samhita',
                          sanskrit: 'सर्वदा सर्वभावानां सामान्यं वृद्धि Barbaram । ह्रासहेतुर्विशेषश्च प्रवृत्तिरुभयस्य तु ॥',
                          indication: 'Samanya-Vishesha Siddhanta in metabolic balancing'
                        }
                      ],
                      formulations: [
                        { name: 'Triphala Churna', dosage: '3g with warm water', anupana: 'Warm water', duration: '14 days' },
                        { name: 'Ashwagandharishta', dosage: '15ml twice daily', anupana: 'Equal quantity of water', duration: '21 days' }
                      ],
                      ahar_diet_plan: '• Avoid sour (amla) and deeply fried items.\n• Favor pomegranate, cooling mung soup, and sweet ripe fruits.',
                      vihar_lifestyle_plan: '• Pranayama (Sitali) before bed.\n• Walk 15 minutes post-dinner.',
                      follow_up_advice: 'Review teleconsult in 14 days.'
                    });
                    setShowPrintModal(true);
                  }}
                  className="px-4 py-2 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl font-bold transition flex items-center justify-center space-x-1.5 shrink-0 shadow-xs"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>View & Print</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Daily Adherence Timeline & Reminders (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2 border-b border-slate-100 pb-2">
              <Bell className="w-4 h-4 text-gold-600" />
              <span>Step 10: Dinacharya & Dose Reminders</span>
            </h3>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200 flex items-start space-x-2.5">
                <Clock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-amber-900 block font-semibold">Morning Dinacharya (7:00 AM)</strong>
                  <p className="text-slate-600 text-[11px] mt-0.5">Sitali Pranayama (10 mins) + 1 glass of copper-charged water.</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 flex items-start space-x-2.5">
                <Clock className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-emerald-900 block font-semibold">Post-Lunch Formulation (1:30 PM)</strong>
                  <p className="text-slate-600 text-[11px] mt-0.5">Ashwagandharishta (15ml) mixed with 15ml warm water.</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-indigo-50/60 border border-indigo-200 flex items-start space-x-2.5">
                <Clock className="w-4 h-4 text-indigo-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-indigo-900 block font-semibold">Bedtime Formulation (9:30 PM)</strong>
                  <p className="text-slate-600 text-[11px] mt-0.5">Triphala Churna (3g) with 1 cup warm water.</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-slate-500">
              <span className="font-bold text-slate-700 block mb-0.5">Doctor Review Scheduled</span>
              <span>Follow-up teleconsultation due in <strong>12 days</strong>. Automatic WhatsApp & SMS reminders enabled.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Printable Modal */}
      <PrescriptionPrintModal
        isOpen={showPrintModal}
        onClose={() => setShowPrintModal(false)}
        data={selectedRx}
      />
    </div>
  );
};
