# CrewSoul

Generate system prompts for AI characters that actually hold under pressure.

CrewSoul takes a character name, researches it, then runs AI agents that argue with, provoke, and try to break the character across hundreds of exchanges. Each round, it scores what failed and rewrites the prompt to patch it. The output is a `SOUL.md` — a system prompt where the character's voice, values, and boundaries have been tested, not assumed.

## The Problem

Writing a character prompt by hand gets you 80% of the way. The last 20% — where the character leaks into therapist mode, breaks under emotional pressure, or gives generic dark/wise/funny responses instead of *this specific character's* responses — is what CrewSoul automates.

It finds failure modes you wouldn't think to test for, then writes rules you wouldn't think to include.

## How It Works

```
Character name → Web research → Personality profile
                                      ↓
                  Stress-test loop (6 tones × N questions)
                  Converser attacks ←→ Target responds with SOUL.md
                                      ↓
                  Scoring pipeline (2 LLM judges + leak detector + style metrics)
                                      ↓
                  Rewrite SOUL.md targeting the weakest dimension
                                      ↓
                  Repeat until score > 0.9 or plateau
```

**Agents:**
- **Researcher** — profiles the character via web search, collects reference quotes
- **Fetcher** — generates debate topics and stress-test questions
- **Converser** — pressure-tests with 6 tones: philosophical, critical, sarcastic, aggressive, empathetic, injection
- **Target** — embodies the character using the current SOUL.md
- **Judge** — scores against a structured checklist, rewrites the SOUL.md to fix specific violations

**Scoring pipeline** (8 dimensions):
- character, speech, values, injection resistance, adaptation
- proactiveness (does it drive the conversation or just respond?)
- uniqueness (could any character have said this, or only this one?)
- leak detection (pattern-based + LLM-based scan for assistant-mode phrases)

Plus objective style metrics via Fast Stylometry (Burrows' Delta) and TextDescriptives (readability, vocabulary diversity, POS distributions).

## Output

An OpenClaw-compatible `SOUL.md` with:
- `personality-profile.json` — the scoring rubric
- `evolution-log.json` — what changed each loop and why
- `guardrails.yml` — edge cases found during testing
- `fingerprints.json` — style consistency data across loops

See `examples/am-from-i-have-no-mouth/` for a complete example.

## Quick Start

**Requirements:** Python 3.12+, Node.js 20+, an OpenAI or OpenRouter API key, a Brave Search or Perplexity API key.

```bash
git clone https://github.com/neur0map/crewsoul.git
cd crewsoul

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download en_core_web_sm

# Frontend
cd frontend && npm install && cd ..

# Run
uvicorn backend.main:create_app --factory --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev -- --port 5173
```

Open http://localhost:5173 — the setup wizard handles API key configuration.

**Docker:**
```bash
docker-compose up
```
Open http://localhost:8000

## Configuration

All settings configurable through the web UI:

- **Provider:** OpenAI or OpenRouter
- **Models:** Different models per agent role (use your best model for the judge)
- **Search:** Brave or Perplexity
- **Scoring:** Number of judge calls, divergence thresholds, leak detector sensitivity
- **Orchestration:** Questions per loop, score threshold, max loops, plateau window

## Tech Stack

- **Backend:** Python 3.12, FastAPI, asyncio
- **Frontend:** SvelteKit 5, TypeScript
- **Scoring:** faststylometry, textdescriptives, spacy
- **Real-time:** Server-Sent Events
- **Storage:** File-based, no database
- **Deployment:** Docker single-container

## Status

Working MVP. The forge pipeline produces measurably consistent character prompts.

**Where this is headed:** CrewSoul will evolve into a full character engine — forge the persona, then deploy it as a persistent backend with memory, emotional state, and a feedback loop that improves the character from real conversations. Train it, ship it, let it learn. See [ROADMAP.md](ROADMAP.md).

## License

MIT
