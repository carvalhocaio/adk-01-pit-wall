from collections.abc import AsyncGenerator
from typing import cast

import httpx
import pytest
from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.runners import InMemoryRunner
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

from adk_01_pit_wall.f1 import StintNotFoundError
from adk_01_pit_wall.jolpica import RateLimitedError
from adk_01_pit_wall.tool_errors import report_tool_error
from adk_01_pit_wall.tools import InvalidToolArgsError


def report(error: Exception) -> dict[str, str] | None:
    return report_tool_error(
        tool=cast(BaseTool, None),
        args={},
        tool_context=cast(ToolContext, None),
        error=error,
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            InvalidToolArgsError("provide exactly one of round or circuit_id"),
            "InvalidToolArgsError: provide exactly one of round or circuit_id",
        ),
        (
            StintNotFoundError("stint 3 requested, driver ran 2"),
            "StintNotFoundError: stint 3 requested, driver ran 2",
        ),
        (RateLimitedError("slow down"), "RateLimitedError: slow down"),
        (httpx.ConnectTimeout("timed out"), "ConnectTimeout: timed out"),
    ],
)
def test_recoverable_errors_reach_the_model(error, expected):
    assert report(error) == {"error": expected}


def test_unexpected_errors_are_left_to_propagate():
    assert report(KeyError("bug")) is None


class ScriptedLlm(BaseLlm):
    turns: int = 0

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        self.turns += 1
        part = (
            types.Part(function_call=types.FunctionCall(name="pit_call", args={}))
            if self.turns == 1
            else types.Part(text="copy that")
        )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


async def run_with_failing_tool(error: Exception) -> list[dict[str, object]]:
    def pit_call() -> dict[str, str]:
        """Calls the car into the pits."""
        raise error

    agent = LlmAgent(
        name="error_probe",
        model=ScriptedLlm(model="scripted"),
        tools=[pit_call],
        on_tool_error_callback=report_tool_error,
    )
    runner = InMemoryRunner(agent=agent, app_name="error_probe")
    session = await runner.session_service.create_session(
        app_name="error_probe", user_id="user"
    )
    message = types.Content(role="user", parts=[types.Part(text="box box")])
    return [
        response.response
        async for event in runner.run_async(
            user_id="user", session_id=session.id, new_message=message
        )
        for response in event.get_function_responses()
    ]


async def test_recoverable_error_becomes_a_function_response():
    responses = await run_with_failing_tool(InvalidToolArgsError("missing season"))

    assert responses == [{"error": "InvalidToolArgsError: missing season"}]


async def test_unexpected_error_aborts_the_run():
    with pytest.raises(KeyError, match="bug"):
        await run_with_failing_tool(KeyError("bug"))
