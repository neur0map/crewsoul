<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api';
  import type { ChatMessage, Job } from '$lib/types';

  let messages: ChatMessage[] = $state([]);
  let input = $state('');
  let loading = $state(false);
  let jobInfo: Job | null = $state(null);
  let error = $state('');

  const jobId = $page.params.jobId!;

  onMount(async () => {
    try {
      jobInfo = await api.jobs.get(jobId);
      const chattable = ['TESTING', 'COMPLETED', 'REVIEW'];
      if (jobInfo && !chattable.includes(jobInfo.status)) {
        error = `Cannot chat with job in ${jobInfo.status} state. Wait for it to finish or go back to the queue.`;
        return;
      }
      const res = await api.chat.history(jobId);
      if (res.history?.length) {
        messages = res.history;
      }
    } catch (e: any) {
      error = e.message || 'Failed to load job';
    }
  });

  async function send() {
    if (!input.trim() || loading) return;
    const msg = input;
    input = '';
    messages = [...messages, { role: 'user', content: msg }];
    loading = true;
    try {
      const res = await api.chat.send(jobId, msg);
      messages = [...messages, { role: 'assistant', content: res.response }];
    } catch (e: any) {
      messages = [...messages, { role: 'assistant', content: `Error: ${e.message || e}` }];
    }
    loading = false;
  }
</script>

<div class="header">
  <h1>Test Chat {jobInfo ? `— ${jobInfo.character}` : ''}</h1>
  {#if jobInfo}
    <div class="meta">
      <span class="status">{jobInfo.status}</span>
      {#if jobInfo.scores.length}
        <span class="mono">Score: {jobInfo.scores[jobInfo.scores.length - 1].toFixed(2)}</span>
      {/if}
      <span class="mono">SOUL v{jobInfo.current_soul_version}</span>
    </div>
  {/if}
  <a href="/queue" class="back">&larr; Back to queue</a>
</div>

{#if error}
  <div class="error">{error}</div>
{:else}
  <div class="chat">
    {#each messages as msg}
      <div class="message {msg.role}">
        <span class="label">{msg.role === 'user' ? 'You' : 'Target'}</span>
        <p>{msg.content}</p>
      </div>
    {/each}
    {#if loading}
      <div class="message assistant"><span class="label">Target</span><p class="typing">...</p></div>
    {/if}
    {#if messages.length === 0 && !loading}
      <p class="empty">Start a conversation to test the personality.</p>
    {/if}
  </div>

  <div class="input-bar">
    <input bind:value={input} onkeydown={(e: KeyboardEvent) => e.key === 'Enter' && send()} placeholder="Type a message..." />
    <button class="primary" onclick={send} disabled={loading}>Send</button>
  </div>
{/if}

<style>
  .header { margin-bottom: 1rem; }
  h1 { font-size: 1.125rem; font-weight: 600; margin-bottom: 0.25rem; }
  .meta { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.5rem; font-size: 0.8125rem; }
  .status { font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 1rem; background: #f3e8ff; color: #7c3aed; }
  .back { font-size: 0.8125rem; color: var(--text-secondary); }
  .chat { min-height: 20rem; max-height: 32rem; overflow-y: auto; border: 1px solid var(--border); border-radius: 0.25rem; padding: 1rem; margin-bottom: 0.75rem; }
  .message { margin-bottom: 0.75rem; }
  .label { font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
  .message.user p { color: var(--text-primary); }
  .message.assistant p { color: var(--text-secondary); }
  .typing { color: var(--text-muted); }
  .empty { color: var(--text-muted); text-align: center; font-style: italic; }
  .input-bar { display: flex; gap: 0.5rem; }
  .input-bar input { flex: 1; }
  .error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 0.75rem; border-radius: 0.25rem; }
  .mono { font-family: var(--font-mono); color: var(--text-secondary); }
</style>
