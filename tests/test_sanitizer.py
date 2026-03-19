from backend.sanitizer import sanitize_llm_output, validate_soul_word_count


def test_strip_thinking_tags():
    text = "Hello <thinking>internal reasoning</thinking> world"
    assert sanitize_llm_output(text) == "Hello  world"


def test_strip_ant_thinking_tags():
    text = "Before <antThinking>plan</antThinking> after"
    assert sanitize_llm_output(text) == "Before  after"


def test_strip_multiline_thinking():
    text = "Start\n<thinking>\nline1\nline2\n</thinking>\nEnd"
    assert sanitize_llm_output(text) == "Start\n\nEnd"


def test_no_tags_unchanged():
    text = "Normal response without any tags"
    assert sanitize_llm_output(text) == text


def test_validate_word_count_under_limit():
    soul = "word " * 1999
    assert validate_soul_word_count(soul, max_words=2000) is True


def test_validate_word_count_over_limit():
    soul = "word " * 2001
    assert validate_soul_word_count(soul, max_words=2000) is False


def test_validate_word_count_exact_limit():
    soul = "word " * 2000
    assert validate_soul_word_count(soul, max_words=2000) is True
