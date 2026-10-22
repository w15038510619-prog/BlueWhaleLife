import {
  PetStatus,
  VideoCandidate,
  VideoAnalysis,
  KnowledgeNote,
  ReflectionLog,
  PersonalityState,
  SettingsResponse,
  SchedulerStatus,
  CommentPublication
} from '../types';

const BASE_URL = '';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {})
    },
    ...options
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error [${res.status}]: ${errorText || res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Pet Status & Chat
  getPetStatus: () => request<PetStatus>('/api/pet/status'),
  chatWithPet: (message: string) => request<{ reply: string; pet_state: string; mood: string }>('/api/pet/chat', {
    method: 'POST',
    body: JSON.stringify({ message })
  }),
  getChatHistory: () => request<any[]>('/api/chat/history'),

  // Discovery
  explore: (forceRefresh = false) => request<VideoCandidate[]>(`/api/discovery/explore?force_refresh=${forceRefresh}`, {
    method: 'POST'
  }),
  getCandidates: () => request<VideoCandidate[]>('/api/discovery/candidates'),
  watchCandidate: (bvid: string) => request<VideoAnalysis>(`/api/discovery/watch/${bvid}`, {
    method: 'POST'
  }),

  // Video Diaries & Comments
  getVideos: () => request<VideoAnalysis[]>('/api/videos'),
  getVideo: (bvid: string) => request<VideoAnalysis>(`/api/videos/${bvid}`),
  updateDraft: (bvid: string, draft_status?: string, comment_draft?: string, user_notes?: string, publisher_type?: string) =>
    request<VideoAnalysis>(`/api/videos/${bvid}/draft`, {
      method: 'PATCH',
      body: JSON.stringify({ draft_status, comment_draft, user_notes, publisher_type })
    }),
  analyzeCustomVideo: (data: { bvid: string; title?: string; author?: string; description?: string; tags?: string[] }) =>
    request<VideoAnalysis>('/api/videos/analyze', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  publishComment: (bvid: string) => request<any>(`/api/comments/${bvid}/publish`, {
    method: 'POST'
  }),
  getCommentPublications: () => request<CommentPublication[]>('/api/comments/publications'),

  // Autonomous Life Scheduler
  getSchedulerStatus: () => request<SchedulerStatus>('/api/scheduler/status'),
  triggerSchedulerCycle: () => request<{ status: string; result: string }>('/api/scheduler/trigger', {
    method: 'POST'
  }),

  // Memory & Knowledge Notes
  getKnowledgeNotes: (activeOnly = true) => request<KnowledgeNote[]>(`/api/memory/notes?active_only=${activeOnly}`),
  createKnowledgeNote: (data: { topic: string; content: string; importance?: number; source_bvid?: string }) =>
    request<KnowledgeNote>('/api/memory/notes', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  updateKnowledgeNote: (id: number, data: Partial<KnowledgeNote>) =>
    request<KnowledgeNote>(`/api/memory/notes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  forgetKnowledgeNote: (id: number) => request<{ status: string; message: string }>(`/api/memory/notes/${id}`, {
    method: 'DELETE'
  }),
  deduplicateNotes: () => request<{ status: string; merged_count: number }>('/api/memory/deduplicate', {
    method: 'POST'
  }),
  searchMemories: (q: string) => request<{ query: string; notes: KnowledgeNote[]; videos: VideoAnalysis[] }>(`/api/memory/search?q=${encodeURIComponent(q)}`),

  // Personality & Reflection
  getSoulCurrent: () => request<PersonalityState>('/api/soul/current'),
  getSoulHistory: () => request<PersonalityState[]>('/api/soul/history'),
  rollbackSoul: (target_version: number) => request<PersonalityState>('/api/soul/rollback', {
    method: 'POST',
    body: JSON.stringify({ target_version })
  }),
  triggerReflection: () => request<ReflectionLog>('/api/reflection/trigger', {
    method: 'POST'
  }),
  getReflectionLogs: () => request<ReflectionLog[]>('/api/reflection/logs'),

  // Settings
  getSettings: () => request<SettingsResponse>('/api/settings'),
  updateSettings: (data: any) => request<SettingsResponse>('/api/settings', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  testConnection: (data: { base_url?: string; api_key?: string; model?: string; protocol?: string }) =>
    request<{ success: boolean; latency_ms: number; reply?: string; model?: string; protocol?: string; error_message?: string; status_code?: number; details?: string }>('/api/settings/test-connection', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  getUsage: () => request<{ today_cost_cny: number; total_calls: number; total_tokens: number; all_time_cost_cny: number; recent_logs: any[] }>('/api/settings/usage')
};
