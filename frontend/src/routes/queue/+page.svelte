<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api';
  import { connectSSE, disconnectSSE, events } from '$lib/sse';
  import type { Job } from '$lib/types';

  const SCORE_DIMENSIONS = [
    'character', 'speech', 'values', 'injection',
    'adaptation', 'proactiveness', 'uniqueness', 'leak_detection'
  ] as const;

  type Dimension = typeof SCORE_DIMENSIONS[number];

  interface ProfileDraft {
    reference_samples: string[];
    score_weights: Record<Dimension, number>;
  }

  function defaultDraft(): ProfileDraft {
    const weights = {} as Record<Dimension, number>;
    for (const dim of SCORE_DIMENSIONS) weights[dim] = 1.0;
    return { reference_samples: [], score_weights: weights };
  }

  let jobs: Job[] = $state([]);
  let newCharacter = $state('');
  let searchMode = $state('normal');
  let loading = $state(true);

  // Per-job profile drafts keyed by job id
  let drafts: Record<string, ProfileDraft> = $state({});
  // Track which job's editor panel is expanded
  let expandedEditor: string | null = $state(null);

  let unsub: (() => void) | undefined;

  onMount(async () => {
    jobs = await api.jobs.list();
    loading = false;
    connectSSE();
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
    const draft = drafts[id];
    if (draft) {
      await api.jobs.patchProfile(id, {
        reference_samples: draft.reference_samples.filter(s => s.trim() !== ''),
        score_weights: draft.score_weights,
      });
    }
    await api.jobs.approve(id);
    delete drafts[id];
    expandedEditor = null;
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

  function initDraft(job: any) {
    if (drafts[job.id]) return;
    const profile = job.personality_profile ?? {};
    const existingSamples: string[] = Array.isArray(profile.reference_samples)
      ? [...profile.reference_samples]
      : [];
    const existingWeights: Partial<Record<Dimension, number>> = profile.score_weights ?? {};
    const weights = {} as Record<Dimension, number>;
    for (const dim of SCORE_DIMENSIONS) {
      weights[dim] = typeof existingWeights[dim] === 'number' ? existingWeights[dim] : 1.0;
    }
    drafts[job.id] = { reference_samples: existingSamples, score_weights: weights };
  }

  function toggleEditor(job: any) {
    if (expandedEditor === job.id) {
      expandedEditor = null;
    } else {
      initDraft(job);
      expandedEditor = job.id;
    }
  }

  function addSample(jobId: string) {
    drafts[jobId].reference_samples = [...drafts[jobId].reference_samples, ''];
  }

  function removeSample(jobId: string, index: number) {
    drafts[jobId].reference_samples = drafts[jobId].reference_samples.filter((_, i) => i !== index);
  }

  function updateSample(jobId: string, index: number, value: string) {
    const arr = [...drafts[jobId].reference_samples];
    arr[index] = value;
    drafts[jobId].reference_samples = arr;
  }

  function updateWeight(jobId: string, dim: Dimension, value: number) {
    drafts[jobId].score_weights = { ...drafts[jobId].score_weights, [dim]: value };
  }

  function canApprove(status: string) {
    return status === 'COMPLETED' || status === 'REVIEW' || status === 'READY';
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
            {#if canApprove(job.status)}
              <button onclick={() => toggleEditor(job)}>
                {expandedEditor === job.id ? 'Close Editor' : 'Edit & Approve'}
              </button>
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
        {#if expandedEditor === job.id && drafts[job.id]}
          <tr class="editor-row">
            <td colspan="6">
              <div class="profile-editor">
                <div class="editor-section">
                  <div class="section-label">Reference Samples</div>
                  {#each drafts[job.id].reference_samples as sample, i}
                    <div class="sample-row">
                      <input
                        type="text"
                        value={sample}
                        placeholder="Sample dialogue or text..."
                        oninput={(e) => updateSample(job.id, i, (e.target as HTMLInputElement).value)}
                      />
                      <button class="remove-btn" onclick={() => removeSample(job.id, i)}>Remove</button>
                    </div>
                  {/each}
                  <button class="secondary" onclick={() => addSample(job.id)}>Add sample</button>
                </div>

                <div class="editor-section">
                  <div class="section-label">Score Weights</div>
                  <div class="weights-grid">
                    {#each SCORE_DIMENSIONS as dim}
                      <div class="weight-row">
                        <label for="weight-{job.id}-{dim}">{dim}</label>
                        <input
                          id="weight-{job.id}-{dim}"
                          type="range"
                          min="0.0"
                          max="2.0"
                          step="0.1"
                          value={drafts[job.id].score_weights[dim]}
                          oninput={(e) => updateWeight(job.id, dim, parseFloat((e.target as HTMLInputElement).value))}
                        />
                        <span class="weight-val mono">{drafts[job.id].score_weights[dim].toFixed(1)}</span>
                      </div>
                    {/each}
                  </div>
                </div>

                <div class="editor-actions">
                  <button class="primary" onclick={() => approveJob(job.id)}>Approve</button>
                  <button onclick={() => { expandedEditor = null; }}>Cancel</button>
                </div>
              </div>
            </td>
          </tr>
        {/if}
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

  /* Profile editor */
  .editor-row td { padding: 0; background: var(--bg-inset, #f8f9fa); }
  .profile-editor { padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 1.25rem; }
  .editor-section { display: flex; flex-direction: column; gap: 0.5rem; }
  .section-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); }
  .sample-row { display: flex; gap: 0.5rem; align-items: center; }
  .sample-row input { flex: 1; font-size: 0.875rem; }
  .remove-btn { font-size: 0.75rem; padding: 0.2rem 0.5rem; color: var(--error); border-color: var(--error); background: transparent; }
  .remove-btn:hover { background: #fef2f2; }
  .weights-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: 0.5rem 1.5rem; }
  .weight-row { display: flex; align-items: center; gap: 0.5rem; }
  .weight-row label { font-size: 0.8rem; width: 8rem; flex-shrink: 0; color: var(--text-secondary); text-transform: capitalize; }
  .weight-row input[type="range"] { flex: 1; accent-color: var(--accent); }
  .weight-val { font-size: 0.8rem; width: 2.5rem; text-align: right; color: var(--text-secondary); }
  .editor-actions { display: flex; gap: 0.5rem; padding-top: 0.25rem; }
  .secondary { background: transparent; border: 1px solid var(--border); color: var(--text-secondary); font-size: 0.75rem; padding: 0.2rem 0.5rem; }
  .secondary:hover { background: var(--bg-hover, #f0f1f3); }
</style>
