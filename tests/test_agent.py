from google.adk.agents import LlmAgent

from adk_01_pit_wall import agent
from adk_01_pit_wall.budget import LlmCallBudget
from adk_01_pit_wall.prompts import DESCRIPTION, INSTRUCTION
from adk_01_pit_wall.settings import Settings
from adk_01_pit_wall.tool_errors import report_tool_error

from .tools.support import FakeRaceData


def test_build_agent_wires_tools_and_callbacks():
    settings = Settings(_env_file=None, GOOGLE_API_KEY="key", PIT_WALL_MODEL="m")

    built = agent.build_agent(settings, FakeRaceData())

    assert isinstance(built, LlmAgent)
    assert (built.name, built.model) == (agent.AGENT_NAME, "m")
    assert (built.description, built.instruction) == (DESCRIPTION, INSTRUCTION)
    assert [tool.__name__ for tool in built.tools] == [
        "get_race_results",
        "get_driver_standings",
        "compare_lap_times",
    ]
    assert isinstance(built.before_model_callback, LlmCallBudget)
    assert built.on_tool_error_callback is report_tool_error


def test_root_agent_is_exposed_for_adk():
    assert isinstance(agent.root_agent, LlmAgent)
    assert agent.root_agent.name == agent.AGENT_NAME


def test_instruction_has_no_state_placeholders():
    assert "{" not in INSTRUCTION
