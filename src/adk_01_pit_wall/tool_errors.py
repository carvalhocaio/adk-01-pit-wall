from typing import Any

import httpx
from google.adk.tools import BaseTool, ToolContext

from .f1 import F1Error
from .jolpica import JolpicaError
from .tools import InvalidToolArgsError

RECOVERABLE_ERRORS = (InvalidToolArgsError, F1Error, JolpicaError, httpx.HTTPError)


def report_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str] | None:
    if not isinstance(error, RECOVERABLE_ERRORS):
        return None
    return {"error": f"{type(error).__name__}: {error}"}
