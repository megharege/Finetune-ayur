import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Pill, 
  Sparkles, 
  BarChart3, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Calendar, 
  TrendingUp, 
  Package, 
  ShieldCheck, 
  Clock,
  Layers,
  Leaf
} from 'lucide-react';
import { 
  getPharmacyInventory, 
  getPanchakarmaTherapies, 
  bookPanchakarma, 
  getHospitalAnalytics, 
  getDoctors, 
  verifyDoctorAdmin 
} from '../api/client';
import { PharmacyItem, PanchakarmaTherapy, Doctor } from '../types';

export const HospitalERPPage: React.FC = () => {
  const [subTab, setSubTab] = useState<'pharmacy' | 'panchakarma' | 'analytics' | 'verification'>('pharmacy');
  
  // Pharmacy
  const [pharmacyItems, setPharmacyItems] = useState<PharmacyItem[]>([]);
  const [pharmacyCategory, setPharmacyCategory] = useState<string>('all');
  const [lowStockOnly, setLowStockOnly] = useState<boolean>(false);
  
  // Panchakarma
  const [therapies, setTherapies] = useState<PanchakarmaTherapy[]>([]);
  const [bookingTherapy, setBookingTherapy] = useState<PanchakarmaTherapy | null>(null);
  const [bookingDate, setBookingDate] = useState<string>('');
  
  // Analytics
  const [analytics, setAnalytics] = useState<any>(null);
  
  // Doctor Verification Queue
  const [doctorsList, setDoctorsList] = useState<Doctor[]>([]);

  useEffect(() => {
    getPharmacyInventory()
      .then((data) => setPharmacyItems(data))
      .catch((err) => console.error(err));

    getPanchakarmaTherapies()
      .then((data) => setTherapies(data))
      .catch((err) => console.error(err));

    getHospitalAnalytics()
      .then((data) => setAnalytics(data))
      .catch((err) => console.error(err));

    getDoctors()
      .then((data) => setDoctorsList(data))
      .catch((err) => console.error(err));
  }, []);

  const handleVerifyDoctor = async (docId: number, approved: boolean) => {
    try {
      await verifyDoctorAdmin(docId, approved);
      const updated = await getDoctors();
      setDoctorsList(updated);
      alert(approved ? 'Doctor verified and credential certified!' : 'Doctor verification rejected.');
    } catch (err) {
      console.error(err);
    }
  };

  const handleBookPanchakarmaSubmit = async () => {
    if (!bookingTherapy || !bookingDate) return;
    try {
      await bookPanchakarma({ therapy_id: bookingTherapy.id, start_date: new Date(bookingDate).toISOString() });
      alert(`Panchakarma booking confirmed for ${bookingTherapy.name}! Pre-procedure diet instructions dispatched.`);
      setBookingTherapy(null);
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
            <Building2 className="w-3.5 h-3.5 text-ayur-700" />
            <span>Ayurvedic Hospital ERP & Administration</span>
          </div>
          <h1 className="text-3xl font-display font-bold text-slate-900">
            Integrated Hospital Management Suite
          </h1>
          <p className="text-xs text-slate-500">
            Real-time management of Herbal Pharmacy stocks, Panchakarma schedules, Doctor credential audits, and clinical analytics.
          </p>
        </div>

        {/* Sub-tab Navigation */}
        <div className="bg-slate-100 p-1.5 rounded-xl flex space-x-1 text-xs font-semibold">
          <button
            onClick={() => setSubTab('pharmacy')}
            className={`px-3 py-2 rounded-lg transition ${
              subTab === 'pharmacy' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Herbal Pharmacy
          </button>
          <button
            onClick={() => setSubTab('panchakarma')}
            className={`px-3 py-2 rounded-lg transition ${
              subTab === 'panchakarma' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Panchakarma Studio
          </button>
          <button
            onClick={() => setSubTab('verification')}
            className={`px-3 py-2 rounded-lg transition ${
              subTab === 'verification' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Doctor Registry
          </button>
          <button
            onClick={() => setSubTab('analytics')}
            className={`px-3 py-2 rounded-lg transition ${
              subTab === 'analytics' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Clinical Analytics
          </button>
        </div>
      </div>

      {/* 1. Herbal Pharmacy Tab */}
      {subTab === 'pharmacy' && (
        <div className="space-y-6 animate-in fade-in">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Ayurvedic Pharmacy Stock Catalog</h3>
              <p className="text-xs text-slate-500">Formulated formulations tagged with classical textual authority</p>
            </div>

            <div className="flex items-center space-x-3 text-xs">
              <label className="flex items-center space-x-1.5 text-slate-700 font-semibold cursor-pointer bg-white px-3 py-1.5 rounded-lg border border-slate-200">
                <input
                  type="checkbox"
                  checked={lowStockOnly}
                  onChange={(e) => setLowStockOnly(e.target.checked)}
                  className="rounded accent-red-600"
                />
                <span>Show Low Stock Alerts Only</span>
              </label>
            </div>
          </div>

          <div className="overflow-x-auto bg-white rounded-2xl border border-slate-200 shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Formulation Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Classical Source</th>
                  <th className="py-3 px-4">Dosha Target</th>
                  <th className="py-3 px-4">Inventory Level</th>
                  <th className="py-3 px-4">Unit Price</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pharmacyItems
                  .filter((item) => (lowStockOnly ? item.is_low_stock : true))
                  .map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/60 transition">
                      <td className="py-3.5 px-4">
                        <strong className="text-slate-900 font-semibold block">{item.name}</strong>
                        <span className="text-[10px] text-slate-400 italic">{item.botanical_name}</span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-700 font-medium">{item.category}</td>
                      <td className="py-3.5 px-4 text-slate-600">{item.classical_text}</td>
                      <td className="py-3.5 px-4 font-semibold text-ayur-800">{item.dosha_affinity}</td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className={item.is_low_stock ? 'text-red-600 font-bold' : 'text-slate-800'}>
                          {item.stock_quantity} units
                        </span>
                        <span className="text-[10px] text-slate-400 block">Min: {item.reorder_level}</span>
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">₹{item.unit_price}</td>
                      <td className="py-3.5 px-4 text-right">
                        {item.is_low_stock ? (
                          <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-200">
                            <AlertTriangle className="w-3 h-3 text-red-600" />
                            <span>Reorder Needed</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>In Stock</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 2. Panchakarma Studio Tab */}
      {subTab === 'panchakarma' && (
        <div className="space-y-6 animate-in fade-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Panchakarma Detoxification & Rejuvenation</h3>
            <p className="text-xs text-slate-500">Comprehensive multi-day bio-purification protocols</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {therapies.map((t) => (
              <div
                key={t.id}
                className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-ayur-400 transition flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="text-base font-bold text-slate-900 font-display">{t.name}</h4>
                      <p className="font-sanskrit text-ayur-800 font-medium text-xs">{t.sanskrit_name}</p>
                    </div>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-gold-50 text-gold-800 border border-gold-200">
                      ₹{t.price}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">{t.description}</p>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Duration:</span>
                      <strong className="text-slate-800">{t.duration_days} Days Bio-Cycle</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Primary Target Dosha:</span>
                      <strong className="text-rose-700">{t.target_dosha}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Clinical Referral:</span>
                      <strong className="text-slate-800">{t.requires_doctor_referral ? 'Mandatory Vaidya Assessment' : 'Open Registration'}</strong>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-600">
                    <strong className="text-slate-800">Key Clinical Benefits:</strong> {t.benefits}
                  </div>
                </div>

                <button
                  onClick={() => setBookingTherapy(t)}
                  className="w-full py-2.5 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl text-xs font-bold transition shadow-xs flex items-center justify-center space-x-1.5"
                >
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Reserve Therapy Program</span>
                </button>
              </div>
            ))}
          </div>

          {/* Panchakarma Booking Modal */}
          {bookingTherapy && (
            <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 text-xs">
                <div className="border-b border-slate-100 pb-3">
                  <h3 className="text-base font-bold text-slate-900">{bookingTherapy.name}</h3>
                  <p className="text-slate-500">{bookingTherapy.duration_days} Days Purification Cycle • ₹{bookingTherapy.price}</p>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Select Commencement Date</label>
                  <input
                    type="date"
                    value={bookingDate}
                    onChange={(e) => setBookingDate(e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-xl outline-none"
                  />
                </div>

                <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl text-amber-900">
                  <p className="font-semibold">Pre-Panchakarma Protocol:</p>
                  <p className="text-[11px] mt-0.5">Includes preliminary Snehana (internal oleation with medicated ghee) and Swedana (sudation) prior to primary procedure.</p>
                </div>

                <div className="flex space-x-2 pt-2">
                  <button
                    onClick={() => setBookingTherapy(null)}
                    className="w-1/2 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleBookPanchakarmaSubmit}
                    disabled={!bookingDate}
                    className="w-1/2 py-2.5 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl font-bold transition disabled:opacity-50"
                  >
                    Confirm Booking
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. Doctor Verification Registry Queue Tab */}
      {subTab === 'verification' && (
        <div className="space-y-6 animate-in fade-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Central Council Practitioner Verification Queue</h3>
            <p className="text-xs text-slate-500">
              Audit doctors claiming profiles from the Kaggle dataset against official state and national registry certificates.
            </p>
          </div>

          <div className="space-y-3">
            {doctorsList.map((doc) => (
              <div
                key={doc.id}
                className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
              >
                <div className="flex items-center space-x-3">
                  <img
                    src={doc.avatar_url || 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=120&auto=format&fit=crop&q=80'}
                    alt={doc.name}
                    className="w-10 h-10 rounded-xl object-cover"
                  />
                  <div>
                    <h4 className="font-bold text-slate-900 text-sm">{doc.name}</h4>
                    <p className="text-slate-500">{doc.qualification} • {doc.specialty}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                      Reg: {doc.registration_number || 'PENDING'} | Council: {doc.state_council || 'State Board'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Trust Score</span>
                    <span className="font-bold text-slate-900 text-sm">{doc.trust_score} / 100</span>
                  </div>

                  {doc.is_verified ? (
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-lg font-bold flex items-center space-x-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Certified</span>
                    </span>
                  ) : (
                    <div className="flex items-center space-x-1.5">
                      <button
                        onClick={() => handleVerifyDoctor(doc.id, true)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold transition flex items-center space-x-1"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>Approve & Certify</span>
                      </button>
                      <button
                        onClick={() => handleVerifyDoctor(doc.id, false)}
                        className="px-2.5 py-1.5 bg-slate-100 hover:bg-red-50 text-slate-600 hover:text-red-600 rounded-lg font-semibold transition"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Analytics Tab */}
      {subTab === 'analytics' && analytics && (
        <div className="space-y-6 animate-in fade-in">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Hospital Administrative Intelligence</h3>
            <p className="text-xs text-slate-500">Live metrics across consultations, dosha epidemiology, and pharmacy turns</p>
          </div>

          {/* KPI Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Verified Doctor Network</span>
              <span className="text-2xl font-black text-slate-900 mt-1 block">{analytics.kpis.verification_rate}</span>
              <span className="text-[10px] text-slate-500">{analytics.kpis.verified_doctors} of {analytics.kpis.total_doctors} certified</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Total Teleconsultations</span>
              <span className="text-2xl font-black text-slate-900 mt-1 block">{analytics.kpis.total_consultations}</span>
              <span className="text-[10px] text-emerald-600 font-semibold">{analytics.kpis.completed_teleconsults} completed</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Pharmacy SKUs</span>
              <span className="text-2xl font-black text-slate-900 mt-1 block">{analytics.kpis.pharmacy_skus}</span>
              <span className="text-[10px] text-amber-600 font-semibold">{analytics.kpis.low_stock_reorders} low stock alerts</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Gross Telehealth Revenue</span>
              <span className="text-2xl font-black text-ayur-900 mt-1 block font-mono">₹{analytics.kpis.total_revenue_inr.toLocaleString()}</span>
              <span className="text-[10px] text-slate-500">Razorpay settlements</span>
            </div>
          </div>

          {/* Dosha Epidemiology Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h4 className="font-bold text-slate-900 text-sm">Presenting Dosha Imbalance Epidemiology (Vitiation Distribution)</h4>
            <div className="space-y-3">
              {analytics.dosha_distribution.map((d: any) => (
                <div key={d.dosha} className="text-xs">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-800">{d.dosha} ({d.cases} cases)</span>
                    <span className="font-bold">{d.percentage}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${d.percentage}%`, backgroundColor: d.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
