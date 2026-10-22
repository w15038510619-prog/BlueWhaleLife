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
  source_channel?: string;
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
  draft_status: 'draft' | 'pending_approval' | 'approved' | 'published' | 'declined' | 'failed';
  user_notes: string;

  // Phase 2 Tiered comprehension & truthfulness
  comprehension_tier: 'subtitles' | 'metadata_only' | 'multimodal' | 'failed';
  is_partial: boolean;
  evidence_map: Record<string, string[]>;
  failure_reason: string;
  comment_decision_reason: string;

  // Publisher & tracking
  publisher_type: string;
  published_at: string;
  published_comment_id: string;
  publish_error: string;
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
  state: 'idle' | 'thinking' | 'happy' | 'confused' | 'studying' | 'resting' | 'reading' | 'computer' | 'watching';
  mood: string;
  growth_score: number;
  current_activity: string;
  bubble_text: string;
  last_bvid?: string;
  last_discovery_title?: string;
}

export interface SchedulerStatus {
  enabled: boolean;
  last_run_at: string;
  today_date: string;
  today_explores_count: number;
  status: string;
  current_activity: string;
  daily_budget: number;
  quiet_hours: string;
  emergency_stop: boolean;
}

export interface CommentPublication {
  id: number;
  bvid: string;
  comment_content: string;
  publisher_type: string;
  status: string;
  platform_comment_id?: string;
  created_at: string;
  published_at?: string;
  ai_disclaimer_included: boolean;
  audit_passed: boolean;
  audit_details?: string;
  error_message?: string;
}

export interface SettingsResponse {
  llm_base_url: string;
  llm_model: string;
  llm_protocol: string;
  llm_api_key_masked: string;
  has_api_key: boolean;
  demo_mode: boolean;
  daily_cost_budget: number;
  character_name: string;
  curiosity_level: number;
  novelty_weight: number;
  backend_port: number;

  publisher_type: string;
  has_bilibili_token: boolean;
  bilibili_token_masked: string;
  webhook_url: string;
  emergency_stop: boolean;
  max_comments_per_day: number;
  auto_comment_enabled: boolean;

  scheduler_enabled: boolean;
  scheduler_interval_minutes: number;
  quiet_hours_start: number;
  quiet_hours_end: number;
  daily_explore_budget: number;
}
