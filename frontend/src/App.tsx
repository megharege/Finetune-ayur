import React, { useState } from 'react';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/layout/Navbar';
import { EmergencyModal } from './components/triage/EmergencyModal';

// Pages
import { HomePage } from './pages/HomePage';
import { ShlokaExplorer } from './pages/ShlokaExplorer';
import { IntakePage } from './pages/IntakePage';
import { DoctorsPage } from './pages/DoctorsPage';
import { ConsultationRoomPage } from './pages/ConsultationRoomPage';
import { HospitalERPPage } from './pages/HospitalERPPage';
import { PatientPortalPage } from './pages/PatientPortalPage';
import { Doctor } from './types';

export const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('home');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [activeAppointment, setActiveAppointment] = useState<{ id: number; roomId: string } | null>(null);
  const [isEmergencyOpen, setIsEmergencyOpen] = useState(false);

  const handleBookSuccess = (appointmentId: number, roomId: string) => {
    setActiveAppointment({ id: appointmentId, roomId });
    setActiveTab('consult');
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] flex flex-col justify-between text-slate-800">
      <div>
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          onOpenEmergency={() => setIsEmergencyOpen(true)}
        />

        <main>
          {activeTab === 'home' && (
            <HomePage 
              setActiveTab={setActiveTab} 
              onSearchQuery={(q) => setSearchQuery(q)} 
            />
          )}

          {activeTab === 'explorer' && (
            <ShlokaExplorer initialQuery={searchQuery} />
          )}

          {activeTab === 'intake' && (
            <IntakePage 
              setActiveTab={setActiveTab} 
              onSelectDoctor={(doc) => setSelectedDoctor(doc)} 
            />
          )}

          {activeTab === 'doctors' && (
            <DoctorsPage 
              selectedDoctor={selectedDoctor} 
              onBookSuccess={handleBookSuccess} 
            />
          )}

          {activeTab === 'consult' && (
            <ConsultationRoomPage 
              consultationId={1} 
              roomId={activeAppointment?.roomId || 'ayur-consult-live-101'} 
            />
          )}

          {activeTab === 'hospital' && (
            <HospitalERPPage />
          )}

          {activeTab === 'portal' && (
            <PatientPortalPage />
          )}
        </main>
      </div>

      {/* Emergency Modal */}
      <EmergencyModal 
        isOpen={isEmergencyOpen} 
        onClose={() => setIsEmergencyOpen(false)} 
      />

      {/* Footer */}
      <footer className="bg-ayur-950 text-white border-t border-ayur-900 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-xs text-ayur-200">
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <span className="font-serif font-bold text-xl text-gold-300">आयुर्वेद</span>
                <span className="font-display font-bold text-lg text-white">AyurLLM</span>
              </div>
              <p className="leading-relaxed">
                From Manuscript to Machine-Searchable Medicine. Built on a RAG pipeline over classical Ayurvedic literature extended into a verified online hospital platform.
              </p>
              <p className="text-[10px] text-ayur-400 font-mono">
                Presented to: Prof. Kunal Anand | 8th October 2026
              </p>
            </div>

            <div>
              <h4 className="font-bold text-white uppercase tracking-wider text-xs mb-3">Brihat & Laghu Trayi</h4>
              <ul className="space-y-1.5 text-xs">
                <li>Charaka Samhita (1,558 Chunks)</li>
                <li>Sushruta Samhita (240 Chunks)</li>
                <li>Astanga Hridaya (126 Chunks)</li>
                <li>Sharangadhara Samhita (1,972 Chunks)</li>
                <li>Bhavaprakasha V1 & V2 (3,010 Chunks)</li>
                <li>Madhava Nidanam (643 Chunks)</li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-white uppercase tracking-wider text-xs mb-3">Clinical Platforms</h4>
              <ul className="space-y-1.5 text-xs">
                <li>Red-Flag Triage Safety Engine</li>
                <li>Hybrid BM25 + Vector Search (e5-small)</li>
                <li>Bayesian Doctor Verification (0-100)</li>
                <li>WebRTC Encrypted Teleconsultation</li>
                <li>Neo4j Patient Knowledge Graph</li>
                <li>Digital Authenticated E-Prescriptions</li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-white uppercase tracking-wider text-xs mb-3">Clinical Disclaimer</h4>
              <p className="text-[11px] leading-relaxed text-ayur-300">
                Decision support and education only: not an automated allopathic diagnosis. Every verse shown cites its source chunk. Prescriptions come only from registered doctors. Patient data is encrypted and visible to a doctor only during an active consultation.
              </p>
              <div className="mt-3 text-[11px] font-bold text-red-400">
                Emergency Dispatch: Call 112 / 108
              </div>
            </div>
          </div>

          <div className="border-t border-ayur-900 pt-6 flex flex-col sm:flex-row justify-between items-center text-[11px] text-ayur-400">
            <p>© 2026 AyurLLM Project Group — Megha Rege, Hitanshu Choraria, Anand Jadon, Agni Pravoali.</p>
            <p className="mt-2 sm:mt-0 font-mono">Hitanshu_work branch • Ready for production</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </LanguageProvider>
  );
}
