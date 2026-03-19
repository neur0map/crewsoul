# Roadmap

## Current State (MVP)

The core forge pipeline works: research, stress-test, score, rewrite, repeat. Characters go from generic LLM behavior to measurably consistent personality embodiment. Output is OpenClaw-compatible.

### Known Limitations

- **Multi-turn injection breaks:** Characters hold on single responses but can break on sustained emotional pressure in multi-turn conversations (model safety training ceiling)
- **Serial job processing:** One job at a time — queued jobs wait
- **No external validation:** The judge grades against its own checklist — no human-in-the-loop scoring during the loop
- **Topic recycling:** Only 5 topics generated per job — recycled after exhaustion
- **Guardrails are thin:** Log rewrite events but don't capture specific failure scenarios with enough detail
- **Frontend is functional, not polished:** Setup wizard, queue, dashboard, chat work but need design pass

---

## Phase 1: Scoring Reliability

**Goal:** Make the judge trustworthy enough that the scores mean something.

- [ ] **Multiple judge calls per response** — Average 3 independent scores to reduce variance
- [ ] **Curated test bank** — A fixed set of known-hard scenarios (empathy trap, injection, boredom, topic switch) that run every loop instead of random converser questions
- [ ] **Human scoring integration** — Let the user flag bad responses during the loop, injected as ground truth alongside the judge's scores
- [ ] **A/B comparison view** — Show v0 and vN responses side-by-side in the UI so users can see actual improvement
- [ ] **Score calibration** — Track judge score vs human score over time to detect and correct bias

## Phase 2: Character Depth

**Goal:** Characters that feel genuinely alive, not just consistent.

- [ ] **Agency rules in researcher output** — The personality profile should specify how the character acts unprompted, not just how they respond
- [ ] **Mood state machine** — Characters should have moods that shift across a conversation based on what's said
- [ ] **Memory within sessions** — Characters should reference earlier parts of the conversation, hold grudges, notice patterns
- [ ] **Refusal vocabulary** — The researcher should generate character-specific ways to refuse, deflect, or redirect instead of generic responses
- [ ] **Multi-turn stress testing** — Converser should test 3-4 message sequences, not just single exchanges

## Phase 3: Pipeline Efficiency

**Goal:** Faster, cheaper, and smarter forging.

- [ ] **Parallel job processing** — Run multiple jobs concurrently with a semaphore
- [ ] **Model-specific roleplay frames** — Different models have different safety boundaries — the target wrapper should adapt
- [ ] **Smart topic generation** — Generate topics that specifically target the character's weak points, not random news
- [ ] **Incremental rewrites** — Instead of rewriting the entire SOUL.md each loop, patch only the section that failed
- [ ] **Cost tracking** — Track API spend per job, per loop, per agent — display in the UI
- [ ] **Caching** — Cache personality profiles and topic lists so re-runs are faster

## Phase 4: UI/UX Polish

**Goal:** Professional tool, not a developer prototype.

- [ ] **Dashboard observatory** — Live conversation view with score chart, SOUL.md diff viewer, event timeline
- [ ] **SOUL.md editor** — Edit the SOUL.md in the browser, re-run the test chat to validate
- [ ] **Version comparison** — Compare any two SOUL.md versions side-by-side with diff highlighting
- [ ] **Export formats** — Export as OpenClaw workspace, ChatGPT custom instructions, Claude system prompt
- [ ] **Dark mode** — Professional dark theme
- [ ] **Mobile responsive** — Queue and chat views usable on mobile

## Phase 5: Advanced Features

**Goal:** Capabilities that go beyond the basic forge.

- [ ] **Mixed personalities** — Combine traits from multiple characters ("Naval Ravikant's wisdom with Yoda's speech")
- [ ] **Original personalities** — Generate personalities from a description, not just existing characters
- [ ] **Reddit/X research sources** — PRAW for Reddit, X API for Twitter — richer source material
- [ ] **Personality regression testing** — After editing a SOUL.md, run the full test suite to check nothing broke
- [ ] **Community library** — Share and download forged personalities
- [ ] **Webhook notifications** — Notify when a job completes via Discord, Slack, or email
