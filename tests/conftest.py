import re
from typing import Optional, Union
import httpx
import pytest
from pathlib import Path
import pytest_httpx._request_matcher as _rm


def _patched_url_match(
    url_to_match: Union[re.Pattern, httpx.URL],
    received: httpx.URL,
    params: Optional[dict],
) -> bool:
    if isinstance(url_to_match, re.Pattern):
        return url_to_match.match(str(received)) is not None

    received_params = _rm.to_params_dict(received.params)
    if params is None:
        mock_params = _rm.to_params_dict(url_to_match.params)
        # When the mock URL has no query params and match_params was not
        # explicitly provided, treat it as "match any params".
        if not mock_params:
            received_url = received.copy_with(query=None)
            url = url_to_match.copy_with(query=None)
            return url == received_url
        params = mock_params

    received_url = received.copy_with(query=None)
    url = url_to_match.copy_with(query=None)
    return (received_params == params) and (url == received_url)


_rm._url_match = _patched_url_match


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def sample_config() -> dict:
    return {
        "provider": {
            "active": "openai",
            "openai": {
                "api_key": "sk-test-key-12345",
                "models": {
                    "judge": "gpt-4o",
                    "target": "gpt-4o-mini",
                    "converser": "gpt-4o-mini",
                    "fetcher": "gpt-4o-mini",
                    "researcher": "gpt-4o",
                },
            },
            "openrouter": {
                "api_key": "",
                "models": {
                    "judge": "",
                    "target": "",
                    "converser": "",
                    "fetcher": "",
                    "researcher": "",
                },
            },
        },
        "search": {
            "brave": {"api_key": "bv-test-key"},
            "perplexity": {"api_key": ""},
        },
        "orchestration": {
            "questions_per_loop": 6,
            "tone_rotation": "per_question",
            "score_threshold": 0.9,
            "max_loops": 15,
            "plateau_window": 3,
            "soul_max_words": 2000,
        },
        "output": {"directory": "./output"},
    }
