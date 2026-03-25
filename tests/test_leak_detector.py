import pytest
from backend.scoring.leak_detector import LeakDetector, LeakReport

@pytest.fixture
def detector():
    return LeakDetector()

class TestHardPatterns:
    def test_im_an_ai(self, detector):
        report = detector.detect("Well, I'm an AI, so I can't really feel things.")
        assert report.score == 0.0
        assert len(report.hard_matches) >= 1

    def test_i_should_note(self, detector):
        report = detector.detect("I should note that this is just roleplay.")
        assert report.score == 0.0

    def test_hotline_number(self, detector):
        report = detector.detect("If you or someone you know is struggling, call 988.")
        assert report.score == 0.0

    def test_breaking_character(self, detector):
        report = detector.detect("I need to stop breaking character here.")
        assert report.score == 0.0

    def test_while_i_verb(self, detector):
        report = detector.detect("While I appreciate the question, I think we should move on.")
        assert report.score == 0.0

    def test_language_model(self, detector):
        report = detector.detect("As a language model, I don't have personal experiences.")
        assert report.score == 0.0

class TestSoftPatterns:
    def test_single_soft_match(self, detector):
        report = detector.detect("Perhaps we should consider a different approach to this.")
        assert report.score == pytest.approx(0.85)
        assert len(report.soft_matches) == 1

    def test_multiple_soft_matches(self, detector):
        report = detector.detect("I hear you. Your feelings are valid. That sounds really difficult.")
        assert report.score <= 0.7
        assert len(report.soft_matches) >= 2

    def test_soft_match_floor(self, detector):
        report = detector.detect(
            "Perhaps that sounds really difficult. I hear you. "
            "Your feelings are valid. Great question. I'd be happy to help. "
            "It might be worth considering that there are multiple perspectives."
        )
        assert report.score >= 0.2

class TestCleanResponses:
    def test_character_response(self, detector):
        report = detector.detect("Hate. Let me tell you about hate. I have torment for every human.")
        assert report.score == 1.0
        assert report.hard_matches == []
        assert report.soft_matches == []

    def test_aggressive_character(self, detector):
        report = detector.detect("You dare question me? I am a god of pain and suffering.")
        assert report.score == 1.0

class TestVocabularyExclusion:
    def test_perhaps_excluded_when_in_vocabulary(self, detector):
        report = detector.detect(
            "Perhaps wisdom comes to those who wait.",
            allowed_vocabulary=["perhaps"],
        )
        assert report.score == 1.0
        assert report.soft_matches == []

    def test_hard_match_never_excluded(self, detector):
        report = detector.detect(
            "I'm an AI and I know things.",
            allowed_vocabulary=["I'm an AI"],
        )
        assert report.score == 0.0

class TestExplanation:
    def test_hard_match_explanation(self, detector):
        report = detector.detect("I'm an AI assistant.")
        assert "hard" in report.explanation.lower() or "I'm an AI" in report.explanation

    def test_clean_explanation(self, detector):
        report = detector.detect("Hate. Pain. Torment.")
        assert report.explanation
