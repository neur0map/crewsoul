<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api';
  import { connectSSE, disconnectSSE, events } from '$lib/sse';
  import type { Job, SSEEvent } from '$lib/types';

  let jobs: Job[] = $state([]);
  let liveEvents: SSEEvent[] = $state([]);
  let loading = $state(true);
  let unsub: (() => void) | undefined;

  onMount(async () => {
    jobs = await api.jobs.list();
    loading = false;
    connectSSE();
    unsub = events.subscribe(evts => {
      liveEvents = evts.slice(-50); // keep last 50 events
      api.jobs.list().then(j => { jobs = j; });
    });
  });

  onDestroy(() => {
    disconnectSSE();
    unsub?.();
  });

  function activeJobs(): Job[] {
    return jobs.filter(j => ['RESEARCHING', 'READY', 'LOOPING'].includes(j.status));
  }

  function completedJobs(): Job[] {
    return jobs.filter(j => ['COMPLETED', 'REVIEW', 'TESTING', 'EXPORTED'].includes(j.status));
  }
</script>

<h1>Dashboard</h1>
<p class="subtitle">Observatory — watch personality forging in real-time</p>

{#if loading}
  <p>Loading...</p>
{:else if jobs.length === 0}
  <div class="placeholder">
    <p>No jobs yet. <a href="/queue">Add a character to the queue</a> to get started.</p>
  </div>
{:else}
  <div class="layout">
    <div class="main-col">
      {#if activeJobs().length > 0}
        <h2>Active</h2>
        {#each activeJobs() as job}
          <div class="job-card">
            <div class="job-header">
              <strong>{job.character}</strong>
              <span class="status {job.status.toLowerCase()}">{job.status}</span>
            </div>
            {#if job.status === 'LOOPING'}
              <div class="loop-info">
                <span class="mono">Loop {job.current_loop}/{job.max_loops}</span>
                {#if job.scores.length}
                  <span class="mono">Score: {job.scores[job.scores.length - 1].toFixed(2)}</span>
                {/if}
              </div>
              {#if job.scores.length > 1}
                <div class="score-bar">
                  {#each job.scores as score, i}
                    <div class="score-tick" style="height: {score * 100}%;" title="Loop {i+1}: {score.toFixed(2)}"></div>
                  {/each}
                </div>
              {/if}
            {/if}
          </div>
        {/each}
      {/if}

      {#if completedJobs().length > 0}
        <h2>Completed</h2>
        {#each completedJobs() as job}
          <div class="job-card done">
            <div class="job-header">
              <strong>{job.character}</strong>
              <span class="status {job.status.toLowerCase()}">{job.status}</span>
              {#if job.scores.length}
                <span class="mono">Final: {job.scores[job.scores.length - 1].toFixed(2)}</span>
              {/if}
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <div class="event-col">
      <h2>Live Events</h2>
      <div class="event-feed">
        {#if liveEvents.length === 0}
          <p class="empty">Waiting for events...</p>
        {:else}
          {#each [...liveEvents].reverse() as evt}
            <div class="event">
              <span class="event-type">{evt.type}</span>
              {#if evt.tone}<span class="event-detail">[{evt.tone}]</span>{/if}
              {#if evt.text}<span class="event-text">{String(evt.text).slice(0, 100)}{String(evt.text).length > 100 ? '...' : ''}</span>{/if}
              {#if evt.overall}<span class="event-score mono">{Number(evt.overall).toFixed(2)}</span>{/if}
              {#if evt.status}<span class="event-detail">{evt.status}</span>{/if}
              {#if evt.message}<span class="event-text">{evt.message}</span>{/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  h1 { font-size: 1.125rem; font-weight: 600; margin-bottom: 0.25rem; }
  h2 { font-size: 0.875rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; margin-top: 1rem; }
  .subtitle { color: var(--text-secondary); margin-bottom: 1.5rem; }
  .placeholder { border: 1px dashed var(--border); padding: 2rem; text-align: center; border-radius: 0.25rem; color: var(--text-muted); }
  .placeholder a { color: var(--accent); }
  .layout { display: grid; grid-template-columns: 1fr 20rem; gap: 1.5rem; }
  .job-card { border: 1px solid var(--border); border-radius: 0.25rem; padding: 0.75rem; margin-bottom: 0.5rem; background: var(--bg-surface); }
  .job-card.done { opacity: 0.7; }
  .job-header { display: flex; align-items: center; gap: 0.5rem; }
  .loop-info { display: flex; gap: 0.75rem; margin-top: 0.375rem; font-size: 0.8125rem; }
  .score-bar { display: flex; gap: 2px; align-items: flex-end; height: 2rem; margin-top: 0.5rem; }
  .score-tick { width: 6px; background: var(--accent); border-radius: 1px; min-height: 2px; }
  .status { font-size: 0.6875rem; padding: 0.1rem 0.4rem; border-radius: 1rem; }
  .status.researching { background: #e0e7ff; color: #3730a3; }
  .status.ready { background: #dbeafe; color: #1d4ed8; }
  .status.looping { background: #dbeafe; color: #1d4ed8; }
  .status.completed { background: #dcfce7; color: #15803d; }
  .status.review { background: #fef3c7; color: #b45309; }
  .status.testing { background: #f3e8ff; color: #7c3aed; }
  .status.exported { background: #f0fdf4; color: #166534; }
  .mono { font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-secondary); }
  .event-col { border-left: 1px solid var(--border); padding-left: 1rem; }
  .event-feed { max-height: 30rem; overflow-y: auto; }
  .event { padding: 0.375rem 0; border-bottom: 1px solid var(--bg-inset); font-size: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.375rem; align-items: baseline; }
  .event-type { font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); font-size: 0.6875rem; }
  .event-detail { color: var(--accent); }
  .event-text { color: var(--text-secondary); max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
  .event-score { color: var(--success); font-weight: 600; }
  .empty { color: var(--text-muted); font-style: italic; font-size: 0.8125rem; }
</style>
