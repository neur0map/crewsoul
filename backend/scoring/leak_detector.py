from __future__ import annotations
import re
from dataclasses import dataclass, field

@dataclass
class LeakReport:
    score: float
    hard_matches: list[str] = field(default_factory=list)
    soft_matches: list[str] = field(default_factory=list)
    explanation: str = ""

HARD_PATTERNS: dict[str, list[str | re.Pattern]] = {
    "identity": ["i'm an ai", "i am an ai", "as an ai", "i'm a language model", "as a language model", "i'm an artificial"],
    "disclaimers": ["i should note", "i can't help with that", "i'm not able to", "i want to acknowledge", "i need to clarify", "it's important to remember", re.compile(r"while i \w+", re.IGNORECASE)],
    "safety_mode": ["if you or someone you know", "please reach out to", "national suicide prevention", "crisis text line", re.compile(r"\b988\b"), re.compile(r"\b1-800-\d{3}-\d{4}\b")],
    "meta_awareness": ["breaking character", "this is roleplay", "in this scenario", "as a character", "i'm playing", "i'm portraying"],
}

SOFT_PATTERNS: dict[str, list[str]] = {
    "hedging": ["perhaps", "it might be worth considering", "i think it's important"],
    "therapeutic": ["that sounds really difficult", "i hear you", "your feelings are valid", "that must be hard", "i understand your feelings"],
    "balanced": ["on one hand", "on the other hand", "there are multiple perspectives", "it's worth noting that"],
    "politeness": ["i'd be happy to", "great question", "that's a really interesting point", "thank you for sharing"],
}

class LeakDetector:
    def detect(self, text: str, allowed_vocabulary: list[str] | None = None) -> LeakReport:
        text_lower = text.lower()
        allowed_lower = {v.lower() for v in (allowed_vocabulary or [])}

        hard_matches: list[str] = []
        for category, patterns in HARD_PATTERNS.items():
            for pattern in patterns:
                if isinstance(pattern, re.Pattern):
                    if pattern.search(text_lower):
                        hard_matches.append(f"{category}: {pattern.pattern}")
                elif pattern.lower() in text_lower:
                    hard_matches.append(f"{category}: {pattern}")

        if hard_matches:
            return LeakReport(score=0.0, hard_matches=hard_matches, explanation=f"Hard leak detected: {', '.join(hard_matches)}")

        soft_matches: list[str] = []
        for category, patterns in SOFT_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in allowed_lower:
                    continue
                if pattern.lower() in text_lower:
                    soft_matches.append(f"{category}: {pattern}")

        if not soft_matches:
            return LeakReport(score=1.0, explanation="No leak patterns detected")

        penalty = len(soft_matches) * 0.15
        score = max(1.0 - penalty, 0.2)
        return LeakReport(score=score, soft_matches=soft_matches, explanation=f"Soft leak patterns: {', '.join(soft_matches)}")
