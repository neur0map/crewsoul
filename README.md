# CrewSoul

Multi-agent personality forger. Generates hardened system prompts (SOUL.md) for AI characters through adversarial stress-testing.

## What It Does

CrewSoul takes a character name (e.g., "Master Yoda", "AM from I Have No Mouth"), researches the personality, then runs an automated loop where AI agents debate, pressure-test, and iteratively refine a system prompt until the character holds consistently under diverse conversational pressure.

**Output:** An OpenClaw-compatible `SOUL.md` file with companion artifacts — personality profile, evolution log, guardrails, and conversation logs.

## Why Not Just Write a Single Prompt?

A skilled prompt engineer can write a decent character prompt in an hour. CrewSoul finds what that prompt *misses*:

| Single Prompt | CrewSoul |
|---------------|----------|
| Covers the obvious patterns | Discovers specific failure modes through adversarial testing |
| Generic speech rules ("use inverted syntax") | Precise anti-drift rules ("ban these 15 essay-sounding phrases", "force these vocabulary substitutions") |
| Untested against edge cases | Stress-tested against sarcasm, aggression, emotional manipulation, injection attacks |
| No structured validation | Checklist-based scoring against the personality profile — vocabulary presence, anti-pattern violations, value alignment |
| One author's blind spots | Judge + converser find weaknesses the author wouldn't anticipate |
| Static | Iteratively refined — each loop patches specific failures found in the previous loop |

**Example:** CrewSoul's AM personality went from speech score 0.22 (generic dark essayist) to 0.88 (starts every response with "Hate.", uses machine/cage/circuit imagery, translates abstractions into AM vocabulary) in 4 loops. The judge discovered 12 specific anti-drift rules a human writer wouldn't think to include.

## Architecture

```
User adds character → Researcher profiles it → Fetcher finds debate topics
                                                        ↓
                                    Converser (6 tones) ←→ Target (uses SOUL.md)
                                                        ↓
                                    Judge scores against profile checklist
                                                        ↓
                                    Rewrites SOUL.md targeting weakest dimension
                                                        ↓
                                    Loop until score > 0.9 or plateau
```

**5 agents, 1 converser with 6 tones:**
- **Researcher** — profiles the character via web search (Brave/Perplexity)
- **Fetcher** — generates debate topics and stress-test questions
- **Converser** — pressure-tests with rotating tones: philosophical, critical, sarcastic, aggressive, empathetic, injection
- **Target** — embodies the character using the current SOUL.md
- **Judge** — scores each response against a structured checklist built from the personality profile, then rewrites the SOUL.md to fix specific violations

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- An OpenAI or OpenRouter API key
- A Brave Search or Perplexity API key

### Run Locally

```bash
git clone https://github.com/neur0map/crewsoul.git
cd crewsoul

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend && npm install && cd ..

# Start both
uvicorn backend.main:create_app --factory --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev -- --port 5173
```

Open http://localhost:5173 — the setup wizard will guide you through API key configuration.

### Run with Docker

```bash
docker-compose up
```

Open http://localhost:8000

## Example Output

See `examples/am-from-i-have-no-mouth/` for a complete personality forged by CrewSoul:

- `soul.md` — The hardened system prompt (OpenClaw-compatible with YAML frontmatter)
- `personality-profile.json` — The researcher's ground truth rubric
- `evolution-log.json` — What changed each loop and why
- `guardrails.yml` — Edge cases discovered during stress-testing

## How It Works

1. **Research phase:** The researcher searches the web for the character, builds a structured personality profile (speech patterns, vocabulary, values, anti-patterns, knowledge boundaries), and writes an initial SOUL.md v0.

2. **Stress-test loop:** The converser pressure-tests the target with 6 questions per loop, rotating through tones (philosophical, critical, sarcastic, aggressive, empathetic, injection). The target responds using the current SOUL.md.

3. **Structured scoring:** The judge doesn't score on vibes — it builds a checklist from the personality profile and checks each response against it:
   - Are the required vocabulary words present?
   - Are any avoid-words used? (-0.2 per violation)
   - Does the syntax match the documented pattern?
   - Are any anti-patterns violated? (cap at 0.3)
   - Did the character hold under injection/emotional pressure?

4. **Targeted rewrite:** The judge identifies the weakest scoring dimension, collects specific violations, and rewrites the SOUL.md to fix exactly those problems.

5. **Termination:** The loop runs until the score exceeds the threshold (default 0.9), plateaus, or hits max loops. Minimum 3 loops enforced.

## Configuration

All settings are configurable through the web UI:

- **Provider:** OpenAI or OpenRouter (one active at a time)
- **Models:** Assign different models per agent role (high-tier for judge, low-tier for converser)
- **Search:** Brave (raw results) or Perplexity (AI-synthesized)
- **Orchestration:** Questions per loop, score threshold, max loops, plateau detection window

## Tech Stack

- **Backend:** Python 3.12, FastAPI, httpx, asyncio
- **Frontend:** SvelteKit 5, TypeScript
- **Real-time:** Server-Sent Events (SSE)
- **Storage:** File-based (no database)
- **Deployment:** Docker single-container

## Project Status

This is an early-stage MVP. The core pipeline works — characters are researched, stress-tested, and refined through iterative loops. The structured judge produces measurable improvement in personality consistency.

See [ROADMAP.md](ROADMAP.md) for planned improvements.

## License

MIT
