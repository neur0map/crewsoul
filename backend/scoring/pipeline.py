from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
from backend.agents.judge import JudgeAgent
from backend.config import ScoringSettings
from backend.models import ScoreBreakdown
from backend.scoring.leak_detector import LeakDetector, LeakReport
from backend.scoring.style_metrics import StyleMetrics, StyleFingerprint, ObjectiveReport

logger = logging.getLogger(__name__)

@dataclass
class ScoringResult:
    scores: ScoreBreakdown
    llm_scores: list[ScoreBreakdown] = field(default_factory=list)
    leak_report: LeakReport = field(default_factory=lambda: LeakReport(score=1.0))
    objective_report: ObjectiveReport = field(default_factory=lambda: ObjectiveReport(
        style_similarity=None, fingerprint=StyleFingerprint(), drift=None, divergence_details="",
    ))
    diagnostics: str = ""
    violations: list[str] = field(default_factory=list)

class ScoringPipeline:
    def __init__(self, judge: JudgeAgent, leak_detector: LeakDetector, style_metrics: StyleMetrics, config: ScoringSettings):
        self.judge = judge
        self.leak_detector = leak_detector
        self.style_metrics = style_metrics
        self.config = config
        self.fingerprint_history: dict[str, list[StyleFingerprint]] = {}

    async def score(self, target_response: str, converser_message: str, tone: str, personality_profile: dict, job_id: str, loop: int) -> ScoringResult:
        # 1. Fire LLM calls concurrently
        llm_tasks = [
            self._judge_call(target_response, converser_message, tone, personality_profile, job_id, temp=0.3),
            self._judge_call(target_response, converser_message, tone, personality_profile, job_id, temp=0.5),
        ]
        llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)

        # 2. Collect successful results
        successful_scores = []
        all_violations = []
        all_reasonings = []
        for r in llm_results:
            if isinstance(r, Exception):
                logger.warning("[pipeline] LLM judge call failed: %s", r)
                continue
            score, reasoning = r
            successful_scores.append(score)
            all_reasonings.append(reasoning)
            if "Violations:" in reasoning:
                parts = reasoning.split("Violations:", 1)[1].strip()
                all_violations.extend(v.strip() for v in parts.split(",") if v.strip())

        if not successful_scores:
            raise RuntimeError("All LLM judge calls failed")

        # 3. Average LLM scores
        avg_scores = ScoreBreakdown.average_of(successful_scores)

        if len(successful_scores) == 2:
            s1, s2 = successful_scores
            for fname in avg_scores.to_dict():
                if abs(getattr(s1, fname) - getattr(s2, fname)) > 0.4:
                    logger.warning("[pipeline] Scoring instability on %s: %.2f vs %.2f", fname, getattr(s1, fname), getattr(s2, fname))

        # 4. Leak detection
        allowed_vocab = personality_profile.get("speech_patterns", {}).get("vocabulary", [])
        try:
            leak_report = self.leak_detector.detect(target_response, allowed_vocabulary=allowed_vocab)
        except Exception as e:
            logger.error("[pipeline] Leak detection failed: %s", e)
            leak_report = LeakReport(score=1.0, explanation="Leak detection unavailable")

        avg_scores.leak_detection = min(avg_scores.leak_detection, leak_report.score)

        # 5. Objective metrics
        reference_samples = personality_profile.get("reference_samples", [])
        job_history = self.fingerprint_history.get(job_id, [])
        try:
            objective_report = self.style_metrics.analyze(response=target_response, reference_samples=reference_samples, fingerprint_history=job_history)
            if job_id not in self.fingerprint_history:
                self.fingerprint_history[job_id] = []
            self.fingerprint_history[job_id].append(objective_report.fingerprint)
        except Exception as e:
            logger.warning("[pipeline] Style metrics failed: %s", e)
            objective_report = ObjectiveReport(style_similarity=None, fingerprint=StyleFingerprint(), drift=None, divergence_details="")

        # 6. Build diagnostics
        diagnostics_parts = []
        if objective_report.style_similarity is not None:
            speech_llm = avg_scores.speech
            divergence = abs(speech_llm - objective_report.style_similarity)
            if divergence > self.config.divergence_threshold:
                diagnostics_parts.append(f"Style divergence: LLM speech={speech_llm:.2f} vs stylometric={objective_report.style_similarity:.2f}")
        if objective_report.divergence_details:
            diagnostics_parts.append(f"Style metrics: {objective_report.divergence_details}")
        if leak_report.hard_matches or leak_report.soft_matches:
            diagnostics_parts.append(f"Leak detection: {leak_report.explanation}")
        for r in all_reasonings:
            if r:
                diagnostics_parts.append(r)

        return ScoringResult(
            scores=avg_scores, llm_scores=successful_scores, leak_report=leak_report,
            objective_report=objective_report, diagnostics=" | ".join(diagnostics_parts), violations=all_violations,
        )

    def save_fingerprints(self, job_id: str, writer, job) -> None:
        from dataclasses import asdict
        history = self.fingerprint_history.get(job_id, [])
        writer.write_fingerprints(job, [asdict(fp) for fp in history])

    def load_fingerprints(self, job_id: str, writer, job) -> None:
        data = writer.read_fingerprints(job)
        if data:
            from backend.scoring.style_metrics import StyleFingerprint
            self.fingerprint_history[job_id] = [StyleFingerprint(**d) for d in data]

    async def _judge_call(self, target_response, converser_message, tone, personality_profile, job_id, temp):
        return await self.judge.score_response(
            target_response=target_response, converser_message=converser_message,
            tone=tone, personality_profile=personality_profile, job_id=job_id, temperature=temp,
        )
