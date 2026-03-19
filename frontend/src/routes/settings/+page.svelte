<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  let loading = $state(true);
  let saving = $state(false);
  let error = $state('');
  let success = $state('');

  let provider = $state('openai');
  let apiKey = $state('');
  let redactedKey = $state('');
  let keyChecking = $state(false);
  let availableModels: string[] = $state([]);

  let judgeModel = $state('');
  let targetModel = $state('');
  let converserModel = $state('');
  let fetcherModel = $state('');
  let researcherModel = $state('');

  let braveKey = $state('');
  let perplexityKey = $state('');
  let redactedBrave = $state('');
  let redactedPerplexity = $state('');

  let questionsPerLoop = $state(6);
  let scoreThreshold = $state(0.9);
  let maxLoops = $state(15);
  let plateauWindow = $state(3);
  let soulMaxWords = $state(2000);
  let toneRotation = $state('per_question');

  onMount(async () => {
    try {
      const res = await api.config.get();
      if (res.configured && res.config) {
        provider = res.config.provider.active;
        redactedKey = res.config.provider[provider]?.api_key || '';
        const models = res.config.provider[provider]?.models || {};
        judgeModel = models.judge || '';
        targetModel = models.target || '';
        converserModel = models.converser || '';
        fetcherModel = models.fetcher || '';
        researcherModel = models.researcher || '';
        redactedBrave = res.config.search?.brave?.api_key || '';
        redactedPerplexity = res.config.search?.perplexity?.api_key || '';
        const orch = res.config.orchestration || {};
        questionsPerLoop = orch.questions_per_loop || 6;
        scoreThreshold = orch.score_threshold || 0.9;
        maxLoops = orch.max_loops || 15;
        plateauWindow = orch.plateau_window || 3;
        soulMaxWords = orch.soul_max_words || 2000;
        toneRotation = orch.tone_rotation || 'per_question';
      }
    } catch { /* no config yet */ }
    loading = false;
  });

  async function validateKey() {
    if (!apiKey.trim()) return;
    keyChecking = true;
    error = '';
    try {
      const res = await api.config.validate(provider, apiKey);
      if (res.valid) {
        availableModels = res.models || [];
        success = `Key valid — ${availableModels.length} models available`;
      } else {
        error = (res as any).error || 'Invalid API key';
      }
    } catch (e: any) {
      error = e.message || 'Validation failed';
    }
    keyChecking = false;
  }

  async function save() {
    saving = true;
    error = '';
    success = '';
    const config = {
      provider: {
        active: provider,
        openai: {
          api_key: provider === 'openai' ? apiKey : '',
          models: provider === 'openai' ? { judge: judgeModel, target: targetModel, converser: converserModel, fetcher: fetcherModel, researcher: researcherModel } : { judge: '', target: '', converser: '', fetcher: '', researcher: '' },
        },
        openrouter: {
          api_key: provider === 'openrouter' ? apiKey : '',
          models: provider === 'openrouter' ? { judge: judgeModel, target: targetModel, converser: converserModel, fetcher: fetcherModel, researcher: researcherModel } : { judge: '', target: '', converser: '', fetcher: '', researcher: '' },
        },
      },
      search: {
        brave: { api_key: braveKey },
        perplexity: { api_key: perplexityKey },
      },
      orchestration: {
        questions_per_loop: questionsPerLoop,
        tone_rotation: toneRotation,
        score_threshold: scoreThreshold,
        max_loops: maxLoops,
        plateau_window: plateauWindow,
        soul_max_words: soulMaxWords,
      },
      output: { directory: './output' },
    };
    try {
      await api.config.save(config);
      success = 'Settings saved. Background runners restarted with new config.';
    } catch (e: any) {
      error = e.message || 'Failed to save';
    }
    saving = false;
  }
</script>

{#if loading}
  <p>Loading...</p>
{:else}
  <h1>Settings</h1>

  {#if error}<div class="msg error">{error}</div>{/if}
  {#if success}<div class="msg success">{success}</div>{/if}

  <div class="sections">
    <section>
      <h2>LLM Provider</h2>
      <div class="radio-group">
        <label><input type="radio" bind:group={provider} value="openai" /> OpenAI</label>
        <label><input type="radio" bind:group={provider} value="openrouter" /> OpenRouter</label>
      </div>

      <label class="field-label">API Key</label>
      {#if redactedKey && !apiKey}
        <p class="current-value">Current: {redactedKey}</p>
      {/if}
      <div class="key-row">
        <input type="password" bind:value={apiKey} placeholder="Enter new key to change..." />
        <button onclick={validateKey} disabled={keyChecking || !apiKey.trim()}>
          {keyChecking ? 'Checking...' : 'Validate'}
        </button>
      </div>
      <p class="hint">Leave blank to keep current key.</p>
    </section>

    <section>
      <h2>Model Assignment</h2>
      <p class="hint">Type model IDs directly, or validate your key above to get a dropdown.</p>

      {#if availableModels.length > 0}
        <div class="grid-2">
          <div>
            <label class="field-label">Judge (High)</label>
            <select bind:value={judgeModel}>
              <option value="">Select...</option>
              {#each availableModels as m}<option value={m}>{m}</option>{/each}
            </select>
          </div>
          <div>
            <label class="field-label">Researcher (High)</label>
            <select bind:value={researcherModel}>
              <option value="">Select...</option>
              {#each availableModels as m}<option value={m}>{m}</option>{/each}
            </select>
          </div>
          <div>
            <label class="field-label">Target (Medium)</label>
            <select bind:value={targetModel}>
              <option value="">Select...</option>
              {#each availableModels as m}<option value={m}>{m}</option>{/each}
            </select>
          </div>
          <div>
            <label class="field-label">Converser (Low-Med)</label>
            <select bind:value={converserModel}>
              <option value="">Select...</option>
              {#each availableModels as m}<option value={m}>{m}</option>{/each}
            </select>
          </div>
          <div>
            <label class="field-label">Fetcher (Low-Med)</label>
            <select bind:value={fetcherModel}>
              <option value="">Select...</option>
              {#each availableModels as m}<option value={m}>{m}</option>{/each}
            </select>
          </div>
        </div>
      {:else}
        <div class="grid-2">
          <div>
            <label class="field-label">Judge (High)</label>
            <input bind:value={judgeModel} placeholder="e.g., gpt-4o" />
          </div>
          <div>
            <label class="field-label">Researcher (High)</label>
            <input bind:value={researcherModel} placeholder="e.g., gpt-4o" />
          </div>
          <div>
            <label class="field-label">Target (Medium)</label>
            <input bind:value={targetModel} placeholder="e.g., gpt-4o-mini" />
          </div>
          <div>
            <label class="field-label">Converser (Low-Med)</label>
            <input bind:value={converserModel} placeholder="e.g., gpt-4o-mini" />
          </div>
          <div>
            <label class="field-label">Fetcher (Low-Med)</label>
            <input bind:value={fetcherModel} placeholder="e.g., gpt-4o-mini" />
          </div>
        </div>
      {/if}
    </section>

    <section>
      <h2>Search Providers</h2>
      <p class="hint">Leave blank to keep current keys.</p>
      <div class="grid-2">
        <div>
          <label class="field-label">Brave API Key</label>
          {#if redactedBrave && !braveKey}
            <p class="current-value">Current: {redactedBrave}</p>
          {/if}
          <input type="password" bind:value={braveKey} placeholder="Enter new key..." />
        </div>
        <div>
          <label class="field-label">Perplexity API Key</label>
          {#if redactedPerplexity && !perplexityKey}
            <p class="current-value">Current: {redactedPerplexity}</p>
          {/if}
          <input type="password" bind:value={perplexityKey} placeholder="Enter new key..." />
        </div>
      </div>
    </section>

    <section>
      <h2>Orchestration</h2>
      <div class="grid-2">
        <div>
          <label class="field-label">Questions per loop</label>
          <input type="number" bind:value={questionsPerLoop} min="2" max="12" />
        </div>
        <div>
          <label class="field-label">Score threshold</label>
          <input type="number" bind:value={scoreThreshold} min="0.5" max="1.0" step="0.05" />
        </div>
        <div>
          <label class="field-label">Max loops</label>
          <input type="number" bind:value={maxLoops} min="3" max="50" />
        </div>
        <div>
          <label class="field-label">Plateau window</label>
          <input type="number" bind:value={plateauWindow} min="2" max="10" />
        </div>
        <div>
          <label class="field-label">SOUL.md max words</label>
          <input type="number" bind:value={soulMaxWords} min="500" max="4000" step="100" />
        </div>
        <div>
          <label class="field-label">Tone rotation</label>
          <select bind:value={toneRotation}>
            <option value="per_question">Per question</option>
            <option value="per_2_questions">Per 2 questions</option>
          </select>
        </div>
      </div>
    </section>

    <div class="save-bar">
      <button class="primary" onclick={save} disabled={saving}>
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  </div>
{/if}

<style>
  h1 { font-size: 1.25rem; font-weight: 600; margin-bottom: 1.5rem; }
  h2 { font-size: 0.9375rem; font-weight: 600; margin-bottom: 0.5rem; }
  .hint { color: var(--text-secondary); font-size: 0.8125rem; }
  .sections { display: flex; flex-direction: column; gap: 2rem; max-width: 40rem; }
  section { display: flex; flex-direction: column; gap: 0.625rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
  .field-label { font-size: 0.75rem; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.03em; }
  .radio-group { display: flex; gap: 1.5rem; }
  .radio-group label { display: flex; align-items: center; gap: 0.375rem; font-size: 0.875rem; cursor: pointer; }
  .radio-group input { width: auto; }
  .key-row { display: flex; gap: 0.5rem; }
  .key-row input { flex: 1; }
  .key-row button { white-space: nowrap; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  select { width: 100%; }
  .save-bar { padding-top: 1rem; }
  .msg { padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-size: 0.8125rem; margin-bottom: 1rem; }
  .msg.error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
  .msg.success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
  .current-value { font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-secondary); background: var(--bg-inset); padding: 0.25rem 0.5rem; border-radius: 0.25rem; }
</style>
