import React from 'react';
import { 
  BookOpen, 
  Stethoscope, 
  UserCheck, 
  Video, 
  Building2, 
  FileText, 
  Globe, 
  AlertTriangle, 
  ShieldCheck, 
  User as UserIcon,
  Sparkles
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenEmergency: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, onOpenEmergency }) => {
  const { lang, toggleLang, t } = useLanguage();
  const { user, role, setRole } = useAuth();

  const navItems = [
    { id: 'home', label: t('nav.home'), icon: Sparkles },
    { id: 'explorer', label: t('nav.explorer'), icon: BookOpen },
    { id: 'intake', label: t('nav.intake'), icon: Stethoscope },
    { id: 'doctors', label: t('nav.doctors'), icon: UserCheck },
    { id: 'consult', label: t('nav.consult'), icon: Video },
    { id: 'hospital', label: t('nav.hospital'), icon: Building2 },
    { id: 'portal', label: t('nav.portal'), icon: FileText },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-ayur-100 shadow-xs">
      {/* Emergency Triage Bar */}
      <div className="bg-red-600 text-white text-xs py-1 px-4 flex items-center justify-between font-medium">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-3.5 h-3.5 text-yellow-300 animate-pulse" />
          <span>Clinical Safety Protocol: Experiencing acute crushing chest pain, slurred speech, or choking?</span>
        </div>
        <button 
          onClick={onOpenEmergency}
          className="bg-white/20 hover:bg-white/30 text-white px-2.5 py-0.5 rounded text-xs font-bold transition flex items-center space-x-1"
        >
          <span>Call 112 / 108 Hotline</span>
        </button>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div 
            onClick={() => setActiveTab('home')}
            className="flex items-center space-x-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ayur-800 to-ayur-600 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
              <span className="font-serif font-black text-xl text-gold-300">आयु</span>
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-display font-bold text-xl tracking-tight text-ayur-950">AyurLLM</span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-ayur-100 text-ayur-800 border border-ayur-200">
                  v2.0
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">From Manuscript to Machine-Searchable Medicine</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-ayur-800 text-white shadow-xs'
                      : 'text-slate-600 hover:text-ayur-900 hover:bg-ayur-50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-gold-300' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Actions & Role Switcher */}
          <div className="flex items-center space-x-2.5">
            {/* Language Toggle */}
            <button
              onClick={toggleLang}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-ayur-300 text-xs font-semibold text-slate-700 bg-white hover:bg-ayur-50 transition"
              title="Toggle English / हिन्दी"
            >
              <Globe className="w-3.5 h-3.5 text-ayur-600" />
              <span>{lang === 'en' ? 'हिन्दी' : 'EN'}</span>
            </button>

            {/* Role Switcher Demo Control */}
            <div className="flex items-center rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
              <button
                onClick={() => setRole('patient')}
                className={`px-2 py-1 rounded font-medium transition ${
                  role === 'patient' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Patient
              </button>
              <button
                onClick={() => setRole('doctor')}
                className={`px-2 py-1 rounded font-medium transition ${
                  role === 'doctor' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Vaidya
              </button>
              <button
                onClick={() => setRole('admin')}
                className={`px-2 py-1 rounded font-medium transition ${
                  role === 'admin' ? 'bg-white text-ayur-900 shadow-xs font-bold' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Admin
              </button>
            </div>

            {/* User Avatar */}
            <div className="hidden lg:flex items-center space-x-2 pl-2 border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-ayur-100 border border-ayur-300 flex items-center justify-center text-ayur-800 text-xs font-bold">
                {user.full_name.slice(0, 2).toUpperCase()}
              </div>
              <div className="text-left text-xs">
                <p className="font-semibold text-slate-800 leading-tight truncate max-w-[100px]">{user.full_name}</p>
                <p className="text-[10px] text-ayur-600 capitalize font-medium">{role}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
