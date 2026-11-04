/// <reference types="vite/client" />
import axios from 'axios';
import { ShlokaChunk, Doctor, TriageResult, KnowledgeGraphData, PharmacyItem, PanchakarmaTherapy } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth
export const requestOtp = async (phoneOrEmail: string, role = 'patient') => {
  const res = await api.post('/auth/request-otp', { phone_or_email: phoneOrEmail, role });
  return res.data;
};

export const verifyOtp = async (phoneOrEmail: string, otp: string, fullName?: string) => {
  const res = await api.post('/auth/verify-otp', { phone_or_email: phoneOrEmail, otp, full_name: fullName });
  return res.data;
};

// Shloka RAG Search
export const searchShlokas = async (query: string, sthana?: string, category?: string, limit = 6) => {
  const res = await api.get('/search', { params: { q: query, sthana, category, limit } });
  return res.data;
};

export const getAllShlokas = async () => {
  const res = await api.get('/search/all-shlokas');
  return res.data;
};

// Intake & Triage
export const getPrakritiQuiz = async () => {
  const res = await api.get('/intake/prakriti-quiz');
  return res.data;
};

export const submitIntake = async (payload: {
  chief_complaint: string;
  symptoms: string[];
  severity_level: number;
  duration_days: number;
  current_medications?: string;
  known_allergies?: string;
  prakriti_answers?: Array<{ question_id: number; selected_option: string }>;
}) => {
  const res = await api.post('/intake/submit', payload);
  return res.data;
};

export const checkTriageQuick = async (symptoms: string, chiefComplaint?: string, severity = 1): Promise<TriageResult> => {
  const res = await api.post('/triage/check', { symptoms, chief_complaint: chiefComplaint, severity });
  return res.data;
};

// Doctors
export const getDoctors = async (params?: { specialty?: string; verified_only?: boolean; min_trust_score?: number; search?: string }): Promise<Doctor[]> => {
  const res = await api.get('/doctors', { params });
  return res.data;
};

export const getDoctorDetail = async (id: number): Promise<Doctor> => {
  const res = await api.get(`/doctors/${id}`);
  return res.data;
};

export const claimDoctorProfile = async (data: any) => {
  const res = await api.post('/doctors/claim', data);
  return res.data;
};

export const verifyDoctorAdmin = async (id: number, approved = true) => {
  const res = await api.post(`/doctors/${id}/verify`, null, { params: { approved } });
  return res.data;
};

// Appointments
export const getDoctorSlots = async (doctorId: number) => {
  const res = await api.get(`/appointments/slots/${doctorId}`);
  return res.data;
};

export const bookAppointment = async (data: { doctor_id: number; slot_time: string; chief_complaint: string; symptoms: string[] }) => {
  const res = await api.post('/appointments/book', data);
  return res.data;
};

// Consultations & Graph
export const getConsultation = async (consultationId: number) => {
  const res = await api.get(`/consultations/${consultationId}`);
  return res.data;
};

export const getConsultationGraph = async (consultationId: number): Promise<KnowledgeGraphData> => {
  const res = await api.get(`/consultations/${consultationId}/graph`);
  return res.data;
};

export const endConsultation = async (consultationId: number, notes: string) => {
  const res = await api.post(`/consultations/${consultationId}/end`, null, { params: { clinical_notes: notes } });
  return res.data;
};

// Prescriptions
export const createPrescription = async (data: any) => {
  const res = await api.post('/prescriptions/create', data);
  return res.data;
};

export const getPrescription = async (id: number) => {
  const res = await api.get(`/prescriptions/${id}`);
  return res.data;
};

export const getPatientPrescriptions = async (patientId: number) => {
  const res = await api.get(`/prescriptions/patient/${patientId}`);
  return res.data;
};

// Hospital ERP
export const getPharmacyInventory = async (category?: string, lowStock?: boolean): Promise<PharmacyItem[]> => {
  const res = await api.get('/hospital/pharmacy', { params: { category, low_stock: lowStock } });
  return res.data;
};

export const getPanchakarmaTherapies = async (): Promise<PanchakarmaTherapy[]> => {
  const res = await api.get('/hospital/panchakarma');
  return res.data;
};

export const bookPanchakarma = async (data: { therapy_id: number; start_date: string }) => {
  const res = await api.post('/hospital/panchakarma/book', data);
  return res.data;
};

export const getHospitalAnalytics = async () => {
  const res = await api.get('/analytics/hospital-overview');
  return res.data;
};
