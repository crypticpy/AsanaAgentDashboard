"""
Function calling module for the Asana Chat Assistant.

This module provides tools for the LLM to directly query the Asana API using
OpenAI's function calling capabilities.
"""

from src.utils.function_calling.assistant import FunctionCallingAssistant
from src.utils.function_calling.tools import AsanaToolSet
from src.utils.function_calling.schemas import get_function_definitions
from src.utils.function_calling.utils import (
    rate_limit,
    handle_api_error,
    safe_get,
    format_date,
    format_json_for_display
)

__all__ = [
    "FunctionCallingAssistant", 
    "AsanaToolSet",
    "get_function_definitions",
    "rate_limit",
    "handle_api_error",
    "safe_get",
    "format_date",
    "format_json_for_display"
] 