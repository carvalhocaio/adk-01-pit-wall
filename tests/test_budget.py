from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import cast

import pytest
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_01_pit_wall.budget import CALLS_KEY, EXHAUSTED_REPLY, LlmCallBudget


def context(state: dict[str, int]) -> CallbackContext:
    return cast(CallbackContext, SimpleNamespace(state=state, invocation_id="inv"))


def test_budget_rejects_non_positive_limit():
    with pytest.raises(ValueError, match="at least 1"):
        LlmCallBudget(0)


def test_budget_counts_calls_in_temp_state():
    budget = LlmCallBudget(2)
    state: dict[str, int] = {}

    replies = [budget(context(state), LlmRequest()) for _ in range(3)]

    assert replies[:2] == [None, None]
    assert replies[2] is not None
    assert replies[2].content.parts[0].text == EXHAUSTED_REPLY
    assert state == {CALLS_KEY: 2}
    assert CALLS_KEY.startswith("temp:")


class LoopingLlm(BaseLlm):
    calls: int = 0

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        self.calls += 1
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(function_call=types.FunctionCall(name="ping", args={}))
                ],
            )
        )


def ping() -> dict[str, bool]:
    """Always answers pong."""
    return {"pong": True}


async def invoke(runner: InMemoryRunner, session_id: str) -> str:
    message = types.Content(role="user", parts=[types.Part(text="ping forever")])
    reply = ""
    async for event in runner.run_async(
        user_id="user", session_id=session_id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply += "".join(part.text or "" for part in event.content.parts)
    return reply


async def test_budget_stops_tool_loop_and_resets_per_invocation():
    max_calls = 3
    llm = LoopingLlm(model="looping")
    agent = LlmAgent(
        name="budget_probe",
        model=llm,
        tools=[ping],
        before_model_callback=LlmCallBudget(max_calls),
    )
    runner = InMemoryRunner(agent=agent, app_name="budget_probe")
    session = await runner.session_service.create_session(
        app_name="budget_probe", user_id="user"
    )

    first = await invoke(runner, session.id)
    assert llm.calls == max_calls
    assert first == EXHAUSTED_REPLY

    await invoke(runner, session.id)
    assert llm.calls == 2 * max_calls
