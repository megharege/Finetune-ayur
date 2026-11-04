import React, { useState, useEffect } from 'react';
import { 
  Video, 
  Mic, 
  MicOff, 
  VideoOff, 
  PhoneOff, 
  MessageSquare, 
  FileEdit, 
  Network, 
  Send, 
  Sparkles, 
  Plus, 
  Trash2, 
  FileCheck2,
  Lock,
  User,
  ShieldCheck,
  Award
} from 'lucide-react';
import { getConsultation, getConsultationGraph, createPrescription } from '../api/client';
import { KnowledgeGraphData } from '../types';
import { KnowledgeGraphView } from '../components/graph/KnowledgeGraphView';
import { PrescriptionPrintModal } from '../components/prescription/PrescriptionPrintModal';

interface ConsultationRoomPageProps {
  consultationId?: number;
  roomId?: string;
}

export const ConsultationRoomPage: React.FC<ConsultationRoomPageProps> = ({ 
  consultationId = 1,
  roomId = 'ayur-consult-live-101'
}) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'notes' | 'prescription'>('graph');
  const [consultData, setConsultData] = useState<any>(null);
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null);

  // AV controls
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVideoOn, setIsVideoOn] = useState(true);

  // Chat
  const [chatMessages, setChatMessages] = useState<Array<{ sender: string; text: string; time: string }>>([
    { sender: 'Dr. Vaidya Hitanshu', text: 'Namaste Ananya ji. Welcome to the AyurLLM Consultation Room. How may I assist you today?', time: '10:02 AM' },
    { sender: 'Patient', text: 'Namaste Doctor. I have been suffering from recurrent acid reflux and restlessness at night for the past 2 weeks.', time: '10:03 AM' }
  ]);
  const [newMessage, setNewMessage] = useState('');

  // Clinical Notes
  const [clinicalNotes, setClinicalNotes] = useState(
    'Patient exhibits secondary Pitta vitiation manifesting as Amlapitta (hyperacidity) and Tikshnagni. Sleep latency is impaired by Vata disturbance. Pulse (Nadi): Pitta-dominant, rapid.'
  );

  // E-Prescription Form State
  const [formulations, setFormulations] = useState([
    { name: 'Triphala Churna', dosage: '3g with warm water', anupana: 'Warm water at bedtime', duration: '14 days' },
    { name: 'Ashwagandharishta', dosage: '15ml twice daily after meals', anupana: 'Equal quantity of water', duration: '21 days' }
  ]);
  const [newFormulation, setNewFormulation] = useState({ name: '', dosage: '', anupana: '', duration: '' });
  const [aharPlan, setAharPlan] = useState('• Avoid sour (amla), excessively pungent (katu), and stale foods.\n• Favor fresh pomegranate, cooling mung soup, and soaked almonds.\n• Dinner before 7:30 PM.');
  const [viharPlan, setViharPlan] = useState('• Practice Sitali and Bhramari Pranayama 10 minutes before bed.\n• Walk 15 minutes after light meals.\n• Avoid screen exposure after 9:30 PM.');
  
  // Printable modal
  const [savedPrescription, setSavedPrescription] = useState<any>(null);
  const [showPrintModal, setShowPrintModal] = useState(false);
  const [prescribeLoading, setPrescribeLoading] = useState(false);

  useEffect(() => {
    getConsultation(consultationId)
      .then((res) => setConsultData(res))
      .catch((err) => console.error(err));

    getConsultationGraph(consultationId)
      .then((res) => setGraphData(res))
      .catch((err) => console.error(err));
  }, [consultationId]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (newMessage.trim()) {
      setChatMessages([
        ...chatMessages,
        { sender: 'Dr. Vaidya Hitanshu', text: newMessage.trim(), time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      ]);
      setNewMessage('');
    }
  };

  const handleAddFormulation = () => {
    if (newFormulation.name.trim()) {
      setFormulations([...formulations, newFormulation]);
      setNewFormulation({ name: '', dosage: '', anupana: '', duration: '' });
    }
  };

  const handleSavePrescription = async () => {
    setPrescribeLoading(true);
    try {
      const payload = {
        consultation_id: consultationId,
        patient_id: consultData?.patient?.id || 1,
        classical_citations: [
          {
            chunk_id: 'CS-SU-01-042',
            source_book: 'Charaka Samhita',
            sanskrit: 'सर्वदा सर्वभावानां सामान्यं वृद्धि Barbaram । ह्रासहेतुर्विशेषश्च प्रवृत्तिरुभयस्य तु ॥',
            indication: 'Samanya-Vishesha Siddhanta in metabolic Pitta-Vata harmonization'
          },
          {
            chunk_id: 'SH-MK-02-015',
            source_book: 'Sharangadhara Samhita',
            sanskrit: 'हरीतकी विभीतकश्चामलकं त्रिफलोच्यते । त्रिफला कफपित्तघ्नी मेहकुष्ठहरा सरा ॥',
            indication: 'Triphala formulation for mild gut purgation and Amlapitta cure'
          }
        ],
        formulations: formulations,
        ahar_diet_plan: aharPlan,
        vihar_lifestyle_plan: viharPlan,
        follow_up_advice: 'Review after 14 days or earlier if symptom aggravation occurs.',
        dosha_assessment: 'Pitta-Vata Prakopa (Amlapitta & Anidra)'
      };

      const res = await createPrescription(payload);
      setSavedPrescription({
        ...payload,
        id: res.prescription_id,
        digital_signature: res.digital_signature,
        date: new Date().toLocaleDateString(),
        doctor: consultData?.doctor,
        patient: consultData?.patient
      });
      setShowPrintModal(true);
    } catch (err) {
      console.error(err);
    } finally {
      setPrescribeLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center text-red-600">
            <Video className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900">AyurLLM Secure Teleconsultation Suite</h2>
              <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full border border-emerald-200 flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping" />
                <span>Live Encrypted Session</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono">Room: {roomId} | Peer WebRTC Signalling: Connected</p>
          </div>
        </div>

        {/* Patient header chip */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="text-right">
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Patient</span>
            <span className="font-bold text-slate-800">{consultData?.patient?.name || 'Ananya Sharma'}</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-ayur-100 border border-ayur-300 flex items-center justify-center text-ayur-900 font-bold">
            AS
          </div>
        </div>
      </div>

      {/* Main Grid: Video Stream + Clinical Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Video Feeds & Live Chat (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Main Video Box */}
          <div className="relative bg-slate-950 rounded-2xl overflow-hidden aspect-video shadow-md border border-slate-800 flex items-center justify-center">
            {isVideoOn ? (
              <img
                src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&auto=format&fit=crop&q=80"
                alt="Patient Video"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="text-center text-slate-500">
                <User className="w-16 h-16 mx-auto mb-2 opacity-40" />
                <p className="text-xs">Patient Video Paused</p>
              </div>
            )}

            {/* Doctor PIP preview */}
            <div className="absolute bottom-3 right-3 w-28 h-20 bg-slate-900 rounded-xl overflow-hidden border-2 border-white/20 shadow-lg">
              <img
                src="https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=300&auto=format&fit=crop&q=80"
                alt="Doctor Video"
                className="w-full h-full object-cover"
              />
              <span className="absolute bottom-1 left-1.5 text-[8px] bg-black/60 text-white px-1 rounded font-bold">
                You (Vaidya)
              </span>
            </div>

            {/* In-Call Controls Overlay */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center space-x-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <button
                onClick={() => setIsMicOn(!isMicOn)}
                className={`p-2 rounded-full transition ${isMicOn ? 'bg-white/20 text-white hover:bg-white/30' : 'bg-red-600 text-white'}`}
                title={isMicOn ? 'Mute Mic' : 'Unmute Mic'}
              >
                {isMicOn ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setIsVideoOn(!isVideoOn)}
                className={`p-2 rounded-full transition ${isVideoOn ? 'bg-white/20 text-white hover:bg-white/30' : 'bg-red-600 text-white'}`}
                title={isVideoOn ? 'Turn Camera Off' : 'Turn Camera On'}
              >
                {isVideoOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
              </button>
              <button
                onClick={() => alert('Call session ended')}
                className="p-2 rounded-full bg-red-600 hover:bg-red-700 text-white transition"
                title="End Consultation"
              >
                <PhoneOff className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Live Chat Panel */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs flex flex-col h-[380px]">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center space-x-2 text-xs font-bold text-slate-800">
              <MessageSquare className="w-4 h-4 text-ayur-700" />
              <span>Real-Time Clinical Consultation Chat</span>
            </div>

            {/* Message List */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs">
              {chatMessages.map((msg, i) => {
                const isDoc = msg.sender.includes('Vaidya') || msg.sender.includes('Hitanshu');
                return (
                  <div key={i} className={`flex flex-col ${isDoc ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] text-slate-400 mb-0.5">{msg.sender} • {msg.time}</span>
                    <div
                      className={`max-w-[85%] p-2.5 rounded-2xl ${
                        isDoc
                          ? 'bg-ayur-800 text-white rounded-tr-xs'
                          : 'bg-slate-100 text-slate-800 rounded-tl-xs'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSendMessage} className="p-2.5 border-t border-slate-200 flex space-x-2 bg-white">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type clinical observation or advice..."
                className="flex-1 text-xs px-3 py-2 border border-slate-200 rounded-xl outline-none focus:border-ayur-500"
              />
              <button
                type="submit"
                className="p-2 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl transition"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Doctor Workspace (Graph, Notes, Prescription Generator) (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Workspace Tabs */}
          <div className="bg-white p-1.5 rounded-2xl border border-slate-200 shadow-xs flex space-x-2 text-xs font-bold">
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex-1 py-2.5 rounded-xl transition flex items-center justify-center space-x-1.5 ${
                activeTab === 'graph'
                  ? 'bg-ayur-800 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Network className="w-4 h-4" />
              <span>Neo4j Patient Knowledge Graph</span>
            </button>

            <button
              onClick={() => setActiveTab('notes')}
              className={`flex-1 py-2.5 rounded-xl transition flex items-center justify-center space-x-1.5 ${
                activeTab === 'notes'
                  ? 'bg-ayur-800 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <FileEdit className="w-4 h-4" />
              <span>Doctor Clinical Notes</span>
            </button>

            <button
              onClick={() => setActiveTab('prescription')}
              className={`flex-1 py-2.5 rounded-xl transition flex items-center justify-center space-x-1.5 ${
                activeTab === 'prescription'
                  ? 'bg-ayur-800 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <FileCheck2 className="w-4 h-4" />
              <span>Generate E-Prescription</span>
            </button>
          </div>

          {/* Active Tab Content */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 min-h-[500px]">
            {activeTab === 'graph' && (
              <div className="space-y-4 animate-in fade-in">
                <div className="flex justify-between items-center text-xs">
                  <div>
                    <h3 className="font-bold text-slate-900">Patient-Symptom-Dosha-Shloka Graph</h3>
                    <p className="text-[11px] text-slate-500">Live Neo4j graph model: Doctor sees it only during active consultation</p>
                  </div>
                  <span className="text-[10px] font-mono bg-ayur-50 text-ayur-800 px-2 py-0.5 rounded border border-ayur-200 font-bold">
                    Telemetry: Synchronized
                  </span>
                </div>
                <KnowledgeGraphView data={graphData} height={420} />
              </div>
            )}

            {activeTab === 'notes' && (
              <div className="space-y-4 animate-in fade-in">
                <div className="flex justify-between items-center text-xs">
                  <div>
                    <h3 className="font-bold text-slate-900">Clinical Case Sheet & Examination</h3>
                    <p className="text-[11px] text-slate-500">Nadi Pariksha, Dosha assessment, and differential diagnosis</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Constitutional Prakriti</span>
                    <span className="font-bold text-ayur-900 text-sm">Pitta-Vata (Tikshnagni)</span>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Nadi Pariksha Findings</span>
                    <span className="font-bold text-rose-800 text-sm">Manduka Gati (Rapid Pitta)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Physician's Progress Notes
                  </label>
                  <textarea
                    value={clinicalNotes}
                    onChange={(e) => setClinicalNotes(e.target.value)}
                    rows={8}
                    className="w-full text-xs p-3.5 rounded-xl border border-slate-200 focus:border-ayur-500 outline-none leading-relaxed"
                  />
                </div>

                <button
                  type="button"
                  onClick={() => alert('Clinical case sheet saved.')}
                  className="px-5 py-2.5 bg-ayur-800 hover:bg-ayur-900 text-white rounded-xl text-xs font-bold transition shadow-xs"
                >
                  Save Case Notes
                </button>
              </div>
            )}

            {activeTab === 'prescription' && (
              <div className="space-y-5 animate-in fade-in">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Digital E-Prescription Composer</h3>
                    <p className="text-[11px] text-slate-500">Every formulation citations must link to validated classical chunks</p>
                  </div>
                  <span className="text-xs font-bold text-ayur-700 bg-ayur-50 px-2.5 py-1 rounded-lg border border-ayur-200">
                    Certified Practitioner Portal
                  </span>
                </div>

                {/* Formulations list */}
                <div className="space-y-3">
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                    Formulations (Aushadha)
                  </span>
                  <div className="space-y-2">
                    {formulations.map((f, i) => (
                      <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex justify-between items-center text-xs">
                        <div>
                          <strong className="text-slate-900 font-semibold">{f.name}</strong>
                          <span className="text-slate-500 ml-2">({f.dosage} • {f.anupana} • {f.duration})</span>
                        </div>
                        <button
                          onClick={() => setFormulations(formulations.filter((_, idx) => idx !== i))}
                          className="text-red-500 hover:text-red-700 p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Add formulation input row */}
                  <div className="grid grid-cols-4 gap-2 pt-1 text-xs">
                    <input
                      type="text"
                      placeholder="Herb / Churna name"
                      value={newFormulation.name}
                      onChange={(e) => setNewFormulation({ ...newFormulation, name: e.target.value })}
                      className="p-2 border border-slate-200 rounded-lg outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Dosage (e.g. 3g twice daily)"
                      value={newFormulation.dosage}
                      onChange={(e) => setNewFormulation({ ...newFormulation, dosage: e.target.value })}
                      className="p-2 border border-slate-200 rounded-lg outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Anupana (e.g. Warm water)"
                      value={newFormulation.anupana}
                      onChange={(e) => setNewFormulation({ ...newFormulation, anupana: e.target.value })}
                      className="p-2 border border-slate-200 rounded-lg outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleAddFormulation}
                      className="bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-lg px-3 py-2 flex items-center justify-center space-x-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Herb</span>
                    </button>
                  </div>
                </div>

                {/* Ahar & Vihar Plans */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block font-bold text-slate-800 mb-1">आहार (Dietary Plan)</label>
                    <textarea
                      value={aharPlan}
                      onChange={(e) => setAharPlan(e.target.value)}
                      rows={3}
                      className="w-full p-2.5 rounded-xl border border-slate-200 outline-none leading-relaxed"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-800 mb-1">विहार (Lifestyle & Dinacharya)</label>
                    <textarea
                      value={viharPlan}
                      onChange={(e) => setViharPlan(e.target.value)}
                      rows={3}
                      className="w-full p-2.5 rounded-xl border border-slate-200 outline-none leading-relaxed"
                    />
                  </div>
                </div>

                {/* Final Issue Prescription Button */}
                <button
                  type="button"
                  onClick={handleSavePrescription}
                  disabled={prescribeLoading}
                  className="w-full py-3.5 bg-gradient-to-r from-ayur-800 to-ayur-900 hover:from-ayur-900 hover:to-ayur-950 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center justify-center space-x-2"
                >
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>{prescribeLoading ? 'Signing & Stamping Prescription...' : 'Digitally Sign & Issue E-Prescription (with Citations)'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Printable Modal */}
      <PrescriptionPrintModal
        isOpen={showPrintModal}
        onClose={() => setShowPrintModal(false)}
        data={savedPrescription}
      />
    </div>
  );
};
