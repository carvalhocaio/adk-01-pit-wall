import pytest
from pydantic import ValidationError

from adk_01_pit_wall.settings import Settings


def settings(**env: str) -> Settings:
    return Settings(_env_file=None, **env)


def test_defaults_with_gemini_api_key():
    loaded = settings(GOOGLE_API_KEY="key")

    assert (loaded.agent_model, loaded.max_llm_calls) == ("gemini-flash-latest", 6)


@pytest.mark.parametrize(
    "env",
    [
        pytest.param({}, id="gemini api without key"),
        pytest.param({"GOOGLE_GENAI_USE_ENTERPRISE": "1"}, id="vertex without project"),
        pytest.param(
            {"GOOGLE_API_KEY": "key", "PIT_WALL_MAX_LLM_CALLS": "0"},
            id="budget below one",
        ),
        pytest.param(
            {
                "GOOGLE_API_KEY": "key",
                "PIT_WALL_MAX_LLM_CALLS": "8",
                "ADK_MAX_LLM_CALLS": "8",
            },
            id="budget not below adk limit",
        ),
    ],
)
def test_invalid_settings(env, monkeypatch):
    for name in ("GOOGLE_API_KEY", "ADK_MAX_LLM_CALLS", "PIT_WALL_MAX_LLM_CALLS"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        settings(**env)


def test_unlimited_adk_calls_accept_any_budget():
    loaded = settings(GOOGLE_API_KEY="key", ADK_MAX_LLM_CALLS="0")

    assert loaded.adk_max_llm_calls == 0
