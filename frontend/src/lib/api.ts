const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    const msg = err.error || (err.errors && err.errors.join(', ')) || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  config: {
    get: () => request<{ configured: boolean; config: any }>('/config'),
    save: (config: any) => request('/config', { method: 'POST', body: JSON.stringify(config) }),
    validate: (provider: string, api_key: string) =>
      request<{ valid: boolean; models: string[]; error?: string }>('/config/validate', {
        method: 'POST', body: JSON.stringify({ provider, api_key }),
      }),
  },
  jobs: {
    list: () => request<any[]>('/jobs'),
    get: (id: string) => request<any>(`/jobs/${id}`),
    create: (character: string, search_mode: string) =>
      request('/jobs', { method: 'POST', body: JSON.stringify({ character, search_mode }) }),
    delete: (id: string) => request(`/jobs/${id}`, { method: 'DELETE' }),
    approve: (id: string) => request(`/jobs/${id}/approve`, { method: 'POST' }),
    resume: (id: string) => request(`/jobs/${id}/resume`, { method: 'POST' }),
    export: (id: string) => request(`/jobs/${id}/export`, { method: 'POST' }),
    soul: (id: string) => request<{ content: string; version: number }>(`/jobs/${id}/soul`),
    patchProfile: (id: string, body: { reference_samples?: string[]; score_weights?: Record<string, number> }) =>
      request(`/jobs/${id}/profile`, { method: 'PATCH', body: JSON.stringify(body) }),
  },
  chat: {
    send: (jobId: string, message: string) =>
      request<{ response: string; history: any[] }>(`/chat/${jobId}`, {
        method: 'POST', body: JSON.stringify({ message }),
      }),
    history: (jobId: string) => request<{ history: any[] }>(`/chat/${jobId}`),
  },
};
