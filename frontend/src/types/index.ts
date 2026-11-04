export interface User {
  id: number;
  phone?: string;
  email?: string;
  full_name: string;
  role: 'patient' | 'doctor' | 'admin';
}

export interface ShlokaChunk {
  chunk_id: string;
  source_file: string;
  sthana: string;
  chapter: number;
  verse_num: number;
  primary_category: string;
  sanskrit: string;
  transliteration: string;
  hindi_commentary: string;
  english_translation: string;
  clinical_principle: string;
  indications: string[];
  dosha_affinity: string;
  recommended_herbs: string[];
}

export interface TrustBreakdownItem {
  value?: any;
  years?: number;
  rate?: string;
  hours?: string;
  is_verified?: boolean;
  score_out_of_100: number;
  weight: string;
  contribution: number;
  note?: string;
}

export interface Doctor {
  id: number;
  name: string;
  registration_number?: string;
  state_council?: string;
  qualification: string;
  specialty: string;
  experience_years: number;
  bio: string;
  avatar_url?: string;
  consultation_fee: number;
  languages: string;
  is_verified: boolean;
  verification_status: 'Unverified' | 'Pending_Review' | 'Verified' | 'Rejected';
  is_kaggle_seed: boolean;
  bayesian_rating: number;
  total_reviews: number;
  trust_score: number;
  trust_breakdown?: Record<string, TrustBreakdownItem>;
}

export interface TriageResult {
  is_red_flag: boolean;
  status: string;
  emergency_numbers: string[];
  matched_reasons: Array<{
    category: string;
    matched_term: string;
    severity: string;
    advice: string;
  }>;
  action_required: string;
  clinical_disclaimer: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'Patient' | 'Doctor' | 'Consultation' | 'Dosha' | 'Symptom' | 'Shloka' | 'Book';
  color: string;
  radius: number;
  details?: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  relation: string;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  summary: {
    total_nodes: number;
    total_edges: number;
    root_patient: string;
    active_consult_doctor: string;
  };
}

export interface PharmacyItem {
  id: number;
  name: string;
  botanical_name: string;
  classical_text: string;
  category: string;
  stock_quantity: number;
  reorder_level: number;
  is_low_stock: boolean;
  unit_price: number;
  dosha_affinity: string;
  indications: string;
}

export interface PanchakarmaTherapy {
  id: number;
  name: string;
  sanskrit_name: string;
  description: string;
  duration_days: number;
  target_dosha: string;
  price: number;
  requires_doctor_referral: boolean;
  benefits: string;
}
