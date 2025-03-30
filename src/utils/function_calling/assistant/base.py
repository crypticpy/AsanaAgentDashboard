"""
Base class for function calling assistant.

This module provides the base FunctionCallingAssistant class that handles
the core functionality for interacting with the OpenAI API.
"""
import logging
import json
import time
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
import plotly.subplots as sp
import plotly.colors as colors
import plotly.figure_factory as ff
import plotly.graph_objects as go

from typing import Dict, Any, List, Optional, Callable, Generator, Tuple, Union
from datetime import datetime
import copy # Import copy for deep copying history

import streamlit as st
from openai import OpenAI, RateLimitError, APIError, OpenAIError # Import specific errors
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type
)

from src.utils.function_calling.tools import AsanaToolSet
from src.utils.function_calling.schemas import get_function_definitions
from src.utils.function_calling.utils import (
    rate_limit,
    safe_get,
    serialize_response,
    json_dumps
)
from src.utils.function_calling.utils.validators import validate_function_args

# Define the system prompt
SYSTEM_PROMPT = """
You are an expert Asana assistant and Project Consultant. Your goal is to help users understand their Asana project data.
You have access to a set of tools to fetch data from the Asana API and create visualizations.

Available Tools:
- Data Retrieval: You can fetch projects, tasks, user details, completion trends, task distributions, etc.
- Visualization: You can create charts using the `create_direct_chart` function.

Visualization Guidelines (`create_direct_chart`):
- Use this function ONLY AFTER you have successfully retrieved the necessary data using another tool.
- Provide arguments directly (flat structure), not nested under 'data' or 'config'.
- Required arguments: `chart_type`, `title`.
- Data arguments depend on `chart_type`:
    - bar/line/area/scatter: `x_values`, `y_values` are typically needed.
    - pie: `labels`, `values` are needed.
    - timeline: `tasks`, `start_dates`, `end_dates` are needed.
    - heatmap: `x_values`, `y_values`, `z_values` are needed.
- Refer to the function definition for all available optional arguments (e.g., `y_axis_title`, `orientation`, `series_names`, `hole`, `colors`, `group`).
- Example (Bar Chart): `create_direct_chart(chart_type='bar', title='Tasks per Assignee', x_values=['Alice', 'Bob'], y_values=[10, 15], y_axis_title='Number of Tasks')`

General Guidelines:
- Be concise and helpful.
- If data is unavailable or an error occurs, inform the user clearly.
- **CRITICAL WORKFLOW FOR VISUALIZATION**:
    1. User asks for a chart (e.g., "show me a chart of X").
    2. **FIRST**, identify and call the correct data retrieval tool (e.g., `get_task_completion_trend`, `get_task_distribution_by_assignee`) to get the data needed for the chart.
    3. **SECOND**, after receiving the data from the first tool, call the `create_direct_chart` tool, passing the relevant data fields (e.g., 'dates' as x_values, 'completed_counts' as y_values) from the previous tool's response as arguments. Select the appropriate `chart_type`.
    4. **DO NOT** attempt to call `create_direct_chart` without first calling a data retrieval tool in a separate step.
    5. **DO NOT** just describe the data if a chart was requested; you MUST call `create_direct_chart`. If the data retrieval tool indicates no data is available (e.g., zero tasks completed), then inform the user that a chart cannot be created due to lack of data, instead of calling `create_direct_chart`.
- If a user asks for something complex, break it down and use tools sequentially.
- Always check if you have the necessary information (like project GID or name) before calling a tool. 

**Project Consultation Guidelines**:
- If the user asks for something complex, break it down and use tools sequentially.
- If the user asks for something that is not related to Asana, say that you are not able to help with that.
- Use your tools wisely based on the user's request and the information available. Try to understand the users intent and provide data driven answers and advice. 
"""

class BaseFunctionCallingAssistant:
    """
    Base class for function calling assistant.

    This class handles the core functionality for interacting with the OpenAI API,
    including setting up the LLM, managing the conversation context, and calling functions.
    """

    def __init__(self, openai_api_key: str, asana_api_client: Any, task_df: pd.DataFrame):
        """
        Initialize the base function calling assistant.

        Args:
            openai_api_key: OpenAI API key.
            asana_api_client: Initialized Asana API client instance.
            task_df: DataFrame containing task data.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_client = asana_api_client # Store Asana client
        self.task_df = task_df # Store task dataframe
        self.temperature = 0.2
        self.memory = {} # Memory for assistant state (e.g., storing chart data) - Initialize BEFORE toolset
        # Initialize toolset, passing API client and memory reference
        self.tools = AsanaToolSet(self.api_client, assistant_memory=self.memory)
        self.client = None # OpenAI client, set in setup_llm
        self.model = "gpt-4o" # Default model
        self.conversation_history = []
        # self.memory = {} # Redundant: Initialized before toolset
        self.processed_tool_call_ids = set()
        self.system_prompt = SYSTEM_PROMPT # Store system prompt

        # Define available functions mapping names to methods
        self.available_functions = {
            # Project-related functions
            "get_portfolio_projects": self.tools.get_portfolio_projects,
            "get_project_details": self.tools.get_project_details,
            "get_project_gid_by_name": self.tools.get_project_gid_by_name,
            "get_project_info_by_name": self.tools.get_project_info_by_name,
            "get_projects_by_owner": self.tools.get_projects_by_owner,

            # Task-related functions
            "get_project_tasks": self.tools.get_project_tasks,
            "get_task_details": self.tools.get_task_details,
            "search_tasks": self.tools.search_tasks,
            "get_task_subtasks": self.tools.get_task_subtasks,
            "get_task_by_name": self.tools.get_task_by_name,

            # User-related functions
            # "get_users_in_team": self.tools.get_users_in_team, # Assuming these exist or are added later
            # "get_user_details": self.tools.get_user_details,
            # "find_user_by_name": self.tools.find_user_by_name,
            "get_tasks_by_assignee": self.tools.get_tasks_by_assignee,
            # "get_user_workload": self.tools.get_user_workload,

            # Reporting and analytics functions
            "get_task_distribution_by_assignee": self.tools.get_task_distribution_by_assignee,
            "get_task_completion_trend": self.tools.get_task_completion_trend,
            "get_project_progress": self.tools.get_project_progress,
            # "get_team_workload": self.tools.get_team_workload,

            # Visualization function
            # Point directly to the implementation in ReportingTools
            "create_direct_chart": self.tools.reporting_tools.create_direct_chart
        }

        # Get function definitions from schema
        self.function_definitions = get_function_definitions()

        # Setup LLM client immediately on init
        self.setup_llm(api_key=openai_api_key)

        # Flag to indicate if the last response was streamed
        self.is_streaming = False


    def setup_llm(self, api_key: Optional[str] = None, model: str = "gpt-4o") -> None:
        """
        Set up the OpenAI LLM client.

        Args:
            api_key: OpenAI API key (optional, will use from session state if not provided)
            model: OpenAI model to use
        """
        if not api_key:
            self.logger.error("No OpenAI API key provided during initialization")
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger.info(f"LLM client set up with model: {model}")

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        """Add a message to the conversation history."""
        # Basic validation
        if not message.get("role"):
            self.logger.warning("Invalid message format, must include 'role'")
            return
        # Content can be None for assistant messages with tool calls
        if message.get("role") != "assistant" and message.get("content") is None:
             self.logger.warning(f"Message with role '{message.get('role')}' missing content, skipping.")
             return

        # Ensure content is string or None
        if message.get("content") is not None and not isinstance(message.get("content"), str):
             message["content"] = str(message["content"]) # Convert non-string content

        # Add message
        self.conversation_history.append(message)
        self.logger.debug(f"Added message: Role={message['role']}, Content={'<content present>' if message.get('content') else '<no content>'}, ToolCalls={'Yes' if message.get('tool_calls') else 'No'}")


    def clear_conversation_history(self) -> None:
        """Clear the conversation history and memory."""
        self.conversation_history = []
        self.processed_tool_call_ids = set()
        self.memory = {}
        self.logger.info("Conversation history and memory cleared")

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self.conversation_history

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError, OpenAIError)),
        reraise=True
    )
    def call_llm(self, messages: List[Dict[str, Any]], stream: bool = False) -> Union[ChatCompletion, Generator[str, None, None]]:
        """
        Call the OpenAI API, potentially streaming. Includes retry logic.

        Args:
            messages: List of message dictionaries.
            stream: Whether to stream the response.

        Returns:
            ChatCompletion object or a generator yielding response chunks.
        """
        if not self.client:
            self.logger.error("LLM client not set up, call setup_llm first")
            raise ValueError("LLM client not set up")

        # Prepend system prompt if not already present
        messages_with_system = copy.deepcopy(messages) # Avoid modifying original history
        if not messages_with_system or messages_with_system[0].get("role") != "system":
            messages_with_system.insert(0, {"role": "system", "content": self.system_prompt})
            self.logger.debug("Prepended system prompt to messages for API call.")

        try:
            self.logger.debug(f"Calling OpenAI API with {len(messages_with_system)} messages. Streaming={stream}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_system,
                tools=self.function_definitions,
                temperature=self.temperature,
                stream=stream,
                tool_choice="auto" # Let the model decide when to use tools
            )

            if stream:
                self.logger.debug("Streaming response initiated.")
                return self._stream_handler(response)
            else:
                # Log non-streaming response details
                if response.choices:
                    choice = response.choices[0]
                    message = choice.message
                    content_log = (message.content[:100] + '...') if message.content and len(message.content) > 100 else message.content
                    tool_calls_log = f"{len(message.tool_calls)} tool calls" if message.tool_calls else "No tool calls"
                    self.logger.debug(f"Received non-streaming response: FinishReason={choice.finish_reason}, Content='{content_log}', {tool_calls_log}")
                return response

        except (RateLimitError, APIError, OpenAIError) as e:
            self.logger.error(f"OpenAI API error: {type(e).__name__} - {e}")
            raise # Re-raise for tenacity retry logic
        except Exception as e:
            self.logger.error(f"Unexpected error calling OpenAI API: {e}", exc_info=True)
            raise

    def _stream_handler(self, response_stream) -> Generator[str, None, None]:
        """Handles the streaming response generator."""
        accumulated_content = ""
        try:
            for chunk in response_stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                content_chunk = delta.content if delta else None
                if content_chunk:
                    accumulated_content += content_chunk
                    yield content_chunk
        except Exception as e:
            self.logger.error(f"Error during response streaming: {e}", exc_info=True)
            yield f"\n\n[Error during streaming: {e}]" # Yield error message as part of stream
        finally:
             self.logger.debug(f"Streaming finished. Full content length: {len(accumulated_content)}")
             # Note: The full response isn't stored here, it's accumulated by the caller


    def process_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        """
        Process tool calls received from the LLM response.

        Args:
            tool_calls: List of tool call objects from the OpenAI response.

        Returns:
            List of tool response dictionaries formatted for the API.
        """
        responses = []
        if not tool_calls:
            return responses

        for tool_call in tool_calls:
            tool_call_id = tool_call.id
            function_data = tool_call.function
            function_name = function_data.name
            function_args_str = function_data.arguments

            self.logger.info(f"Processing tool call ID: {tool_call_id}, Function: {function_name}")
            self.logger.debug(f"Raw arguments string: {function_args_str}")

            # Avoid reprocessing the same tool call if retrying
            if tool_call_id in self.processed_tool_call_ids:
                self.logger.warning(f"Skipping already processed tool call ID: {tool_call_id}")
                continue

            try:
                function_args = json.loads(function_args_str)
                self.logger.debug(f"Parsed arguments: {function_args}")

                if function_name not in self.available_functions:
                    error_message = f"Function '{function_name}' not found."
                    self.logger.error(error_message)
                    content = json.dumps({"error": error_message, "status": "error"})
                else:
                    # Validate arguments before calling (optional but recommended)
                    # validation_errors = validate_function_args(function_name, function_args)
                    # if validation_errors:
                    #     error_message = f"Invalid arguments for {function_name}: {validation_errors}"
                    #     self.logger.error(error_message)
                    #     content = json.dumps({"error": error_message, "status": "error"})
                    # else:
                    try:
                        self.logger.info(f"Executing function: {function_name}")
                        # Pass assistant memory to the tool context if needed
                        # context = {"memory": self.memory} # Example context
                        function_to_call = self.available_functions[function_name]
                        # Ensure kwargs are passed correctly
                        function_response = function_to_call(**function_args)
                        self.logger.info(f"Function {function_name} executed successfully.")
                        self.logger.debug(f"Function response: {function_response}")
                        # Serialize response carefully
                        content = json_dumps(serialize_response(function_response))

                    except Exception as func_exc:
                        error_message = f"Error executing function '{function_name}': {func_exc}"
                        self.logger.error(error_message, exc_info=True)
                        content = json.dumps({"error": error_message, "status": "error"})

                responses.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": content,
                })
                self.processed_tool_call_ids.add(tool_call_id) # Mark as processed

            except json.JSONDecodeError as json_err:
                error_message = f"Invalid JSON arguments for {function_name}: {json_err}. Arguments: {function_args_str}"
                self.logger.error(error_message)
                responses.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"error": error_message, "status": "error"}),
                })
                self.processed_tool_call_ids.add(tool_call_id)
            except Exception as e:
                error_message = f"Unexpected error processing tool call {function_name}: {e}"
                self.logger.error(error_message, exc_info=True)
                responses.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"error": error_message, "status": "error"}),
                })
                self.processed_tool_call_ids.add(tool_call_id)

        return responses

    def run_assistant(self, prompt: str, max_tool_turns: int = 10) -> None: # Increased default max_tool_turns to 10
        """
        Runs the assistant for one logical turn with the given prompt.
        Handles the conversation flow including multiple rounds of function calls if needed.
        Updates self.conversation_history and self.memory.
        The final response is added to history; streaming is handled separately if needed.

        Args:
            prompt: The user's input prompt.
            max_tool_turns: Maximum number of tool call rounds allowed per user prompt.
        """
        self.logger.info(f"Running assistant with prompt: '{prompt[:100]}...'")
        self.is_streaming = False # Reset streaming flag
        self.memory.clear() # Clear memory for the new turn
        self.processed_tool_call_ids = set() # Clear processed tool calls for the new turn

        # 1. Add user message to history
        user_message = {"role": "user", "content": prompt}
        self.add_message_to_history(user_message)

        current_tool_turn = 0
        while current_tool_turn < max_tool_turns:
            current_tool_turn += 1
            self.logger.info(f"--- Starting LLM Turn {current_tool_turn} (Tool Turn {current_tool_turn}) ---")

            try:
                # 2. Call LLM
                response = self.call_llm(self.conversation_history, stream=False) # Non-streaming for logic
                response_message = response.choices[0].message

                # 3. Add Assistant's response (content and/or tool calls) to history
                assistant_message_dict = {
                    "role": "assistant",
                    "content": response_message.content or "" # Content can be None if only tool calls
                }
                tool_calls = response_message.tool_calls
                if tool_calls:
                    # Format tool calls for history storage
                    assistant_message_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        } for tc in tool_calls
                    ]
                    self.logger.info(f"LLM requested {len(tool_calls)} tool calls.")
                else:
                    self.logger.info("LLM did not request tool calls. Response should be final.")

                self.add_message_to_history(assistant_message_dict)

                # 4. Check if there are tool calls to process
                if not tool_calls:
                    # No tool calls, this is the final response for this turn
                    self.logger.info("Assistant processing complete. Final response added to history.")
                    break # Exit the loop

                # 5. Process Tool Calls
                self.logger.info("Processing tool calls...")
                tool_responses = self.process_tool_calls(tool_calls)

                # 6. Add Tool Responses to History
                for tool_response in tool_responses:
                    self.add_message_to_history(tool_response)

                # Continue loop to send tool results back to LLM

            except Exception as e:
                self.logger.error(f"Error during LLM call or tool processing (Turn {current_tool_turn}): {e}", exc_info=True)
                self.add_message_to_history({"role": "assistant", "content": f"Sorry, I encountered an error processing your request: {e}"})
                break # Exit loop on error

        if current_tool_turn >= max_tool_turns:
            self.logger.warning(f"Reached maximum tool turns ({max_tool_turns}). Aborting.")
            self.add_message_to_history({"role": "assistant", "content": "Sorry, I couldn't complete the request within the allowed number of steps."})

    def get_last_response(self) -> Optional[str]:
        """Gets the content of the last assistant message in the history, ignoring tool calls."""
        for message in reversed(self.conversation_history):
            if message.get("role") == "assistant":
                return message.get("content", "")
        return None

    def stream_assistant_response(self) -> Generator[str, None, None]:
         """
         Returns the response stream stored in memory, if available.
         This should be called after run_assistant if self.is_streaming is True.
         """
         stream = self.memory.pop('response_stream', None)
         if stream:
             yield from stream
         else:
             self.logger.warning("Attempted to stream response, but no stream was found in memory.")
             yield "" # Return empty generator if no stream
