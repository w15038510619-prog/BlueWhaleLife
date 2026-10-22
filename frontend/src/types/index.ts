export interface VideoCandidate {
  bvid: string;
  title: string;
  author: string;
  cover: string;
  duration: string;
  pubdate: string;
  tags: string[];
  description: string;
  reason: string;
  score: number;
  status: 'discovered' | 'watched' | 'skipped';
}

export interface VideoAnalysis {
  bvid: string;
  title: string;
  author: string;
  cover: string;
  description: string;
  tags: string[];
  watched_at: string;
  choice_reason: string;
  summary: string;
  learned: string;
  viewpoint: string;
  doubts: string;
  worth_commenting: boolean;
  comment_draft: string;
  draft_status: 'draft' | 'approved' | 'copied' | 'rejected';
  user_notes: string;
}

export interface KnowledgeNote {
  id?: number;
  topic: string;
  content: string;
  source_bvid?: string;
  created_at: string;
  importance: number;
  is_active: boolean;
}

export interface ReflectionLog {
  id?: number;
  date: string;
  discoveries_summary: string;
  viewpoint_shifts: string;
  new_interests: string[];
  pending_doubts: string;
  growth_score: number;
  mood: string;
  created_at: string;
}

export interface PersonalityState {
  id?: number;
  version: number;
  created_at: string;
  reason: string;
  traits: Record<string, number>;
  interests: Record<string, number>;
  is_current: boolean;
}

export interface PetStatus {
  state: 'idle' | 'thinking' | 'happy' | 'confused' | 'studying' | 'resting';
  mood: string;
  growth_score: number;
  current_activity: string;
  bubble_text: string;
  last_bvid?: string;
  last_discovery_title?: string;
}

export interface SettingsResponse {
  llm_base_url: string;
  llm_model: string;
  llm_api_key_masked: string;
  has_api_key: boolean;
  demo_mode: boolean;
  character_name: string;
  curiosity_level: number;
  novelty_weight: number;
  backend_port: number;
}
