"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Video,
  Mic,
  MicOff,
  VideoOff,
  PhoneOff,
  MessageSquare,
  FileText,
  User,
  Settings,
  Share2,
} from "lucide-react";

export default function ConsultationPage() {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [activeTab, setActiveTab] = useState("notes");

  return (
    <div className="flex flex-col min-h-screen bg-[var(--background)]">
      <Navbar />

      <main className="flex-1 pt-20 pb-8 h-screen flex flex-col">
        <div className="container-app h-full flex flex-col lg:flex-row gap-6 pt-4">
          
          {/* Main Video Area */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Header */}
            <div className="flex items-center justify-between card px-6 py-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--ayur-emerald)] to-[var(--ayur-emerald-dark)] flex items-center justify-center text-white font-bold text-lg">
                  AS
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Dr. Ananya Sharma</h2>
                  <p className="text-sm text-[var(--ayur-emerald-light)] font-medium">
                    Consultation in progress... 12:45
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn btn-ghost btn-sm">
                  <Share2 className="w-4 h-4" />
                </button>
                <button className="btn btn-ghost btn-sm">
                  <Settings className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Video Container */}
            <div className="flex-1 card overflow-hidden relative bg-black flex items-center justify-center min-h-[400px]">
              {/* Remote Video (Mock) */}
              <div className="absolute inset-0 flex items-center justify-center bg-[#111]">
                <User className="w-32 h-32 text-gray-700" />
              </div>
              
              {/* Local Video (Mock) */}
              <div className="absolute bottom-6 right-6 w-48 h-36 bg-gray-800 rounded-xl border-2 border-[var(--border)] overflow-hidden shadow-2xl z-10 flex items-center justify-center">
                 {isVideoOff ? (
                    <User className="w-12 h-12 text-gray-500" />
                 ) : (
                    <div className="w-full h-full bg-gray-700 flex items-center justify-center">
                       <span className="text-xs text-gray-400">Camera Active</span>
                    </div>
                 )}
              </div>

              {/* Controls */}
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 p-3 rounded-2xl glass-light z-10">
                <button 
                  onClick={() => setIsMuted(!isMuted)}
                  className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
                    isMuted ? "bg-red-500/20 text-red-500 hover:bg-red-500/30" : "bg-[var(--background-card)] hover:bg-[var(--border)] text-white"
                  }`}
                >
                  {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                </button>
                
                <button 
                  onClick={() => setIsVideoOff(!isVideoOff)}
                  className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
                    isVideoOff ? "bg-red-500/20 text-red-500 hover:bg-red-500/30" : "bg-[var(--background-card)] hover:bg-[var(--border)] text-white"
                  }`}
                >
                  {isVideoOff ? <VideoOff className="w-5 h-5" /> : <Video className="w-5 h-5" />}
                </button>
                
                <button className="w-14 h-12 rounded-xl bg-red-600 hover:bg-red-700 text-white flex items-center justify-center transition-colors shadow-[0_0_15px_rgba(220,38,38,0.4)]">
                  <PhoneOff className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="w-full lg:w-[400px] flex flex-col gap-4">
            <div className="card flex-1 flex flex-col overflow-hidden">
              {/* Tabs */}
              <div className="flex border-b border-[var(--border)]">
                <button 
                  onClick={() => setActiveTab("notes")}
                  className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === "notes" ? "border-[var(--ayur-emerald)] text-[var(--ayur-emerald-light)]" : "border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
                  }`}
                >
                  <FileText className="w-4 h-4 inline-block mr-2" />
                  Prescription
                </button>
                <button 
                  onClick={() => setActiveTab("chat")}
                  className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === "chat" ? "border-[var(--ayur-emerald)] text-[var(--ayur-emerald-light)]" : "border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
                  }`}
                >
                  <MessageSquare className="w-4 h-4 inline-block mr-2" />
                  Chat
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === "notes" ? (
                  <div className="space-y-4">
                    <div className="p-3 bg-[var(--background-elevated)] rounded-lg border border-[var(--border)]">
                      <h4 className="text-xs font-semibold uppercase text-[var(--foreground-muted)] mb-2">Live Notes</h4>
                      <p className="text-sm text-[var(--foreground)]">Patient reports mild joint pain in knees. Vata aggravation suspected.</p>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-semibold mb-2">Recommended Medicines</h4>
                      <div className="space-y-2">
                         <div className="flex justify-between items-center p-2 border border-[var(--border)] rounded text-sm">
                            <span>Ashwagandha Churna</span>
                            <span className="text-[var(--foreground-muted)]">5g / BD</span>
                         </div>
                         <div className="flex justify-between items-center p-2 border border-[var(--border)] rounded text-sm">
                            <span>Mahanarayan Taila</span>
                            <span className="text-[var(--foreground-muted)]">Local App.</span>
                         </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col h-full justify-end space-y-4">
                    <div className="text-center text-xs text-[var(--foreground-dim)] my-4">Chat started</div>
                    <div className="bg-[var(--background-elevated)] p-3 rounded-lg rounded-tl-none self-start max-w-[85%]">
                      <p className="text-sm">Hello, can you hear me clearly?</p>
                      <span className="text-[10px] text-[var(--foreground-dim)] mt-1 block">12:40 PM</span>
                    </div>
                    <div className="bg-[var(--ayur-emerald)]/20 border border-[var(--ayur-emerald)]/30 p-3 rounded-lg rounded-tr-none self-end max-w-[85%]">
                      <p className="text-sm text-[var(--ayur-emerald-light)]">Yes, doctor. Loud and clear.</p>
                      <span className="text-[10px] text-[var(--ayur-emerald)]/60 mt-1 block text-right">12:41 PM</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              {activeTab === "chat" && (
                <div className="p-3 border-t border-[var(--border)]">
                  <div className="flex gap-2">
                    <input type="text" className="input text-sm" placeholder="Type a message..." />
                    <button className="btn btn-primary px-4">Send</button>
                  </div>
                </div>
              )}
            </div>
          </div>
          
        </div>
      </main>
    </div>
  );
}
