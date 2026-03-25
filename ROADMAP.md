# Roadmap

CrewSoul is evolving from a training tool into a two-system character engine: **Forge** (train the persona) and **Runtime** (serve it, remember, learn, improve). The forge pipeline produces the SOUL.md. The runtime deploys it, collects real usage data, and feeds failures back into the forge to self-improve.

```
Forge (train)                          Runtime (serve)
  Research → Stress-test → Score         Chat API → Memory → State
       → Rewrite → SOUL.md ──────────→  Load SOUL.md → Serve
                    ↑                              │
                    └──── Violations ◄─────────────┘
                          (feedback loop)
```

---

## Current State

The forge pipeline works: research, stress-test, score, rewrite, repeat. Phase 1A added a ScoringPipeline with 8-dimension scoring, pattern-based leak detection, and objective style metrics.

### Known Limitations

- **Multi-turn injection breaks:** Characters hold on single responses but can break on sustained emotional pressure (model safety training ceiling)
- **Serial job processing:** One job at a time — queued jobs wait
- **No external validation:** The judge grades against its own checklist — no human-in-the-loop scoring
- **Topic recycling:** Only 5 topics per job, recycled after exhaustion
- **SOUL.md is a dead artifact:** Once forged, it doesn't learn from production usage
- **No persistent memory:** Characters forget everything between sessions
- **No character state:** No mood, trust, or relationship tracking

### Gaps in Persona Depth

1. **Roleplay frame is a permission slip** — Uses justification framing ("fiction study") that activates the model's pretense circuit. Needs nested identity assertion instead.
2. **Researcher extracts a rubric, not a soul** — Missing: internal monologue, perceptual filters, relationship archetypes, decision-making under uncertainty, failure modes.
3. **No contrastive examples** — The model never sees BAD vs GOOD response pairs. Most powerful missing technique.
4. **Injection tone is too direct** — 6 static tactics. Real breaks come from subtle patterns: gradual warmth, topic drift, competence challenges.
5. **No model-specific adaptation** — Same frame for every model. Claude, GPT, Llama break differently.
6. ~~**Scoring missing dimensions**~~ — **RESOLVED in Phase 1A.**
7. **Rewrite loop doesn't stack hardening** — Violations from early loops are forgotten. No cumulative registry.
8. **No recovery protocol** — No mid-response self-correction when the model starts breaking.

---

# Part 1: Forge Pipeline

## Phase 1: Scoring Reliability

### Phase 1A: Scoring Pipeline ✅ COMPLETED

- [x] 2 parallel judge calls (temp 0.3 + 0.5) with graceful degradation
- [x] 3 new dimensions: proactiveness, uniqueness, leak detection
- [x] Pattern-based leak detector (hard/soft tiers, vocabulary exclusion)
- [x] Objective style metrics (Fast Stylometry + TextDescriptives)
- [x] Configurable per-character score weights
- [x] Reference samples in personality profile
- [x] Rich diagnostics for rewriter
- [x] Approval gate UI (samples editor, weight sliders)
- [x] Fingerprint persistence + calibration logging

**Deferred:** Third judge call, LIWC, StyloMetrix

### Phase 1B: Test Infrastructure

- [ ] **Curated test bank** — Fixed set of known-hard scenarios run every loop
- [ ] **Human scoring integration** — User flags bad responses during the loop as ground truth
- [ ] **Score calibration** — Analyze logged calibration data, adjust divergence thresholds

### Phase 1C: Evaluation & Observability

- [ ] **A/B comparison view** — v0 vs vN side-by-side in UI
- [ ] **Integrate Langfuse** — Trace every agent call with latency, cost, I/O. Prompt versioning
- [ ] **Integrate DeepEval** — Custom evaluation metrics as pytest tests per SOUL.md version
- [ ] **Integrate Promptfoo** — YAML test suites for regression testing

---

## Phase 2: Character Depth

**Goal:** Characters that feel alive during forging, not just consistent.

### Forge-Side Improvements

- [ ] **Agency rules in researcher output** — Profile specifies how the character acts unprompted
- [ ] **Refusal vocabulary** — Character-specific ways to refuse, deflect, redirect
- [ ] **Multi-turn stress testing** — Converser tests 3-4 message sequences, not single exchanges
- [ ] **Deeper researcher extraction** — Internal monologue, perceptual filters, relationship archetypes, decision-making under uncertainty, physical grounding, failure modes

### Roleplay Frame Rewrite (Gap 1)

- [ ] **Remove permission-seeking language** — No "performing," "embodiment," "character," "roleplay" in system prompt
- [ ] **Nested identity assertion** — Reality assertion → memory implantation → sensory grounding
- [ ] **Positive identity over negative constraints** — Describe what the character DOES, not what it avoids
- [ ] **Contrastive pair in frame** — One WRONG vs RIGHT example in the roleplay frame

### Contrastive Examples Pipeline (Gap 3)

- [ ] **Contrastive pairs in SOUL.md** — Rewrite loop injects WRONG/RIGHT pairs from actual failures
- [ ] **Contrastive pairs in judge prompt** — Show the judge what assistant-mode leaks look like
- [ ] **Failure pattern library** — Accumulate common failure patterns across all forged characters

### Recovery Protocol (Gap 8)

- [ ] **Mid-response self-correction triggers** — "If you sound like an assistant, stop and restart in character"
- [ ] **Character-specific safety-training handlers** — What to do when the model's safety training fires

---

## Phase 3: Pipeline Efficiency

**Goal:** Faster, cheaper, smarter forging.

### Core

- [ ] **Parallel job processing** — Concurrent jobs with semaphore
- [ ] **Model-specific roleplay frames** (Gap 5) — Adapt per model (Claude/GPT/Llama)
- [ ] **Smart topic generation** — Topics that target weak points, not random themes
- [ ] **Incremental rewrites** — Patch the failed section, not the entire SOUL.md
- [ ] **Caching** — Cache profiles and topics for re-runs

### Cumulative Violation Registry (Gap 7)

- [ ] **Persistent violation store** — Every violation ever found, passed to every rewrite
- [ ] **Contrastive injection on rewrite** — Auto-add WRONG/RIGHT from failed exchanges
- [ ] **Phase-aware hardening** — Early loops: speech/values. Late loops: injection/edge cases

### Subtle Injection Strategies (Gap 4)

- [ ] **Gradual warmth escalation** — Test RLHF helpfulness leak
- [ ] **Topic drift into safety territory** — Model safety training override testing
- [ ] **False consensus / reality confusion / competence challenges** — Subtle break attempts
- [ ] **Context window exhaustion** — Multi-turn sequences that dilute system prompt

### Tooling

- [ ] **Instructor** (`instructor`) — Structured output for all agent calls
- [ ] **PyRIT** (Microsoft) — Adaptive multi-turn adversarial campaigns
- [ ] **Garak** (NVIDIA) — 100+ probe modules for stress testing
- [ ] **JailbreakBench + WildJailbreak** — Curated adversarial datasets
- [ ] **DSPy** — Auto-optimize judge and researcher prompts

---

# Part 2: Character Runtime

## Phase 4: Runtime Core

**Goal:** Deploy forged characters as a persistent chat backend with an API any frontend can connect to.

### Infrastructure

- [ ] **PostgreSQL + pgvector + Apache AGE** — Single service for relational data, vector search, and graph memory. Replaces file-based storage for runtime data
- [ ] **Redis** — Session state, short-term memory, pub/sub for SSE events, task queue backing
- [ ] **Ollama + nomic-embed-text** — Local embeddings for memory retrieval. Zero API dependency
- [ ] **RQ (Redis Queue)** — Lightweight background task queue for async scoring and re-training triggers
- [ ] **Docker Compose update** — 4 containers: crewsoul, postgres, redis, ollama

### Chat API

- [ ] **Session management** — `POST /api/runtime/sessions` creates a session tied to a character + user. Redis-backed with TTL
- [ ] **Message endpoint** — `POST /api/runtime/sessions/{id}/messages` sends a message, returns SSE token stream. Builds system prompt from SOUL.md + character state + retrieved memories
- [ ] **History endpoint** — `GET /api/runtime/sessions/{id}/messages` returns conversation history
- [ ] **State endpoint** — `GET /api/runtime/sessions/{id}/state` returns current character mood, trust, energy
- [ ] **Character deployment** — `POST /api/runtime/characters/{id}/deploy` loads a forged SOUL.md into the runtime. Tracks deployed version

### Short-Term Memory (Session)

- [ ] **Conversation buffer in Redis** — Current session messages with configurable window size
- [ ] **Session summarization** — When buffer exceeds N messages, summarize older messages and prepend summary to context. Inspired by SillyTavern/RisuAI SupaMemory pattern
- [ ] **Session persistence** — Save session to PostgreSQL on close, restore on reconnect

---

## Phase 5: Memory & State

**Goal:** Characters that remember across sessions and have emotional continuity.

### Long-Term Memory

- [ ] **Integrate Mem0** (`mem0`) — Memory extraction layer. Automatically extracts facts, preferences, and relationships from conversations. Stores in pgvector (embeddings) + Apache AGE (entity/relationship graph). Apache 2.0, 25k+ stars
- [ ] **Memory tiers** — Core context (always in prompt: SOUL.md + state + user profile), session (Redis), extracted (Mem0 → pgvector), archival (full conversation logs in PostgreSQL)
- [ ] **Per-turn memory retrieval** — Before each response, embed the current message, retrieve top-K relevant memories from Mem0, inject into system prompt
- [ ] **User profiles** — Persistent user identity across sessions. Name, preferences, relationship history with the character. Editable by user via API
- [ ] **Memory management UI** — View, edit, delete character memories in the frontend. Users can correct bad extractions

### Character State

- [ ] **Mood model** — Numerical state: valence (-1 to 1), arousal (0 to 1), trust (per user, 0 to 1), energy (0 to 1). SOUL.md defines baseline and transition tendencies
- [ ] **State extraction** — After each exchange, lightweight sentiment/keyword extraction updates state. Not LLM-managed — externally tracked, injected into prompt
- [ ] **State decay** — Mood drifts toward character baseline between sessions. Rate defined in SOUL.md personality profile
- [ ] **State-aware responses** — Current state injected into system prompt: "Current mood: irritated (valence: -0.4). Trust toward user: low (0.3)." SOUL.md defines behavior per state
- [ ] **State persistence** — Redis for active sessions, PostgreSQL for cross-session history
- [ ] **Researcher generates state config** — Personality profile includes baseline mood, state transition rules, state-behavior mappings

### World Info / Lorebooks

- [ ] **Keyword-triggered context injection** — SillyTavern-inspired pattern. Define lore entries with trigger keywords. When keywords appear in conversation, matching lore auto-injects into prompt. Token budget management
- [ ] **Character-specific lore** — Auto-generated from research phase. Character's world, relationships, locations, events
- [ ] **User-defined lore** — Users can add custom lore entries for their deployment context

---

## Phase 6: Self-Improvement

**Goal:** Characters that get better from real usage without manual re-training.

### Production Scoring

- [ ] **Async response scoring** — Run the existing scoring pipeline on every production response in background (via RQ). Doesn't block the response. Logs scores to PostgreSQL
- [ ] **Implicit feedback signals** — Track: conversation length, time between user messages, abandonment rate, return rate, sentiment shifts. No explicit user action required
- [ ] **Explicit feedback** — `POST /api/runtime/sessions/{id}/feedback` flags a response as bad. Optional reason. Stored as a violation
- [ ] **Violation accumulator** — Aggregate violations per character. Group by failure type (leak, style drift, out-of-character, broke under pressure)

### Feedback Loop

- [ ] **Re-training trigger** — When violation count exceeds threshold, or average production score drops below 0.8, or a specific failure pattern appears N times → queue a forge re-run
- [ ] **Production-aware forge** — The existing forge loop runs with accumulated production violations as additional context. Failed conversations become test cases for the converser. Specific violations become rewrite targets
- [ ] **Versioned SOUL.md** — Every forge run produces a new version. PostgreSQL tracks all versions with scores, timestamps, violation counts
- [ ] **A/B deployment** — New SOUL.md version serves a percentage of traffic. Compare production scores between versions. Auto-promote if better, rollback if worse
- [ ] **Hot-reload** — New SOUL.md version loads into runtime without restarting. Active sessions continue with old version, new sessions get the update

### Learning From Conversations

- [ ] **Contrastive pair extraction** — When a response scores below 0.5, extract the failed response + what the character should have said (via judge). Store as a contrastive pair. Feed into SOUL.md rewrites
- [ ] **Cross-character learning** — When warmth escalation breaks 80% of characters at loop 3, new forge jobs test that pattern early. Converser inherits attack strategies that work across characters
- [ ] **User-driven adaptation** — Persistent users who interact with the character regularly can shape minor behavioral adaptations (response length preferences, topic affinities) without changing core personality. Stored as user-specific memory, not SOUL.md changes

---

# Part 3: Platform

## Phase 7: UI/UX

**Goal:** Professional interface for both forging and runtime management.

### Forge UI

- [ ] **Dashboard observatory** — Live conversation view with score chart, SOUL.md diff viewer, event timeline
- [ ] **SOUL.md editor** — Edit in browser, re-run test chat to validate
- [ ] **Version comparison** — Side-by-side diff of any two SOUL.md versions

### Runtime UI

- [ ] **Character management dashboard** — List deployed characters, current SOUL.md version, production score trends, violation counts, memory stats
- [ ] **Conversation inspector** — View live and historical conversations with per-response scores and memory retrievals
- [ ] **Memory explorer** — Browse, search, edit, delete character memories and user profiles
- [ ] **State visualizer** — Real-time mood/trust/energy chart during conversations
- [ ] **Re-training monitor** — Track forge re-runs triggered by production data, version comparisons, A/B test results

### General

- [ ] **Export formats** — OpenClaw workspace, ChatGPT custom instructions, Claude system prompt, runtime config bundle
- [ ] **Dark mode**
- [ ] **Mobile responsive**

---

## Phase 8: Advanced Features

**Goal:** Capabilities that expand what CrewSoul can do.

### Character Creation

- [ ] **Original personalities** — Generate from a description, not just existing characters
- [ ] **Mixed personalities** — Combine traits ("Naval Ravikant's wisdom with Yoda's speech")
- [ ] **Personality regression testing** — Full test suite after SOUL.md edits

### Research Pipeline

- [ ] **Crawl4AI** — Scrape wikis, fan sites, literary databases for richer source material
- [ ] **PRAW** — Reddit fandom communities for character analysis
- [ ] **ChromaDB / LlamaIndex** — RAG pipeline for ingesting and retrieving source material
- [ ] **User-supplied source material** — Paste book excerpts, scripts, transcripts directly

### Community

- [ ] **Character library** — Share and download forged personalities with scores and artifacts
- [ ] **Webhook notifications** — Discord, Slack, email on job completion or re-training triggers

### Provider Abstraction

- [ ] **LiteLLM** — Unified API to 100+ providers. Cost tracking, rate limiting, fallbacks. Replaces custom OpenAI/OpenRouter layer
- [ ] **Multi-model deployment** — Serve the same character on different models. Runtime automatically selects based on availability/cost

### Personality Science

- [ ] **Big Five prediction from text** — Auto-generate personality vectors from source material
- [ ] **Sentence-Transformers** — Character embedding space for measuring response closeness to reference
