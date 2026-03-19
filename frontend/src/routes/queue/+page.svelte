<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api';
  import { connectSSE, disconnectSSE, events } from '$lib/sse';
  import type { Job } from '$lib/types';

  let jobs: Job[] = $state([]);
  let newCharacter = $state('');
  let searchMode = $state('normal');
  let loading = $state(true);

  let unsub: (() => void) | undefined;

  onMount(async () => {
    jobs = await api.jobs.list();
    loading = false;
    connectSSE();
    // Re-fetch jobs when SSE events arrive
    unsub = events.subscribe(() => {
      api.jobs.list().then(j => { jobs = j; });
    });
  });

  onDestroy(() => {
    disconnectSSE();
    unsub?.();
  });

  async function addJob() {
    if (!newCharacter.trim()) return;
    await api.jobs.create(newCharacter, searchMode);
    newCharacter = '';
    jobs = await api.jobs.list();
  }

  async function deleteJob(id: string) {
    await api.jobs.delete(id);
    jobs = await api.jobs.list();
  }

  async function approveJob(id: string) {
    await api.jobs.approve(id);
    jobs = await api.jobs.list();
  }

  async function resumeJob(id: string) {
    await api.jobs.resume(id);
    jobs = await api.jobs.list();
  }

  async function exportJob(id: string) {
    await api.jobs.export(id);
    jobs = await api.jobs.list();
  }
</script>

<h1>Job Queue</h1>

<div class="add-form">
  <div class="add-input">
    <input bind:value={newCharacter} placeholder="Character name (e.g., Master Yoda)" onkeydown={(e: KeyboardEvent) => e.key === 'Enter' && addJob()} />
  </div>
  <div class="add-select">
    <select bind:value={searchMode}>
      <option value="normal">Normal (Brave)</option>
      <option value="smart">Smart (Perplexity)</option>
    </select>
  </div>
  <button class="primary" onclick={addJob} disabled={!newCharacter.trim()}>Add</button>
</div>

{#if loading}
  <p>Loading...</p>
{:else if jobs.length === 0}
  <p class="empty">No jobs yet. Add a character above to get started.</p>
{:else}
  <table>
    <thead>
      <tr>
        <th>Character</th>
        <th>Status</th>
        <th>Loop</th>
        <th>Score</th>
        <th>Search</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each jobs as job}
        <tr>
          <td>{job.character}</td>
          <td><span class="status {job.status.toLowerCase()}">{job.status}</span></td>
          <td class="mono">{job.status === 'LOOPING' ? `${job.current_loop}/${job.max_loops}` : '—'}</td>
          <td class="mono">{job.scores.length ? job.scores[job.scores.length - 1].toFixed(2) : '—'}</td>
          <td>{job.search_mode}</td>
          <td class="actions">
            {#if job.status === 'COMPLETED' || job.status === 'REVIEW'}
              <button onclick={() => approveJob(job.id)}>Approve</button>
            {/if}
            {#if job.status === 'REVIEW'}
              <button onclick={() => resumeJob(job.id)}>Resume</button>
            {/if}
            {#if job.status === 'TESTING' || job.status === 'COMPLETED' || job.status === 'REVIEW'}
              <a href="/chat/{job.id}">Chat</a>
            {/if}
            {#if job.status === 'COMPLETED' || job.status === 'TESTING'}
              <button onclick={() => exportJob(job.id)}>Export</button>
            {/if}
            {#if job.status === 'QUEUED' || job.status === 'EXPORTED'}
              <button class="danger" onclick={() => deleteJob(job.id)}>Delete</button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  h1 { font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; }
  .add-form { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; align-items: center; }
  .add-input { flex: 3; }
  .add-input input { width: 100%; }
  .add-select { flex: 1; min-width: 10rem; }
  .add-select select { width: 100%; }
  .empty { color: var(--text-muted); font-style: italic; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid var(--border); }
  th { color: var(--text-secondary); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .status { font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 1rem; display: inline-block; }
  .status.queued { background: var(--bg-inset); color: var(--text-secondary); }
  .status.researching { background: #e0e7ff; color: #3730a3; }
  .status.ready { background: #dbeafe; color: #1d4ed8; }
  .status.looping { background: #dbeafe; color: #1d4ed8; }
  .status.completed { background: #dcfce7; color: #15803d; }
  .status.review { background: #fef3c7; color: #b45309; }
  .status.testing { background: #f3e8ff; color: #7c3aed; }
  .status.exported { background: #f0fdf4; color: #166534; }
  .mono { font-family: var(--font-mono); }
  .actions { display: flex; gap: 0.375rem; flex-wrap: wrap; align-items: center; }
  .actions button { font-size: 0.75rem; padding: 0.2rem 0.5rem; }
  .actions a { color: var(--accent); font-size: 0.75rem; }
  .danger { color: var(--error); border-color: var(--error); }
  .danger:hover { background: #fef2f2; }
</style>
