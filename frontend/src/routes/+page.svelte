<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';

  let step = $state(1);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state('');

  // Provider
  let provider = $state('openai');
  let apiKey = $state('');
  let keyValid = $state(false);
  let keyChecking = $state(false);
  let availableModels: string[] = $state([]);

  // Model assignments
  let judgeModel = $state('');
  let targetModel = $state('');
  let converserModel = $state('');
  let fetcherModel = $state('');
  let researcherModel = $state('');

  // Search
  let braveKey = $state('');
  let perplexityKey = $state('');

  // Orchestration
  let questionsPerLoop = $state(6);
  let scoreThreshold = $state(0.9);
  let maxLoops = $state(15);
  let plateauWindow = $state(3);
  let soulMaxWords = $state(2000);
  let toneRotation = $state('per_question');

  onMount(async () => {
    try {
      const res = await api.config.get();
      if (res.configured) goto('/dashboard');
    } catch { /* first run */ }
    loading = false;
  });

  async function validateKey() {
    if (!apiKey.trim()) return;
    keyChecking = true;
    error = '';
    try {
      const res = await api.config.validate(provider, apiKey);
      keyValid = res.valid;
      availableModels = res.models || [];
      if (!keyValid) error = (res as any).error || 'Invalid API key — check the key and try again';
    } catch (e: any) {
      error = e.message || 'Validation failed — network error';
      keyValid = false;
    }
    keyChecking = false;
  }

  function skipValidation() {
    keyValid = true;
    availableModels = [];
  }

  async function save() {
    saving = true;
    error = '';
    if (!braveKey && !perplexityKey) {
      error = 'At least one search key (Brave or Perplexity) is required';
      saving = false;
      return;
    }
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
      goto('/queue');
    } catch (e: any) {
      error = e.message || 'Failed to save config';
    }
    saving = false;
  }
</script>

{#if loading}
  <p>Loading...</p>
{:else}
  <div class="wizard">
    <h1>CrewSoul Setup</h1>
    <div class="steps">
      <span class="step" class:active={step === 1} class:done={step > 1}>1. Provider</span>
      <span class="sep">/</span>
      <span class="step" class:active={step === 2} class:done={step > 2}>2. Models</span>
      <span class="sep">/</span>
      <span class="step" class:active={step === 3} class:done={step > 3}>3. Search</span>
      <span class="sep">/</span>
      <span class="step" class:active={step === 4}>4. Tuning</span>
    </div>

    {#if error}
      <div class="error">{error}</div>
    {/if}

    {#if step === 1}
      <div class="section">
        <h2>LLM Provider</h2>
        <p class="hint">Select your provider and enter your API key.</p>

        <label class="field-label">Provider</label>
        <div class="radio-group">
          <label><input type="radio" bind:group={provider} value="openai" onchange={() => { keyValid = false; availableModels = []; }} /> OpenAI</label>
          <label><input type="radio" bind:group={provider} value="openrouter" onchange={() => { keyValid = false; availableModels = []; }} /> OpenRouter</label>
        </div>

        <label class="field-label">API Key</label>
        <div class="key-row">
          <input type="password" bind:value={apiKey} placeholder={provider === 'openai' ? 'sk-...' : 'or-...'} />
          <button onclick={validateKey} disabled={keyChecking || !apiKey.trim()}>
            {keyChecking ? 'Checking...' : keyValid ? 'Valid' : 'Validate'}
          </button>
        </div>
        {#if keyValid && availableModels.length > 0}
          <p class="success">{availableModels.length} models available</p>
        {:else if keyValid}
          <p class="success">Key accepted (skipped validation) — enter model names manually</p>
        {/if}

        <div class="nav-buttons">
          {#if !keyValid && apiKey.trim()}
            <button onclick={skipValidation}>Skip validation</button>
          {:else}
            <div></div>
          {/if}
          <button class="primary" onclick={() => { step = 2; }} disabled={!keyValid || !apiKey.trim()}>Next</button>
        </div>
      </div>

    {:else if step === 2}
      <div class="section">
        <h2>Model Assignment</h2>
        <p class="hint">Assign models to each agent role. Judge + Researcher need the smartest model. Converser + Fetcher can use cheaper ones.</p>

        {#if availableModels.length > 0}
          <label class="field-label">Judge (High tier — scores and rewrites)</label>
          <select bind:value={judgeModel}>
            <option value="">Select model...</option>
            {#each availableModels as m}<option value={m}>{m}</option>{/each}
          </select>

          <label class="field-label">Researcher (High tier — profiles characters)</label>
          <select bind:value={researcherModel}>
            <option value="">Select model...</option>
            {#each availableModels as m}<option value={m}>{m}</option>{/each}
          </select>

          <label class="field-label">Target (Medium tier — the personality being shaped)</label>
          <select bind:value={targetModel}>
            <option value="">Select model...</option>
            {#each availableModels as m}<option value={m}>{m}</option>{/each}
          </select>

          <label class="field-label">Converser (Low-Med tier — generates pressure)</label>
          <select bind:value={converserModel}>
            <option value="">Select model...</option>
            {#each availableModels as m}<option value={m}>{m}</option>{/each}
          </select>

          <label class="field-label">Fetcher (Low-Med tier — synthesizes research)</label>
          <select bind:value={fetcherModel}>
            <option value="">Select model...</option>
            {#each availableModels as m}<option value={m}>{m}</option>{/each}
          </select>
        {:else}
          <p class="hint">Enter model IDs manually (e.g., gpt-4o, gpt-4o-mini).</p>

          <label class="field-label">Judge (High tier)</label>
          <input bind:value={judgeModel} placeholder="e.g., gpt-4o" />

          <label class="field-label">Researcher (High tier)</label>
          <input bind:value={researcherModel} placeholder="e.g., gpt-4o" />

          <label class="field-label">Target (Medium tier)</label>
          <input bind:value={targetModel} placeholder="e.g., gpt-4o-mini" />

          <label class="field-label">Converser (Low-Med tier)</label>
          <input bind:value={converserModel} placeholder="e.g., gpt-4o-mini" />

          <label class="field-label">Fetcher (Low-Med tier)</label>
          <input bind:value={fetcherModel} placeholder="e.g., gpt-4o-mini" />
        {/if}

        <div class="nav-buttons">
          <button onclick={() => { step = 1; }}>Back</button>
          <button class="primary" onclick={() => { step = 3; }} disabled={!judgeModel || !targetModel || !converserModel || !fetcherModel || !researcherModel}>Next</button>
        </div>
      </div>

    {:else if step === 3}
      <div class="section">
        <h2>Search Providers</h2>
        <p class="hint">At least one is required. Brave = raw search results. Perplexity = AI-synthesized research.</p>

        <label class="field-label">Brave API Key (normal search)</label>
        <input type="password" bind:value={braveKey} placeholder="BSA..." />

        <label class="field-label">Perplexity API Key (smart search)</label>
        <input type="password" bind:value={perplexityKey} placeholder="pplx-..." />

        <div class="nav-buttons">
          <button onclick={() => { step = 2; }}>Back</button>
          <button class="primary" onclick={() => { step = 4; }} disabled={!braveKey && !perplexityKey}>Next</button>
        </div>
      </div>

    {:else if step === 4}
      <div class="section">
        <h2>Orchestration Tuning</h2>
        <p class="hint">Defaults work well. Adjust if needed.</p>

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

        <div class="nav-buttons">
          <button onclick={() => { step = 3; }}>Back</button>
          <button class="primary" onclick={save} disabled={saving}>
            {saving ? 'Saving...' : 'Save & Start'}
          </button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .wizard { max-width: 36rem; margin: 2rem auto; }
  h1 { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.75rem; }
  h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; }
  .hint { color: var(--text-secondary); font-size: 0.8125rem; margin-bottom: 1.25rem; }
  .steps { display: flex; gap: 0.25rem; align-items: center; margin-bottom: 1.5rem; font-size: 0.8125rem; color: var(--text-muted); }
  .step.active { color: var(--accent); font-weight: 600; }
  .step.done { color: var(--success); }
  .sep { color: var(--border); }
  .section { display: flex; flex-direction: column; gap: 0.75rem; }
  .field-label { font-size: 0.75rem; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 0.25rem; }
  .radio-group { display: flex; gap: 1.5rem; }
  .radio-group label { display: flex; align-items: center; gap: 0.375rem; font-size: 0.875rem; cursor: pointer; }
  .radio-group input { width: auto; }
  .key-row { display: flex; gap: 0.5rem; }
  .key-row input { flex: 1; }
  .key-row button { white-space: nowrap; }
  .nav-buttons { display: flex; justify-content: space-between; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
  .error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-size: 0.8125rem; }
  .success { color: var(--success); font-size: 0.8125rem; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  select { width: 100%; }
</style>
