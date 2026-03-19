import re
import logging

logger = logging.getLogger(__name__)

_THINKING_PATTERNS = [
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL),
    re.compile(r"<antThinking>.*?</antThinking>", re.DOTALL),
    re.compile(r"<reflection>.*?</reflection>", re.DOTALL),
]


def sanitize_llm_output(text: str) -> str:
    original = text
    for pattern in _THINKING_PATTERNS:
        text = pattern.sub("", text)
    if text != original:
        logger.info("Sanitizer stripped thinking tokens (%d chars removed)", len(original) - len(text))
    return text


def validate_soul_word_count(soul_content: str, max_words: int = 2000) -> bool:
    word_count = len(soul_content.split())
    return word_count <= max_words


def word_count(text: str) -> int:
    return len(text.split())
