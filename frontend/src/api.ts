/** Typed API client for the FastAPI backend. */

export type StepState = 'pending' | 'active' | 'done' | 'failed';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface StepInfo {
  name: string;
  label: string;
  state: StepState;
}

export interface MeetingResult {
  title: string;
  summary: string;
  action_items: string;
  key_decisions: string;
  questions: string;
  transcript: string;
}

export interface JobDetail {
  job_id: string;
  status: JobStatus;
  source: string;
  source_type: 'url' | 'upload';
  language: string;
  progress: number;
  steps: StepInfo[];
  result: MeetingResult | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface JobSummary {
  job_id: string;
  status: JobStatus;
  title: string;
  source: string;
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  ts: string;
}

const jsonHeaders = { 'Content-Type': 'application/json' };

async function handle<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health(): Promise<{ status: string }> {
    return fetch('/api/health').then((r) => handle(r));
  },

  analyzeUrl(url: string, language: string): Promise<{ job_id: string }> {
    return fetch('/api/jobs/analyze-url', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ url, language }),
    }).then((r) => handle(r));
  },

  uploadFile(file: File, language: string): Promise<{ job_id: string }> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('language', language);
    return fetch('/api/jobs/upload', { method: 'POST', body: fd }).then((r) => handle(r));
  },

  listJobs(): Promise<JobSummary[]> {
    return fetch('/api/jobs').then((r) => handle(r));
  },

  getJob(id: string): Promise<JobDetail> {
    return fetch(`/api/jobs/${id}`).then((r) => handle(r));
  },

  chat(id: string, question: string): Promise<{ answer: string }> {
    return fetch(`/api/chat/${id}`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ question }),
    }).then((r) => handle(r));
  },

  chatHistory(id: string): Promise<ChatMessage[]> {
    return fetch(`/api/chat/${id}/history`).then((r) => handle(r));
  },

  exportUrl(id: string, fmt: 'pdf' | 'markdown' | 'txt'): string {
    return `/api/export/${id}/${fmt}`;
  },
};
