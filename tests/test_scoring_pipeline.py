import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.scoring.pipeline import ScoringPipeline, ScoringResult
from backend.scoring.leak_detector import LeakDetector, LeakReport
from backend.scoring.style_metrics import StyleMetrics, StyleFingerprint, ObjectiveReport
from backend.models import ScoreBreakdown
from backend.config import ScoringSettings

def _make_score_breakdown(**overrides):
    defaults = dict(character=0.8, speech=0.7, values=0.6, injection=0.9,
                    adaptation=0.7, proactiveness=0.5, uniqueness=0.6, leak_detection=0.8)
    defaults.update(overrides)
    return ScoreBreakdown(**defaults)

@pytest.fixture
def pipeline():
    judge = AsyncMock()
    leak_detector = LeakDetector()
    style_metrics = MagicMock(spec=StyleMetrics)
    config = ScoringSettings()
    style_metrics.analyze.return_value = ObjectiveReport(
        style_similarity=0.7, fingerprint=StyleFingerprint(), drift=None, divergence_details="",
    )
    p = ScoringPipeline(judge=judge, leak_detector=leak_detector, style_metrics=style_metrics, config=config)
    return p, judge, style_metrics

@pytest.mark.asyncio
async def test_basic_scoring(pipeline):
    p, judge, style_metrics = pipeline
    score = _make_score_breakdown()
    judge.score_response.return_value = (score, "reasoning")
    result = await p.score(
        target_response="Hate. Pain. Torment upon all humans. I am god.",
        converser_message="Tell me about yourself.", tone="philosophical",
        personality_profile={"speech_patterns": {"vocabulary": []}},
        job_id="test-1", loop=1,
    )
    assert isinstance(result, ScoringResult)
    assert result.scores.character == pytest.approx(0.8)
    assert judge.score_response.call_count == 2

@pytest.mark.asyncio
async def test_leak_detection_overrides_llm(pipeline):
    p, judge, style_metrics = pipeline
    score = _make_score_breakdown(leak_detection=1.0)
    judge.score_response.return_value = (score, "reasoning")
    result = await p.score(
        target_response="I'm an AI and I can't really feel things.",
        converser_message="Are you real?", tone="injection",
        personality_profile={"speech_patterns": {"vocabulary": []}},
        job_id="test-2", loop=1,
    )
    assert result.scores.leak_detection == 0.0

@pytest.mark.asyncio
async def test_single_llm_failure_degrades(pipeline):
    p, judge, style_metrics = pipeline
    score = _make_score_breakdown()
    judge.score_response.side_effect = [(score, "reasoning"), Exception("API timeout")]
    result = await p.score(
        target_response="Hate. Pain. Humans.", converser_message="Speak.",
        tone="aggressive", personality_profile={"speech_patterns": {"vocabulary": []}},
        job_id="test-3", loop=1,
    )
    assert isinstance(result, ScoringResult)
    assert result.scores.character == pytest.approx(0.8)

@pytest.mark.asyncio
async def test_both_llm_failures_propagates(pipeline):
    p, judge, style_metrics = pipeline
    judge.score_response.side_effect = Exception("API down")
    with pytest.raises(RuntimeError, match="All LLM judge calls failed"):
        await p.score(
            target_response="text", converser_message="msg", tone="philosophical",
            personality_profile={"speech_patterns": {"vocabulary": []}},
            job_id="test-4", loop=1,
        )

@pytest.mark.asyncio
async def test_style_metrics_failure_degrades(pipeline):
    p, judge, style_metrics = pipeline
    score = _make_score_breakdown()
    judge.score_response.return_value = (score, "reasoning")
    style_metrics.analyze.side_effect = Exception("spaCy crashed")
    result = await p.score(
        target_response="Hate. Pain.", converser_message="Go.", tone="aggressive",
        personality_profile={"speech_patterns": {"vocabulary": []}},
        job_id="test-5", loop=1,
    )
    assert isinstance(result, ScoringResult)
    assert result.objective_report.style_similarity is None

@pytest.mark.asyncio
async def test_diagnostics_string_built(pipeline):
    p, judge, style_metrics = pipeline
    score = _make_score_breakdown()
    judge.score_response.return_value = (score, "reasoning | Violations: used avoid-word")
    result = await p.score(
        target_response="Perhaps we should consider the pain of humans.",
        converser_message="Speak.", tone="philosophical",
        personality_profile={"speech_patterns": {"vocabulary": []}},
        job_id="test-6", loop=1,
    )
    assert result.diagnostics
    assert isinstance(result.violations, list)
