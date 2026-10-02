from google.adk.agents import LlmAgent

from .budget import LlmCallBudget
from .jolpica import JolpicaClient, create_http_client
from .prompts import DESCRIPTION, INSTRUCTION
from .settings import Settings, get_settings
from .tool_errors import report_tool_error
from .tools import PitWallTools, RaceDataSource

AGENT_NAME = "pit_wall"


def build_agent(settings: Settings, source: RaceDataSource) -> LlmAgent:
    pit_wall = PitWallTools(source)
    return LlmAgent(
        name=AGENT_NAME,
        model=settings.agent_model,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=[
            pit_wall.get_race_results,
            pit_wall.get_driver_standings,
            pit_wall.compare_lap_times,
        ],
        before_model_callback=LlmCallBudget(settings.max_llm_calls),
        on_tool_error_callback=report_tool_error,
    )


root_agent = build_agent(get_settings(), JolpicaClient(create_http_client()))
