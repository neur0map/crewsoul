import { writable } from 'svelte/store';
import type { SSEEvent } from './types';

export const events = writable<SSEEvent[]>([]);
export const connected = writable(false);

let eventSource: EventSource | null = null;

export function connectSSE(jobId?: string) {
  if (eventSource) eventSource.close();
  const url = jobId ? `/api/events?job_id=${jobId}` : '/api/events';
  eventSource = new EventSource(url);
  eventSource.onopen = () => connected.set(true);
  eventSource.onerror = () => connected.set(false);
  const eventTypes = [
    'job.status_change', 'converser.message', 'target.response',
    'judge.score', 'soul.updated', 'guardrail.added',
    'job.plateau', 'job.complete', 'rate_limit', 'error',
  ];
  for (const type of eventTypes) {
    eventSource.addEventListener(type, (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      events.update(list => [...list, { type, ...data }]);
    });
  }
}

export function disconnectSSE() {
  eventSource?.close();
  eventSource = null;
  connected.set(false);
}
