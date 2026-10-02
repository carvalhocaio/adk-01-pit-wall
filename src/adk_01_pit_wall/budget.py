import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions.state import State
from google.genai import types

CALLS_KEY = f"{State.TEMP_PREFIX}llm_calls"
EXHAUSTED_REPLY = (
    "Pit wall here: this question used up the model call budget before I could "
    "reach an answer. Narrow it down, for example one race and fewer drivers, "
    "and ask again."
)

logger = logging.getLogger(__name__)


class LlmCallBudget:
    def __init__(self, max_calls: int) -> None:
        if max_calls < 1:
            raise ValueError(f"max_calls must be at least 1, got {max_calls}")
        self._max_calls = max_calls

    def __call__(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        used = callback_context.state.get(CALLS_KEY, 0)
        if used < self._max_calls:
            callback_context.state[CALLS_KEY] = used + 1
            return None
        logger.warning(
            "llm call budget exhausted",
            extra={
                "invocation_id": callback_context.invocation_id,
                "max_calls": self._max_calls,
            },
        )
        return LlmResponse(
            content=types.Content(
                role="model", parts=[types.Part(text=EXHAUSTED_REPLY)]
            )
        )
