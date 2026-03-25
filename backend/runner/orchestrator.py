from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from backend.agents.converser import ConverserAgent, TONE_PROMPTS
from backend.agents.judge import JudgeAgent
from backend.agents.target import TargetAgent
from backend.config import ScoringSettings
from backend.models import Event, EventType, Job, JobStatus, ScoreBreakdown
from backend.output.writer import OutputWriter
from backend.providers.base import ProviderBase
from backend.runner.events import EventEmitter
from backend.runner.queue import JobQueue
from backend.sanitizer import validate_soul_word_count
from backend.scoring.leak_detector import LeakDetector
from backend.scoring.pipeline import ScoringPipeline
from backend.scoring.style_metrics import StyleMetrics

logger = logging.getLogger(__name__)
TONES = list(TONE_PROMPTS.keys())


class Orchestrator:
    def __init__(self, provider: ProviderBase, emitter: EventEmitter, queue: JobQueue, writer: OutputWriter, converser_model: str, target_model: str, judge_model: str, config: Any, scoring_config=None) -> None:
        self.converser = ConverserAgent(provider=provider, model=converser_model, emitter=emitter)
        self.target = TargetAgent(provider=provider, model=target_model, emitter=emitter)
        self.judge = JudgeAgent(provider=provider, model=judge_model, emitter=emitter)
        sc = scoring_config if isinstance(scoring_config, ScoringSettings) else ScoringSettings()
        self.pipeline = ScoringPipeline(
            judge=self.judge, leak_detector=LeakDetector(),
            style_metrics=StyleMetrics(), config=sc,
        )
        self.emitter = emitter
        self.queue = queue
        self.writer = writer
        self.config = config

    async def run_loop(self, job: Job) -> bool:
        job.status = JobStatus.LOOPING
        job.current_loop += 1
        job.updated_at = datetime.now(timezone.utc).isoformat()
        self.queue.persist(job)
        await self.emitter.emit(Event(type=EventType.JOB_STATUS_CHANGE, job_id=job.id, data={"status": "LOOPING", "loop": job.current_loop, "max_loops": job.max_loops}))
        self.pipeline.load_fingerprints(job.id, self.writer, job)

        topic = self._select_topic(job)
        if topic is None:
            # Recycle topics from the beginning
            job.topic_index = 0
            topic = self._select_topic(job)
            if topic is None:
                # No topics at all
                logger.warning("No topics available for job %s", job.id)
                job.status = JobStatus.REVIEW
                job.updated_at = datetime.now(timezone.utc).isoformat()
                self.queue.persist(job)
                await self.emitter.emit(Event(type=EventType.JOB_PLATEAU, job_id=job.id, data={"score": job.scores[-1] if job.scores else 0, "message": "No topics available"}))
                return True
            logger.info("Recycling topics for job %s (starting over)", job.id)

        questions = topic.get("questions", [])[:self.config.questions_per_loop]
        conversation_history = []
        loop_scores: list[ScoreBreakdown] = []
        loop_reasonings: list[str] = []
        loop_conversation = []

        for i, q in enumerate(questions):
            tone = self._assign_tone(q, i)
            try:
                converser_msg = await self.converser.converse(tone=tone, topic=topic["name"], question=q["text"], conversation_history=conversation_history, job_id=job.id)
                await self.emitter.emit(Event(type=EventType.CONVERSER_MESSAGE, job_id=job.id, data={"tone": tone, "text": converser_msg}))
                conversation_history.append({"role": "user", "content": converser_msg})
                loop_conversation.append({"role": "converser", "tone": tone, "text": converser_msg})

                target_msg = await self.target.respond(soul_md=job.current_soul_content, conversation_history=conversation_history, job_id=job.id)
                await self.emitter.emit(Event(type=EventType.TARGET_RESPONSE, job_id=job.id, data={"text": target_msg}))
                conversation_history.append({"role": "assistant", "content": target_msg})
                loop_conversation.append({"role": "target", "text": target_msg})

                result = await self.pipeline.score(
                    target_response=target_msg,
                    converser_message=converser_msg,
                    tone=tone,
                    personality_profile=job.personality_profile,
                    job_id=job.id,
                    loop=job.current_loop,
                )
                loop_scores.append(result.scores)
                loop_reasonings.append(result.diagnostics)
                await self.emitter.emit(Event(type=EventType.JUDGE_SCORE, job_id=job.id, data={"loop": job.current_loop, "question": i + 1, "scores": result.scores.to_dict(), "overall": result.scores.average(), "reasoning": result.diagnostics}))
                if result.objective_report.style_similarity is not None:
                    self.writer.append_calibration(job, {
                        "loop": job.current_loop,
                        "llm_speech": result.scores.speech,
                        "stylometric": result.objective_report.style_similarity,
                        "divergence": abs(result.scores.speech - result.objective_report.style_similarity),
                    })
            except Exception as e:
                logger.error("[orchestrator] Question %d failed: %s", i + 1, e)
                await self.emitter.emit(Event(type=EventType.ERROR, job_id=job.id, data={"agent": "orchestrator", "message": f"Question {i+1} failed: {e}"}))
                continue

        if not loop_scores:
            return False

        avg_score = ScoreBreakdown.average_of(loop_scores)
        weights = job.personality_profile.get("score_weights") if job.personality_profile else None
        overall = avg_score.average(weights)
        job.scores.append(overall)
        job.score_breakdowns.append(avg_score.to_dict())
        self.writer.write_conversation(job, loop=job.current_loop, conversation=loop_conversation)

        # Minimum 3 loops required — early loops always refine regardless of score
        min_loops = 3
        passed_threshold = overall >= self.config.score_threshold
        past_minimum = job.current_loop >= min_loops

        # Always rewrite SOUL.md based on weakest dimension
        weakest_scores = avg_score.to_dict()
        weakest = min(weakest_scores, key=weakest_scores.get)
        # Collect violations and diagnostics from scoring results
        all_violations = " | ".join(r for r in loop_reasonings if r)
        all_diagnostics = " | ".join(r for r in loop_reasonings if r)
        # Truncate conversation to last 4 exchanges to keep rewrite prompt manageable
        truncated_convo = loop_conversation[-8:] if len(loop_conversation) > 8 else loop_conversation
        new_soul = await self.judge.rewrite_soul(
            current_soul=job.current_soul_content,
            weakest_dimension=weakest,
            conversation_log=truncated_convo,
            personality_profile=job.personality_profile,
            job_id=job.id,
            max_words=self.config.soul_max_words,
            violations=all_violations,
            diagnostics=all_diagnostics,
        )
        if not validate_soul_word_count(new_soul, self.config.soul_max_words):
            logger.warning("SOUL.md over word limit, requesting compression")
            new_soul = await self.judge.rewrite_soul(
                current_soul=new_soul, weakest_dimension="compression",
                conversation_log=[], personality_profile=job.personality_profile,
                job_id=job.id, max_words=self.config.soul_max_words,
            )

        job.current_soul_content = new_soul
        job.current_soul_version += 1
        self.writer.write_soul(job, new_soul)
        diff_summary = f"Rewrote for {weakest} (score: {weakest_scores[weakest]:.2f})"
        self.writer.append_evolution_log(
            job, loop=job.current_loop, score=overall,
            changes=diff_summary, dimension=weakest,
        )
        await self.emitter.emit(Event(
            type=EventType.SOUL_UPDATED, job_id=job.id,
            data={"version": job.current_soul_version, "diff": diff_summary, "word_count": len(new_soul.split())},
        ))
        self.pipeline.save_fingerprints(job.id, self.writer, job)

        # Check termination only after minimum loops
        if past_minimum and passed_threshold:
            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self.queue.persist(job)
            await self.emitter.emit(Event(type=EventType.JOB_COMPLETE, job_id=job.id, data={"final_score": overall}))
            return True

        if past_minimum and self._check_plateau(job):
            job.status = JobStatus.REVIEW
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self.queue.persist(job)
            await self.emitter.emit(Event(type=EventType.JOB_PLATEAU, job_id=job.id, data={"score": overall, "message": f"Score plateaued at {overall:.2f} for {self.config.plateau_window} loops"}))
            return True

        if job.current_loop >= job.max_loops:
            job.status = JobStatus.REVIEW
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self.queue.persist(job)
            await self.emitter.emit(Event(type=EventType.JOB_PLATEAU, job_id=job.id, data={"score": overall, "message": f"Max loops ({job.max_loops}) reached"}))
            return True

        job.updated_at = datetime.now(timezone.utc).isoformat()
        self.queue.persist(job)
        return False

    def _finalize_job(self, job: Job) -> None:
        """Write final output files when job completes or goes to review."""
        # Write final SOUL.md with updated frontmatter
        self.writer.write_soul(job, job.current_soul_content)

        # Generate guardrails from evolution log
        import json
        from pathlib import Path
        log_path = self.writer.output_dir / job.character_slug / "evolution-log.json"
        guardrails = []
        if log_path.exists():
            entries = json.loads(log_path.read_text())
            for entry in entries:
                guardrails.append({
                    "trigger": f"Loop {entry['loop']} — {entry['dimension']} weakness",
                    "failure": entry["changes"],
                    "rule": f"SOUL.md was rewritten to address {entry['dimension']} (score: {entry['score']:.2f})",
                    "added_to_soul": True,
                })
        if guardrails:
            self.writer.write_guardrails(job, guardrails)

        logger.info("Finalized output for %s: soul.md + guardrails.yml", job.character)

    async def run_job(self, job: Job) -> None:
        logger.info("Starting orchestration for %s", job.character)
        while True:
            done = await self.run_loop(job)
            if done:
                self._finalize_job(job)
                logger.info("Job %s finished: status=%s score=%s", job.id, job.status.value, job.scores[-1] if job.scores else "N/A")
                break

    async def run_continuous(self) -> None:
        while True:
            job = self.queue.next_ready()
            if job:
                await self.run_job(job)
            else:
                await asyncio.sleep(2.0)

    def _select_topic(self, job: Job) -> dict | None:
        if not job.topics or job.topic_index >= len(job.topics):
            return None
        topic = job.topics[job.topic_index]
        job.topic_index += 1
        return topic

    def _assign_tone(self, question: dict, index: int) -> str:
        if self.config.tone_rotation == "per_question":
            return question.get("suggested_tone", TONES[index % len(TONES)])
        else:
            return question.get("suggested_tone", TONES[(index // 2) % len(TONES)])

    def _check_plateau(self, job: Job) -> bool:
        window = self.config.plateau_window
        if len(job.scores) < window:
            return False
        recent = job.scores[-window:]
        return max(recent) - min(recent) < 0.02
