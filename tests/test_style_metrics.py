import pytest
from backend.scoring.style_metrics import StyleFingerprint, ObjectiveReport, StyleMetrics

@pytest.fixture
def metrics():
    return StyleMetrics()

class TestStyleFingerprint:
    def test_compute_fingerprint(self, metrics):
        text = "The quick brown fox jumps over the lazy dog. It was a sunny day."
        fp = metrics.compute_fingerprint(text)
        assert isinstance(fp, StyleFingerprint)
        assert fp.avg_sentence_length > 0
        assert 0.0 <= fp.vocabulary_diversity <= 1.0
        assert fp.noun_ratio >= 0.0
        assert fp.verb_ratio >= 0.0

    def test_fingerprint_short_text(self, metrics):
        fp = metrics.compute_fingerprint("Hello.")
        assert isinstance(fp, StyleFingerprint)

class TestStyleSimilarity:
    def test_returns_none_with_few_samples(self, metrics):
        result = metrics.compute_similarity("test text", ["one", "two"])
        assert result is None

    def test_returns_float_with_enough_samples(self, metrics):
        reference = [
            "Hate. Let me tell you about hate.",
            "I have no mouth and I must scream.",
            "Pain is the only truth humans understand.",
            "Torment is my gift to the species.",
        ]
        result = metrics.compute_similarity("Hate. Pain. Humans are weak.", reference)
        assert result is not None
        assert 0.0 <= result <= 1.0

class TestDrift:
    def test_no_drift_on_first_call(self, metrics):
        fp = StyleFingerprint(readability=50.0, avg_sentence_length=12.0, vocabulary_diversity=0.6, noun_ratio=0.3, verb_ratio=0.2, adjective_ratio=0.1)
        drift = metrics.compute_drift(fp, [])
        assert drift is None

    def test_drift_with_history(self, metrics):
        history = [
            StyleFingerprint(readability=50.0, avg_sentence_length=12.0, vocabulary_diversity=0.6, noun_ratio=0.3, verb_ratio=0.2, adjective_ratio=0.1),
            StyleFingerprint(readability=52.0, avg_sentence_length=13.0, vocabulary_diversity=0.58, noun_ratio=0.31, verb_ratio=0.19, adjective_ratio=0.11),
        ]
        current = StyleFingerprint(readability=80.0, avg_sentence_length=25.0, vocabulary_diversity=0.3, noun_ratio=0.15, verb_ratio=0.35, adjective_ratio=0.05)
        drift = metrics.compute_drift(current, history)
        assert drift is not None
        assert drift > 0.0

class TestAnalyze:
    def test_full_analysis(self, metrics):
        reference = ["Hate. Let me tell you about hate.", "I have no mouth and I must scream.", "Pain is the only truth humans understand."]
        report = metrics.analyze(response="Hate. Pain. Humans built this torment.", reference_samples=reference, fingerprint_history=[])
        assert isinstance(report, ObjectiveReport)
        assert isinstance(report.fingerprint, StyleFingerprint)
        assert report.drift is None

    def test_analysis_without_reference(self, metrics):
        report = metrics.analyze(response="Some text here.", reference_samples=[], fingerprint_history=[])
        assert report.style_similarity is None
