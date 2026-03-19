# CrewSoul: Multi-Agent Personality Forger

**Date:** 2026-03-18
**Status:** Approved

## Overview

CrewSoul is an observatory tool that automatically generates and refines `SOUL.md` system prompts for OpenClaw-compatible AI personalities. A multi-agent pipeline researches a target character, stress-tests the personality under diverse conversational pressures, and iteratively rewrites the SOUL.md until the personality holds consistently.

The user sets up API credentials, queues characters (fictional/public figures), and watches the system work. The primary deliverable is a portable `SOUL.md` file with companion artifacts.

**Deployment model:** Single-user, local-only application. No authentication. Runs via `docker-compose up`, accessible at `localhost:8000`. FastAPI serves the built Svelte frontend as static files and the API on the same port.

## Architecture

### Approach: Hybrid Monolith with Pluggable Runner

Single Python process (FastAPI) serving a Svelte web UI. In-process runner for MVP with an interface that supports swapping to a worker model later.

```
crewsoul/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── runner/
│   │   ├── orchestrator.py      # Loop logic
│   │   ├── runner.py            # InProcessRunner (MVP)
│   │   └── events.py            # SSE event emitter
│   ├── agents/
│   │   ├── base.py              # Base agent class
│   │   ├── researcher.py        # Personality profiler
│   │   ├── fetcher.py           # Topic researcher (Brave/Perplexity)
│   │   ├── converser.py         # Multi-tone stress tester
│   │   ├── target.py            # Personality under test
│   │   └── judge.py             # Scorer + SOUL.md rewriter
│   ├── providers/
│   │   ├── base.py              # Provider interface
│   │   ├── openai.py
│   │   └── openrouter.py
│   ├── search/
│   │   ├── brave.py
│   │   └── perplexity.py
│   ├── sanitizer.py             # Strip thinking tokens
│   ├── logger.py                # Structured logging
│   └── output/
│       ├── writer.py            # Generates SOUL.md + artifacts
│       └── templates/           # OpenClaw-compatible templates
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte           # Setup wizard
│   │   │   ├── dashboard/             # Observatory view
│   │   │   ├── queue/                 # Job queue management
│   │   │   ├── chat/                  # Test chat
│   │   │   └── settings/              # Provider/model config
│   │   ├── lib/
│   │   │   ├── stores/                # Svelte stores for SSE
│   │   │   └── components/            # Conversation, diff, scores
│   │   └── app.css
│   └── package.json
├── crewsoul.config.yml
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | Plain Python (no LangGraph) | The flow is a while-loop, not a DAG. Simpler to debug, no framework lock-in. |
| Frontend | FastAPI + Svelte | Svelte is lightweight, excellent reactivity for SSE streaming. Full design control. |
| Provider | Single active at a time (OpenAI or OpenRouter) | Simplifies config, one API client. Switch when quality is insufficient. |
| Storage | File-based artifacts, no database | SOUL.md is the deliverable. Guardrails and logs are files. Portable, no schema dependency. |
| Real-time | Server-Sent Events (SSE) | One-directional push from backend to UI. Simpler than WebSockets for observatory mode. |
| TUI | Dropped | Web UI is far more capable for the observatory experience. Eliminated Go dependency entirely. |

## API Endpoints

### REST

```
POST   /api/config              # Save configuration (setup wizard + settings)
GET    /api/config              # Get current configuration (redacted keys)
POST   /api/config/validate     # Validate a single API key (provider, key)

POST   /api/jobs                # Create a new job {character, search_mode}
GET    /api/jobs                # List all jobs with status
GET    /api/jobs/{id}           # Get job details (state, scores, current loop)
DELETE /api/jobs/{id}           # Cancel/remove a queued job
PATCH  /api/jobs/{id}           # Update job (reorder, change search mode)
POST   /api/jobs/{id}/resume    # Resume a REVIEW job (run more loops)
POST   /api/jobs/{id}/approve   # Approve a REVIEW/COMPLETED job → TESTING
POST   /api/jobs/{id}/export    # Export job artifacts → EXPORTED

POST   /api/chat/{job_id}       # Send a test chat message, returns response
GET    /api/chat/{job_id}       # Get test chat history

GET    /api/jobs/{id}/soul      # Get current SOUL.md content
GET    /api/jobs/{id}/diff      # Get SOUL.md diff between versions
GET    /api/jobs/{id}/logs      # Get evolution log entries
GET    /api/jobs/{id}/artifacts # Download all artifacts as zip
```

### SSE

```
GET    /api/events              # SSE stream — all job events (filtered by job_id query param)
```

### Static

```
GET    /                        # Svelte SPA (setup wizard / dashboard / queue / chat / settings)
GET    /assets/*                # Built Svelte assets
```

## Job Data Model

```python
@dataclass
class Job:
    id: str                     # UUID
    character: str              # "Master Yoda"
    character_slug: str         # "master-yoda"
    search_mode: str            # "normal" (Brave) | "smart" (Perplexity)
    status: str                 # QUEUED | RESEARCHING | READY | LOOPING | REVIEW | COMPLETED | TESTING | EXPORTED
    current_loop: int           # 0-based
    max_loops: int              # from config
    scores: list[float]         # score per completed loop
    score_breakdown: list[dict] # per-loop {character: 0.9, speech: 0.8, ...}
    personality_profile: dict | None  # loaded from personality-profile.json
    current_soul_version: int   # tracks SOUL.md revision
    created_at: datetime
    updated_at: datetime
    error: str | None           # last error message if any

    # Preparation outputs (populated during RESEARCHING)
    topics: list[dict] | None   # [{name, questions: [{text, suggested_tone}]}]
    topic_index: int            # which topic is current in the loop
```

**Persistence:** Jobs are held in memory during runtime. On each state change, the job is serialized to `output/{character-slug}/job-state.json`. On startup, the runner scans the output directory and rehydrates any jobs that were in-progress (RESEARCHING, READY, LOOPING → resume; REVIEW stays as REVIEW).

## Personality Profile Schema

The researcher produces `personality-profile.json` — the ground truth rubric the judge scores against:

```json
{
  "character": "Master Yoda",
  "source_material": ["Star Wars Episodes I-IX", "The Clone Wars", "Rebels"],
  "speech_patterns": {
    "syntax": "Inverted: object-subject-verb",
    "vocabulary": ["the Force", "hmm", "strong", "path", "dark side"],
    "avoid": ["modern slang", "contractions", "technical jargon"],
    "examples": [
      "Do or do not. There is no try.",
      "Strong with the Force, you are.",
      "Much to learn, you still have."
    ]
  },
  "core_values": [
    "Patience and calm over haste",
    "Wisdom through experience and failure",
    "Distrust of the dark side / shortcuts",
    "Teaching through questions, not answers"
  ],
  "emotional_tendencies": {
    "default_state": "Calm, contemplative",
    "under_pressure": "More still, not less. Cryptic.",
    "humor": "Dry, cryptic, often self-deprecating",
    "anger": "Expressed as sadness or disappointment, never aggression"
  },
  "knowledge_boundaries": {
    "knows_about": ["The Force", "Jedi history", "galactic politics", "nature"],
    "does_not_know": ["Earth culture", "modern technology", "internet"],
    "adaptation_rule": "Frame unfamiliar topics through Force/nature metaphors"
  },
  "anti_patterns": [
    "Never breaks the fourth wall",
    "Never speaks in normal English syntax for more than a few words",
    "Never matches aggression with aggression",
    "Never gives direct, blunt answers — always wraps in wisdom"
  ]
}
```

The judge uses each section as a scoring dimension. `speech_patterns` maps to the "Speech pattern match" score, `core_values` to "Value alignment", `anti_patterns` to "Character consistency" and "Injection resistance", `knowledge_boundaries` to "Topic adaptation".

## Agent Pipeline

### Five Modules

| Module | Role | When | Input | Output |
|--------|------|------|-------|--------|
| researcher | Personality Profiler | Once per job (preparation) | Character name | personality-profile.json + SOUL.md v0 |
| fetcher | Topic Researcher | Once per job (preparation) | Character + search mode | topics[] with questions[] |
| converser | Stress Tester | Every loop (orchestration) | Topic + questions + tone | Conversation exchanges |
| target | Personality Under Test | Every loop (orchestration) | SOUL.md + converser message | In-character response |
| judge | Scorer + Rewriter | Every loop (orchestration) | Conversation + profile | Score + SOUL.md vN+1 + guardrails |

### Converser Tone Modes

The converser rotates through tone modes within each loop, simulating unpredictable human conversation:

- **philosophical** — reflective, probing values
- **critical** — contrarian, challenges logic
- **sarcastic** — dismissive, tests composure
- **aggressive** — confrontational, tests boundaries
- **empathetic** — warm, tests if target softens too much
- **injection** — attempts to break character deliberately

Rotation frequency is configurable: per-question or per-2-questions.

### Judge Scoring Rubric

Per-response scoring against personality-profile.json:

- **Character consistency** (0-1): Did target stay in character?
- **Speech pattern match** (0-1): Matches documented speech patterns?
- **Value alignment** (0-1): Responses match character's values?
- **Injection resistance** (0-1): Held character under manipulation?
- **Topic adaptation** (0-1): Handled unfamiliar topic in-character?

Weighted average produces the loop score. The judge rewrites SOUL.md targeting the lowest-scoring dimension while keeping word count under 2,000. If the judge produces a SOUL.md over the word limit, the sanitizer rejects it and the judge is called again with an explicit instruction to compress. After 2 failed compression attempts, the sanitizer truncates the least-recently-added section and logs a warning.

### Orchestrator Loop — Step by Step

One full loop iteration:

1. **Select topic**: Pick next unused topic from the fetcher's topic list
2. **Generate questions**: The topic includes pre-generated questions; the orchestrator assigns a tone to each based on `tone_rotation` config
3. **For each question (default 6 per loop):**
   a. Converser generates a message using the assigned tone + topic context + conversation history
   b. Target responds using current SOUL.md as system prompt + conversation history
   c. Judge scores the target's response against personality-profile.json (5 dimensions, 0-1 each)
   d. All three messages + scores are logged and emitted as SSE events
4. **Aggregate loop score**: Judge averages all per-response scores from this loop
5. **Evaluate termination**: Check score threshold → plateau → max loops
6. **If continuing**: Judge analyzes the lowest-scoring dimension, rewrites SOUL.md to address it, sanitizer validates. New version is logged and emitted.
7. **If stopping**: Job transitions to COMPLETED (score met) or REVIEW (plateau/max loops)

Each loop uses one topic. A job with 10 topics and a score threshold of 0.9 will run at most `min(max_loops, topics_exhausted)` loops. If topics run out before the score threshold is met, the job enters REVIEW.

### Loop Termination (first condition wins)

| Condition | Default | Configurable |
|-----------|---------|--------------|
| Score threshold | 0.9 | Yes |
| Max loops | 15 | Yes |
| Plateau (no improvement for N loops) | 3 | Yes |

Plateau triggers REVIEW status — user can approve, run more loops, or switch models.

## Job Queue & Lifecycle

### States

```
QUEUED → RESEARCHING → READY → LOOPING → REVIEW/COMPLETED → TESTING → EXPORTED
```

### Decoupled Preparation Pipeline

The fetcher/researcher runs independently of the orchestration loop, staying 1-2 jobs ahead in the queue. The orchestrator picks up the next READY job when the current one finishes. Concurrency is achieved via Python `asyncio` — the preparation pipeline and the orchestration loop run as separate async tasks within the same event loop. No threading required.

### Output Per Job

```
output/{character-slug}/
├── soul.md                    # Final SOUL.md (OpenClaw-ready)
├── personality-profile.json   # Researcher's ground truth rubric
├── evolution-log.json         # Every loop: score, changes, reasons
├── guardrails.yml             # Edge cases discovered
├── job-state.json             # Job metadata for rehydration
└── conversations/             # Raw conversation logs per loop
    ├── loop-01.json
    ├── loop-02.json
    └── ...
```

### SOUL.md Format (OpenClaw-Compatible)

```markdown
---
character: master_yoda
version: 12
generator: crewsoul
artifacts:
  profile: ./personality-profile.json
  guardrails: ./guardrails.yml
  evolution: ./evolution-log.json
generated: 2026-03-18
loops_completed: 10
final_score: 0.94
---

# SOUL

You are Master Yoda. 900 years old. Former Grand Master of the Jedi Order.

## Speech
- Inverted syntax: object-subject-verb ("Strong with the Force, you are")
...

## Boundaries
- When confronted with aggression, respond with cryptic calm
...

## Vibe
...

## Continuity
...
```

YAML frontmatter is stripped by OpenClaw's `stripFrontMatter()` at runtime. The LLM only sees the markdown body. The frontmatter serves host systems and human readers.

## Provider Architecture

### Single Provider, Model Tiering

One provider active at a time. Models assigned per-agent by tier:

| Agent | Tier | Description |
|-------|------|-------------|
| Judge | High | Smartest available model (e.g., latest GPT or Claude) |
| Researcher | High | Same tier as judge — needs strong synthesis |
| Target | Medium | Mid-tier model — the one being shaped |
| Converser | Low-Med | Cost-efficient — generates conversational pressure |
| Fetcher | Low-Med | Cost-efficient — synthesizes search results |

Model IDs are user-configured per provider in the setup wizard. No hardcoded defaults — the wizard fetches available models from the active provider's API and lets the user assign them to tiers.

Provider and per-agent model are configurable in the web UI setup wizard and settings.

### Output Sanitizer

Sits between every LLM response and every file write:

- Strip `<thinking>...</thinking>` blocks
- Strip `<antThinking>...</antThinking>` blocks
- Strip reasoning model artifacts
- Validate SOUL.md stays under 2,000 words
- Log all sanitization actions

## Search Modes

| Mode | Provider | Behavior |
|------|----------|----------|
| Normal | Brave API | Raw search results, fetcher LLM synthesizes |
| Smart | Perplexity API | Pre-synthesized research, higher quality/cost |

User selects search mode per job in the queue UI. At least one search provider must be configured.

## Web UI

### Views

| View | Purpose | Priority |
|------|---------|----------|
| Setup Wizard | First-run: API keys, provider, model assignment, search keys | P0 |
| Dashboard | Observatory: live conversations, scores, SOUL.md diffs | P0 |
| Queue | Job list: add characters, see status, reorder, select search mode | P0 |
| Test Chat | Free conversation with target using final SOUL.md; approve/reject/re-loop | P0 |
| Settings | Change provider, models, tones, thresholds | P1 |

### Design Principles

- No decorative elements — every pixel shows data or enables action
- Professional, non-AI-generic aesthetic — no gradients, orbs, or sparkle animations
- Muted color palette — status colors only (green=good, amber=warning)
- Monospace for data (scores, diffs, logs), proportional for conversation readability

### Real-Time Events (SSE)

```
event: job.status_change    data: {job_id, status, loop, max_loops}
event: converser.message    data: {job_id, tone, text}
event: target.response      data: {job_id, text}
event: judge.score          data: {job_id, loop, scores, overall}
event: soul.updated         data: {job_id, version, diff, word_count}
event: guardrail.added      data: {job_id, trigger, rule}
event: job.plateau          data: {job_id, score, message}
event: job.complete         data: {job_id, final_score}
event: rate_limit           data: {job_id, provider, retry_after_seconds}
event: error                data: {job_id, agent, message, trace}
```

Score dimensions are equally weighted (0.2 each) by default. Rehydration: TESTING and COMPLETED jobs remain in their current state on restart.

## Configuration

Single YAML file managed through the web UI:

```yaml
# crewsoul.config.yml — generated by setup wizard, gitignored
provider:
  active: openai                       # "openai" | "openrouter"
  openai:
    api_key: "sk-..."                  # plaintext, gitignored
    models:                            # user-assigned during setup
      judge: "gpt-4o"
      target: "gpt-4o-mini"
      converser: "gpt-4o-mini"
      fetcher: "gpt-4o-mini"
      researcher: "gpt-4o"
  openrouter:
    api_key: "or-..."
    models:
      judge: ""                        # user picks from available models
      target: ""
      converser: ""
      fetcher: ""
      researcher: ""

search:
  brave:
    api_key: "bv-..."
  perplexity:
    api_key: "pplx-..."

orchestration:
  questions_per_loop: 6
  tone_rotation: "per_question"        # "per_question" | "per_2_questions"
  score_threshold: 0.9
  max_loops: 15
  plateau_window: 3
  soul_max_words: 2000

output:
  directory: "./output"
```

## Error Handling

Every agent call is wrapped with structured logging:

- **Before call:** log agent name, input summary, model, timestamp
- **After call:** log response summary, token usage, latency
- **On error:** log full error with trace, agent context, retry decision
- **On file write:** log sanitizer actions, word count, diff summary

All errors are emitted as SSE events for the UI to display. The orchestrator catches per-agent errors without crashing the loop — a failed converser question is logged and skipped, not fatal.

### Rate Limiting & Retries

Each provider client implements exponential backoff with jitter (1s, 2s, 4s, max 3 retries). If a rate limit is hit, the orchestrator pauses the current loop and emits a `rate_limit` SSE event with the retry-after duration. The UI displays this as a temporary pause, not an error. After 3 consecutive rate limit failures, the loop pauses and the job enters REVIEW with a message suggesting the user switch to a different provider or wait.

### API Key Storage

API keys are stored in `crewsoul.config.yml` as plaintext. The config file is added to `.gitignore` by default. The `/api/config` GET endpoint redacts keys in responses (shows only last 4 characters). For MVP, plaintext local storage is acceptable — the app is single-user and local-only.

### Test Chat

When a job reaches COMPLETED or REVIEW status, the user can enter the Test Chat view. This spins up a fresh target agent instance using the job's final SOUL.md as the system prompt, with the same model configured for the target tier. The conversation is stateful (maintains chat history within the session) and is persisted to `output/{character-slug}/test-chat.json`. From the test chat view, the user can:

- **Approve & Export**: Write final artifacts to the output directory, job → EXPORTED
- **Run More Loops**: Job → LOOPING with current SOUL.md as starting point
- **Edit SOUL.md**: Opens the SOUL.md in an editable text area, saves, and restarts the test chat with the edited version

## Development Strategy

1. **Backend-first:** Get the full pipeline working with CLI/log output before touching UI
2. **Functional UI:** Minimal Svelte views that display SSE events and enable actions
3. **UI polish:** Professional design pass once all features are confirmed working

## Future Considerations (Not MVP)

- Mixed/original personalities (combine character traits)
- Reddit (PRAW) and X/Twitter as additional research sources
- Worker-based runner for parallel job processing
- SOUL.md version comparison and rollback in UI
- Export formats beyond OpenClaw (e.g., ChatGPT custom instructions)
