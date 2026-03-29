const BASE_URL = 'http://localhost:8000';

export interface Participant {
  id: string;
  name: string;
  screener_data: Record<string, string>;
}

export interface Quote {
  id: string;
  text: string;
  participant_id: string;
  transcript_file: string;
  context: string;
  codes: string[];
}

export interface Code {
  id: string;
  label: string;
  description: string;
  quote_ids: string[];
  group: string | null;
  screener_groups: Record<string, string>;
}

export interface Theme {
  id: string;
  name: string;
  description: string;
  code_ids: string[];
  quote_count: number;
  literature_support: string[];
  interpretation: string;
  contradictory_quotes: string[];
}

export interface POV {
  id: string;
  title: string;
  description: string;
  rationale: string;
  supporting_themes: string[];
}

export interface Recommendation {
  id: string;
  text: string;
  supporting_theme: string;
  priority: 'high' | 'medium' | 'low';
  selected: boolean;
}

export interface Session {
  id: string;
  state: PipelineState;
  created_at: string;
  updated_at: string;
  research_brief: string;
  transcripts: Record<string, string>;
  participants: Participant[];
  screener_questions: string[];
  quotes: Quote[];
  codes: Code[];
  data_saturation_reached: boolean;
  participant_coverage: Record<string, boolean>;
  themes: Theme[];
  selected_pov: POV | null;
  povs: POV[];
  recommendations: Recommendation[];
  report: string | null;
  progress_log: ProgressEntry[];
  validation_results: Record<string, unknown>;
  error: string | null;
}

export type PipelineState =
  | 'idle'
  | 'processing_transcripts'
  | 'awaiting_code_review'
  | 'processing_themes'
  | 'awaiting_pov_selection'
  | 'processing_recommendations'
  | 'awaiting_recommendation_selection'
  | 'writing_report'
  | 'complete'
  | 'error';

export interface ProgressEntry {
  timestamp: string;
  stage: string;
  message: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Sessions
  createSession: (brief: string) =>
    request<Session>('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ research_brief: brief }),
    }),

  getSessions: () => request<Session[]>('/api/sessions'),

  getSession: (id: string) => request<Session>(`/api/sessions/${id}`),

  deleteSession: (id: string) =>
    request<{ message: string }>(`/api/sessions/${id}`, { method: 'DELETE' }),

  // Data upload
  uploadTranscripts: (sessionId: string, files: File[]) => {
    const form = new FormData();
    files.forEach(f => form.append('files', f));
    return request<{ message: string; files: string[] }>(
      `/api/sessions/${sessionId}/transcripts`,
      { method: 'POST', body: form }
    );
  },

  setScreener: (sessionId: string, questions: string[]) =>
    request<{ message: string }>(`/api/sessions/${sessionId}/screener`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ screener_questions: questions }),
    }),

  // Pipeline control
  runPipeline: (sessionId: string) =>
    request<{ message: string; state: string }>(`/api/sessions/${sessionId}/run`, {
      method: 'POST',
    }),

  // Human gates
  submitCodeReview: (sessionId: string, codes: Code[]) =>
    request<{ message: string }>(`/api/sessions/${sessionId}/codes/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes }),
    }),

  selectPOV: (sessionId: string, povId: string) =>
    request<{ message: string }>(`/api/sessions/${sessionId}/pov/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pov_id: povId }),
    }),

  selectRecommendations: (sessionId: string, ids: string[]) =>
    request<{ message: string }>(`/api/sessions/${sessionId}/recommendations/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_ids: ids }),
    }),

  // Report
  getReport: (sessionId: string) =>
    request<{ report: string }>(`/api/sessions/${sessionId}/report`),

  getReportDownloadUrl: (sessionId: string) =>
    `${BASE_URL}/api/sessions/${sessionId}/report/download`,
};

// SSE helper
export function createProgressStream(
  sessionId: string,
  onEvent: (event: ProgressEntry) => void,
  onDone: () => void,
  onError: (err: string) => void
): () => void {
  const evtSource = new EventSource(`${BASE_URL}/api/sessions/${sessionId}/progress`);

  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as ProgressEntry & { stage: string };
      if (data.stage === 'stream_end') {
        evtSource.close();
        onDone();
        return;
      }
      onEvent(data);
    } catch {
      // ignore parse errors
    }
  };

  evtSource.onerror = () => {
    evtSource.close();
    onError('Connection to progress stream lost');
  };

  return () => evtSource.close();
}
