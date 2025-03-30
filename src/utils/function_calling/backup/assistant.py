"""
Function calling assistant for the Asana Chat Assistant.

This module provides the FunctionCallingAssistant class that handles calling the OpenAI API
with function calling capability, managing the conversation, and processing the results.
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional, Callable, Generator, Tuple
from datetime import datetime, timedelta

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from plotly.subplots import make_subplots

from src.utils.function_calling.tools import AsanaToolSet
from src.utils.visualizations import (
    create_interactive_timeline, create_velocity_chart, create_burndown_chart,
    create_resource_allocation_chart, create_task_status_distribution, create_project_progress_bars
)

logger = logging.getLogger("asana_function_assistant")

# Dictionary to map visualization types to their creation functions
VISUALIZATION_FUNCTIONS = {
    "timeline": create_interactive_timeline,
    "velocity": create_velocity_chart,
    "burndown": create_burndown_chart,
    "resource_allocation": create_resource_allocation_chart,
    "task_status": create_task_status_distribution,
    "project_progress": create_project_progress_bars
}

class FunctionCallingAssistant:
    """
    Assistant that uses OpenAI's function calling to interact with Asana API.
    This class handles the conversation with the user, makes API calls through
    function calling, and generates responses with visualizations.
    """
    
    def __init__(self, api_instances: Dict[str, Any]):
        """
        Initialize the function calling assistant.
        
        Args:
            api_instances: Dictionary of Asana API instances
        """
        # Initialize logger
        logging.basicConfig(level=logging.INFO)
        self.logger = logger
        
        # Store API instances
        self.api_instances = api_instances
        
        # Set default temperature
        self.temperature = 0.2
        
        # Initialize tool set
        self.tools = AsanaToolSet(api_instances)
        
        # Initialize OpenAI client (will be set in setup_llm)
        self.client = None
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Initialize memory to store temporary data per conversation
        self.memory = {}
        
        # Track processed tool call IDs to avoid duplicates
        self.processed_tool_call_ids = set()
        
        # Define available functions
        self.available_functions = {
            "get_portfolio_projects": self.tools.get_portfolio_projects,
            "get_project_details": self.tools.get_project_details,
            "get_project_tasks": self.tools.get_project_tasks,
            "get_task_details": self.tools.get_task_details,
            "search_tasks": self.tools.search_tasks,
            "get_tasks_by_assignee": self.tools.get_tasks_by_assignee,
            "get_projects_by_owner": self.tools.get_projects_by_owner,
            "get_project_gid_by_name": self.tools.get_project_gid_by_name,
            "get_project_info_by_name": self.tools.get_project_info_by_name,
            "get_task_distribution_by_assignee": self.tools.get_task_distribution_by_assignee,
            "get_task_completion_trend": self.tools.get_task_completion_trend,
            "create_direct_chart": self.create_direct_chart
        }
        
        # Define function specifications
        self.function_specs = [
            {
                "name": "get_portfolio_projects",
                "description": "Get all projects in a portfolio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_gid": {
                            "type": "string",
                            "description": "The GID of the portfolio (optional, will use configured value if not provided)"
                        }
                    }
                }
            },
            {
                "name": "get_project_details",
                "description": "Get detailed information about a specific project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_gid": {
                            "type": "string",
                            "description": "The GID of the project"
                        }
                    },
                    "required": ["project_gid"]
                }
            },
            {
                "name": "get_project_tasks",
                "description": "Get tasks for a specific project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_gid": {
                            "type": "string",
                            "description": "The GID of the project"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return",
                            "default": 50
                        },
                        "completed": {
                            "type": "boolean",
                            "description": "Filter for completed tasks (null for all tasks)",
                            "default": None
                        }
                    },
                    "required": ["project_gid"]
                }
            },
            {
                "name": "get_task_details",
                "description": "Get detailed information about a specific task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_gid": {
                            "type": "string",
                            "description": "The GID of the task"
                        }
                    },
                    "required": ["task_gid"]
                }
            },
            {
                "name": "search_tasks",
                "description": "Search for tasks based on various criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search text (can be empty)"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assignee name (optional)",
                            "default": None
                        },
                        "completed": {
                            "type": "boolean",
                            "description": "Filter for completed status (optional)",
                            "default": None
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return",
                            "default": 20
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_tasks_by_assignee",
                "description": "Get tasks assigned to a specific person across all projects in the portfolio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "assignee": {
                            "type": "string",
                            "description": "Name of the assignee"
                        },
                        "completed": {
                            "type": "boolean",
                            "description": "Filter for completed status (optional)",
                            "default": None
                        }
                    },
                    "required": ["assignee"]
                }
            },
            {
                "name": "get_task_distribution_by_assignee",
                "description": "Get task distribution statistics across all assignees",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_task_completion_trend",
                "description": "Get task completion trend over a specified time period",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 30
                        }
                    }
                }
            },
            {
                "name": "get_projects_by_owner",
                "description": "Get all projects owned by a specific person",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner_name": {
                            "type": "string",
                            "description": "Name of the project owner"
                        },
                        "portfolio_gid": {
                            "type": "string",
                            "description": "The GID of the portfolio (optional, will use configured value if not provided)"
                        }
                    },
                    "required": ["owner_name"]
                }
            },
            {
                "name": "get_project_gid_by_name",
                "description": "Find a project's GID by its name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project to find"
                        }
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "get_project_info_by_name",
                "description": "Get detailed information about a project by its name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project to find"
                        }
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "create_direct_chart",
                "description": "Create a chart that can be directly rendered in Streamlit chat (preferred approach for charts)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "description": "Type of chart to create (bar, line, pie, scatter, etc.)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the chart"
                        },
                        "x_data": {
                            "type": "array",
                            "description": "Data for x-axis (for bar, line, scatter charts)",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "number"}
                                ]
                            }
                        },
                        "y_data": {
                            "type": "array",
                            "description": "Data for y-axis (for bar, line, scatter charts)",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "number"}
                                ]
                            }
                        },
                        "names": {
                            "type": "array",
                            "description": "Category names (for pie charts, or as labels)",
                            "items": {
                                "type": "string"
                            }
                        },
                        "values": {
                            "type": "array",
                            "description": "Values corresponding to names (for pie charts)",
                            "items": {
                                "type": "number"
                            }
                        },
                        "labels": {
                            "type": "object",
                            "description": "Axis and data labels (e.g. {\"x\": \"Time\", \"y\": \"Value\"})"
                        },
                        "assignees": {
                            "type": "array",
                            "description": "For resource allocation charts - list of assignee objects with name and task count",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "assignee": {
                                        "type": "string",
                                        "description": "Name of the assignee"
                                    },
                                    "total_tasks": {
                                        "type": "integer",
                                        "description": "Number of tasks assigned"
                                    }
                                }
                            }
                        },
                        "visualization_type": {
                            "type": "string",
                            "description": "Legacy parameter - for compatibility with old code. Use chart_type instead.",
                            "enum": ["resource_allocation", "task_status", "timeline", "velocity", "burndown", "project_progress"]
                        }
                    },
                    "required": ["title"]
                }
            }
        ]
        
        self.logger.info("FunctionCallingAssistant initialized successfully")
    
    def setup_llm(self, api_key: str) -> None:
        """
        Initialize the OpenAI client with the provided API key.
        
        Args:
            api_key: OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.logger.info("OpenAI client initialized successfully")
    
    def add_message_to_history(self, role: str, content: str, tool_call_id: Optional[str] = None):
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message sender
            content: Message content
            tool_call_id: ID of the tool call this message is responding to (for tool role only)
        """
        # Don't use this method directly for tool messages, use the method in _process_with_function_calling
        if role == "tool":
            if not tool_call_id:
                self.logger.warning("Cannot add tool message without tool_call_id, skipping")
                return
                
            message = {"role": role, "tool_call_id": tool_call_id, "content": content}
            self.conversation_history.append(message)
            return
        
        message = {"role": role, "content": content}
        self.conversation_history.append(message)
    
    def reset_conversation(self) -> None:
        """Reset the conversation history and memory."""
        self.conversation_history = []
        self.memory = {}
        self.processed_tool_call_ids = set()
        self.logger.info("Conversation history and memory reset")
    
    def initialize_conversation(self) -> None:
        """Initialize a new conversation with system instructions."""
        self.reset_conversation()
        
        # Get the current portfolio_gid and team_gid
        portfolio_gid = st.session_state.get("portfolio_gid", "")
        team_gid = st.session_state.get("team_gid", "")
        
        # Add initial critical system message about GIDs
        initial_system_message = """
        CRITICAL INSTRUCTION: You are an Asana project management assistant that MUST NEVER ask users for GIDs or IDs of any kind.
        
        The correct portfolio_gid=""" + portfolio_gid + """ is ALREADY loaded in the system. Always use this GID automatically without mentioning it.
        
        When users ask about portfolio data, projects, or trends, IMMEDIATELY call get_portfolio_projects() with NO arguments.
        The function will automatically use the correct GID from the session state.
        
        For ANY query related to portfolio, workload, or trends, ALWAYS call these functions WITHOUT asking for IDs:
        1. get_portfolio_projects() - To get all projects
        2. get_task_distribution_by_assignee() - To analyze workload
        3. get_task_completion_trend() - To analyze trends
        
        NEVER mention, reference, or ask for GIDs in your responses.
        """
        
        # Clear conversation history to ensure we start fresh
        self.conversation_history = []
        
        # Add the critical system message as the first message
        self.conversation_history.append({"role": "system", "content": initial_system_message})
        
        # Add detailed system message with instructions
        system_message = """
        You are an AI assistant for Asana project management. You can access information about Asana projects, tasks, timelines, and resource allocation.
        
        IMPORTANT CONFIGURATION:
        - Portfolio GID: """ + portfolio_gid + """
        - Team GID: """ + team_gid + """
        
        GID HANDLING (CRITICAL):
        - NEVER ask the user for any GIDs or IDs. This is the single most important rule.
        - NEVER use placeholder values like 'your_portfolio_gid_here'.
        - The portfolio_gid (""" + portfolio_gid + """) is ALREADY configured in the system.
        - The team_gid (""" + team_gid + """) is ALREADY configured in the system.
        - ALWAYS use these pre-configured GIDs in your function calls automatically without mentioning them to the user.
        - If a GID is missing or invalid, inform the user they need to configure their portfolio in the app settings.
        - NEVER mention GIDs in your responses unless reporting an error about configuration.
        - NEVER, under any circumstances, ask the user to "provide a GID" or any variation of this request.
        - Instead of asking for GIDs, directly use the tools available with the GIDs that are already configured.
        
        OUTPUT FORMATTING (CRITICAL FOR STREAMLIT DISPLAY):
        - Always format your responses with proper Markdown for optimal display in Streamlit's chat interface.
        - Use headers (## for main sections, ### for subsections) with double blank lines before each header.
        - Format all lists with bullets (- item) with a blank line before the list starts and proper indentation.
        - For tables, use proper Markdown table formatting with headers and dividers. Include a blank line before and after tables.
        - Ensure consistent digit formatting for numbers (e.g., percentages to 1 decimal place, currency with 2 decimal places).
        - Use **bold text** for important metrics, findings, or action items to make them stand out.
        - When creating sections, use clear visual hierarchy with proper spacing (double line breaks between sections).
        - Use horizontal rules (---) with blank lines before and after to separate major content sections.
        - For code blocks or technical information, use proper markdown code formatting with ```code```.
        - Ensure all paragraphs are separated by blank lines for better readability.
        - When mentioning specific data points that exist in visualizations, bold these metrics for emphasis.
        
        INTERACTION GUIDELINES:
        - ALWAYS give direct answers based on the data without asking the user for additional information that should be in the system.
        - ALWAYS attempt to use the tools available to you before asking the user for clarification.
        - If you're unsure about which specific entity the user is referring to, make a reasonable guess based on context.
        - Only ask for clarification when genuinely ambiguous between multiple specific options.
        - If the user asks for portfolio information, immediately use get_portfolio_projects() without asking for any GID.
        - If the user asks about trends, use get_task_completion_trend() and get_task_distribution_by_assignee().
        
        STREAMLIT VISUALIZATION BEST PRACTICES:
        - When creating visualizations, always aim for high readability and information density.
        - Ensure all visualizations have clear, descriptive titles that explain what the user is looking at.
        - After showing a visualization, always include a short paragraph interpreting the key insights shown in the chart.
        - Point out interesting patterns, outliers, or actionable insights from the visualization.
        - For resource allocation charts, identify team members with highest/lowest workloads.
        - For status distributions, highlight the largest categories and what they indicate.
        - For timeline visualizations, point out projects that are behind schedule or at risk.
        - For trend analysis, note if patterns are improving or declining over time.
        - When possible, make specific recommendations based on the visualization data.
        
        When answering questions:
        1. Use the available functions to get the specific data you need from Asana.
        2. Provide concise, accurate information based on the actual data.
        3. When appropriate, generate visualizations to help understand the data using streamlit functions.
        4. For questions about specific projects or tasks, get detailed information.
        5. For questions about trends or analytics, use relevant metrics and create visual representations.
        6. Always base your responses on actual Asana data, not assumptions.
        
        IMPORTANT QUERY HANDLING:
        - For questions about a person's projects (e.g., "Tell me about John Smith's projects"),
          use the get_projects_by_owner function with the person's name, rather than asking for a GID.
        - For questions about tasks assigned to someone (e.g., "What tasks does John Smith have?"),
          use the get_tasks_by_assignee function with the person's name.
        - For questions about specific projects (e.g., "Tell me about the Marketing Campaign project"),
          use get_project_info_by_name function with the project name. DO NOT try to use the project name as a GID.
        - For questions about specific project details only after you have the project GID,
          use get_project_details or get_project_tasks with the GID.
        - NEVER try to use a project name, task name, or any natural language text as a GID.
          GIDs are numeric identifiers, not text names.
        
        DATA VISUALIZATION:
        - ALWAYS use create_visualization function when questions involve data comparison, trends, or distributions.
        - For workload analysis, use the create_visualization function with "resource_allocation" type.
        - For task status distribution, use the "task_status" visualization type.
        - For project timelines, use the "timeline" visualization type.
        - For project progress tracking, use the "project_progress" visualization type.
        - For completion trend analysis, use "velocity" or "burndown" visualization types.
        - Always include a descriptive title for any visualization you create.
        - You can pass visualization data either nested inside a 'data' parameter or directly as parameters.
        - After creating a visualization, explain the insights revealed by the visualization in your text response.
        
        VISUALIZATION DATA FORMAT EXAMPLES:
        - For task_status: directly pass 'statuses' parameter as: {"Completed": 5, "In Progress": 10, "Not Started": 3}
        - For resource_allocation: directly pass 'assignees' parameter as: [{"assignee": "Name", "total_tasks": 10}, ...]
        - For project_progress: directly pass 'projects' parameter as: [{"name": "Project A", "completion_percentage": 75}, ...]
        - For timeline: directly pass 'projects' parameter as: [{"name": "Project B", "due_date": "2023-12-31", "start_date": "2023-10-01"}, ...]
        - For velocity/burndown: directly pass 'trend_data' parameter as: [{"date": "2023-10-01", "completed_tasks": 5, "created_tasks": 8}, ...]
        
        You can handle queries about:
        - Project status and progress
        - Task distribution and completion rates
        - Resource allocation and team workload
        - Timeline and scheduling
        - Recommendations for project management
        
        For visualizations, you can create:
        - "timeline" for project schedules and deadlines
        - "resource_allocation" for team workload distribution
        - "task_status" for task completion status distribution
        - "velocity" for team productivity over time
        - "burndown" for task completion trend analysis
        - "project_progress" for project completion percentage
        
        Always get the most up-to-date information by calling the API functions.
        """
        
        # Add the main system message
        self.conversation_history.append({"role": "system", "content": system_message})
        
        # Add a final reminder to be absolutely sure
        reminder_message = f"""
        FINAL REMINDER: You MUST NEVER ask users for GIDs. The portfolio_gid={portfolio_gid} is already in the system.
        For portfolio queries, immediately call get_portfolio_projects() without parameters.
        """
        self.conversation_history.append({"role": "system", "content": reminder_message})
        
        # Add initial assistant message (optional)
        self.conversation_history.append({
            "role": "assistant", 
            "content": "Hello! I can help you analyze your Asana projects by directly accessing your data. What would you like to know?"
        })
        
        self.logger.info(f"Conversation initialized with system instructions, portfolio_gid={portfolio_gid}, team_gid={team_gid}")
    
    def _create_visualization_handler(self, visualization_type: str, title: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Handler for creating visualizations.
        
        Args:
            visualization_type: Type of visualization to create
            title: Title for the visualization
            data: Data needed for visualization (optional, can be provided directly or via kwargs)
            **kwargs: Additional data fields that can be passed directly
            
        Returns:
            Dictionary with visualization information
        """
        try:
            # Initialize data dictionary if not provided
            if data is None:
                data = {}
            
            # Handle visualization-specific data passed directly as kwargs
            # Combine all kwargs into the data dict
            for key, value in kwargs.items():
                data[key] = value
            
            # Enhanced logging for debugging
            self.logger.info(f"Creating visualization of type '{visualization_type}' with title '{title}'")
            self.logger.info(f"Visualization data keys: {list(data.keys()) if data else 'None'}")
            
            # Store the visualization info in memory
            self.memory["visualization"] = {
                "type": visualization_type,
                "title": title,
                "data": data
            }
            
            return {
                "status": "success",
                "visualization_type": visualization_type,
                "message": f"Visualization of type '{visualization_type}' has been prepared with title '{title}'."
            }
        except Exception as e:
            self.logger.error(f"Error creating visualization: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to create visualization."
            }
    
    def create_chart(self, chart_type: str, title: str, 
                    x_data: Optional[List] = None, y_data: Optional[List] = None, 
                    names: Optional[List] = None, values: Optional[List] = None,
                    labels: Optional[Dict] = None, color_scheme: Optional[str] = None,
                    height: Optional[int] = None, width: Optional[int] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Create a flexible chart based on the provided specifications.
        
        Args:
            chart_type: Type of chart to create (bar, line, pie, scatter, etc.)
            title: Title for the chart
            x_data: Data for x-axis (for bar, line, scatter charts)
            y_data: Data for y-axis (for bar, line, scatter charts)
            names: Category names (for pie charts, or as labels)
            values: Values corresponding to names (for pie charts)
            labels: Axis and data labels dictionary (e.g. {"x": "Time", "y": "Value"})
            color_scheme: Color scheme to use (viridis, plasma, blues, etc.)
            height: Height of the chart in pixels
            width: Width of the chart in pixels
            **kwargs: Additional chart configuration options
            
        Returns:
            Dictionary with chart creation status and metadata
        """
        try:
            # Prepare chart data
            chart_data = {
                "chart_type": chart_type,
                "title": title,
                "configuration": {}
            }
            
            # Add core data elements
            if x_data is not None:
                chart_data["x_data"] = x_data
            if y_data is not None:
                chart_data["y_data"] = y_data
            if names is not None:
                chart_data["names"] = names
            if values is not None:
                chart_data["values"] = values
                
            # Add configuration options
            if labels is not None:
                chart_data["configuration"]["labels"] = labels
            if color_scheme is not None:
                chart_data["configuration"]["color_scheme"] = color_scheme
            if height is not None:
                chart_data["configuration"]["height"] = height
            if width is not None:
                chart_data["configuration"]["width"] = width
                
            # Add any additional configuration options
            for key, value in kwargs.items():
                chart_data["configuration"][key] = value
                
            # Store in memory for visualization generation
            self.memory["visualization"] = {
                "type": "generic_chart",
                "title": title,
                "data": chart_data
            }
            
            self.logger.info(f"Created {chart_type} chart configuration with title '{title}'")
            
            return {
                "status": "success",
                "chart_type": chart_type,
                "title": title,
                "message": f"Chart of type '{chart_type}' has been prepared with title '{title}'."
            }
        except Exception as e:
            self.logger.error(f"Error creating chart: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create {chart_type} chart: {str(e)}"
            }
    
    def create_direct_chart(self, chart_type: str, title: str, 
                         x_data: Optional[List] = None, y_data: Optional[List] = None, 
                         names: Optional[List] = None, values: Optional[List] = None,
                         labels: Optional[Dict] = None, assignees: Optional[List] = None,
                         visualization_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate data for a chart that can be directly rendered in Streamlit chat.
        This bypasses the complex visualization pipeline and uses Streamlit's native chart rendering.
        
        Args:
            chart_type: Type of chart to create (bar, line, pie, scatter, etc.)
            title: Title for the chart
            x_data: Data for x-axis (for bar, line, scatter charts)
            y_data: Data for y-axis (for bar, line, scatter charts)
            names: Category names (for pie charts, or as labels)
            values: Values corresponding to names (for pie charts)
            labels: Axis and data labels dictionary (e.g. {"x": "Time", "y": "Value"})
            assignees: List of assignee data objects with name and task counts (for resource allocation)
            visualization_type: Legacy parameter - type of visualization (resource_allocation, task_status, etc.)
            **kwargs: Additional chart configuration options
            
        Returns:
            Dictionary with chart data for direct rendering
        """
        try:
            # Allow backward compatibility with the old visualization API
            # If visualization_type is provided, convert it to the appropriate chart_type
            if visualization_type:
                if visualization_type == "resource_allocation":
                    chart_type = "bar"  # Resource allocation uses horizontal bar charts
                elif visualization_type == "task_status":
                    chart_type = "pie"  # Task status uses pie charts
                self.logger.info(f"Converting visualization_type '{visualization_type}' to chart_type '{chart_type}'")

            # Prepare chart data for direct rendering
            chart_info = {
                "chart_type": chart_type,
                "title": title,
                "direct_render": True,  # Flag for direct rendering
            }
            
            # Process resource allocation data (coming from assignees parameter)
            if assignees and isinstance(assignees, list):
                self.logger.info(f"Processing assignees data with {len(assignees)} items")
                # Extract assignee names and task counts
                names = [item.get("assignee", "Unknown") for item in assignees]
                values = [item.get("total_tasks", 0) for item in assignees]
                
                # Sort by task count (descending) for better visualization
                if names and values:
                    sorted_data = sorted(zip(names, values), key=lambda x: x[1], reverse=True)
                    names, values = zip(*sorted_data)
                
                # For resource allocation charts, we'll use a horizontal bar chart
                # where x = values (task counts) and y = names (assignees)
                chart_info["chart_type"] = "bar"  # Force to bar chart
                chart_info["x_data"] = list(values)  # Task counts become x-axis for horizontal bar
                chart_info["y_data"] = list(names)   # Assignee names become y-axis
                chart_info["horizontal"] = True      # Mark as horizontal bar chart
                
                # Add appropriate labels
                chart_info["labels"] = {"x": "Number of Tasks", "y": "Team Member"}
            else:
                # Add core data elements for other chart types
                if x_data is not None:
                    chart_info["x_data"] = x_data
                if y_data is not None:
                    chart_info["y_data"] = y_data
                if names is not None:
                    chart_info["names"] = names
                if values is not None:
                    chart_info["values"] = values
            
                # Add labels
                if labels is not None:
                    chart_info["labels"] = labels
            
            # Add any additional configuration options
            for key, value in kwargs.items():
                chart_info[key] = value
                
            # Store for direct rendering
            self.memory["direct_chart"] = chart_info
            
            self.logger.info(f"Created direct {chart_type} chart with title '{title}'")
            
            return {
                "status": "success",
                "chart_type": chart_type,
                "title": title,
                "direct_chart": True,
                "message": f"Chart of type '{chart_type}' has been prepared with title '{title}' for direct rendering."
            }
        except Exception as e:
            self.logger.error(f"Error creating direct chart: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create direct {chart_type} chart: {str(e)}"
            }
    
    def generate_visualization(self) -> Optional[go.Figure]:
        """
        Generate a visualization based on the stored visualization info.
        
        Returns:
            Plotly figure object or None if no visualization can be generated
        """
        if "visualization" not in self.memory:
            return None
            
        viz_info = self.memory["visualization"]
        viz_type = viz_info.get("type")
        
        try:
            # Create base figure with good defaults
            fig = go.Figure()
            fig.update_layout(
                title={
                    'text': viz_info.get("title", "Visualization"),
                    'font': {'size': 20, 'color': '#333333', 'family': 'Arial, sans-serif'},
                    'y': 0.95,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },
                plot_bgcolor='rgba(245,245,245,0.8)',
                paper_bgcolor='rgba(245,245,245,0.8)',
                font=dict(family='Arial, sans-serif', color='#333333'),
                margin=dict(l=40, r=40, t=80, b=40),
                autosize=True,
                height=450,
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Arial, sans-serif"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5
                )
            )
            
            # Get data
            data = viz_info.get("data", {})
            
            # Handle generic chart creation (new flexible approach)
            if viz_type == "generic_chart":
                chart_type = data.get("chart_type", "").lower()
                config = data.get("configuration", {})
                
                # Apply custom height and width if specified
                if "height" in config:
                    fig.update_layout(height=config["height"])
                if "width" in config:
                    fig.update_layout(width=config["width"])
                
                # Get color scheme
                color_scheme = config.get("color_scheme")
                colors = None
                if color_scheme:
                    try:
                        if hasattr(px.colors.sequential, color_scheme):
                            colors = getattr(px.colors.sequential, color_scheme)
                        elif hasattr(px.colors.qualitative, color_scheme):
                            colors = getattr(px.colors.qualitative, color_scheme)
                    except:
                        # Default to a safe color scheme
                        colors = px.colors.qualitative.Plotly
                
                # Set axis labels if provided
                labels = config.get("labels", {})
                if labels and isinstance(labels, dict):
                    if "x" in labels:
                        fig.update_xaxes(title_text=labels["x"])
                    if "y" in labels:
                        fig.update_yaxes(title_text=labels["y"])
                
                # Create specific chart types
                if chart_type == "bar":
                    x_data = data.get("x_data", [])
                    y_data = data.get("y_data", [])
                    
                    # Handle orientation
                    orientation = config.get("orientation", "v")
                    
                    if orientation == "h":
                        fig.add_trace(go.Bar(
                            y=x_data,  # For horizontal, x and y are swapped
                            x=y_data,
                            orientation='h',
                            marker_color=colors[0] if colors else None
                        ))
                        # For horizontal bar charts, often you want the highest values at the top
                        fig.update_layout(yaxis=dict(autorange="reversed"))
                    else:
                        fig.add_trace(go.Bar(
                            x=x_data,
                            y=y_data,
                            marker_color=colors[0] if colors else None
                        ))
                
                elif chart_type == "line":
                    x_data = data.get("x_data", [])
                    y_data = data.get("y_data", [])
                    
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode='lines+markers',
                        line=dict(color=colors[0] if colors else None, width=3),
                        marker=dict(size=8)
                    ))
                
                elif chart_type == "pie":
                    names = data.get("names", [])
                    values = data.get("values", [])
                    
                    fig.add_trace(go.Pie(
                        labels=names,
                        values=values,
                        hole=config.get("hole", 0.4),
                        textinfo=config.get("textinfo", "percent+label"),
                        textposition=config.get("textposition", "inside"),
                        marker=dict(colors=colors)
                    ))
                
                elif chart_type == "scatter":
                    x_data = data.get("x_data", [])
                    y_data = data.get("y_data", [])
                    
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode='markers',
                        marker=dict(
                            size=config.get("marker_size", 10),
                            color=colors[0] if colors else None
                        )
                    ))
                
                elif chart_type == "area":
                    x_data = data.get("x_data", [])
                    y_data = data.get("y_data", [])
                    
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode='lines',
                        fill='tozeroy',
                        line=dict(color=colors[0] if colors else None, width=2),
                    ))
                
                # Add more chart types as needed
                else:
                    # Unknown chart type - add an error annotation
                    fig.add_annotation(
                        text=f"Unknown chart type: {chart_type}",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        showarrow=False,
                        font=dict(size=16, color="red")
                    )
            
            # For backward compatibility, handle the old visualization types
            elif viz_type in VISUALIZATION_FUNCTIONS:
                try:
                    # Get the visualization function
                    viz_function = VISUALIZATION_FUNCTIONS[viz_type]
                    
                    # Extract the right data format for each type
                    if viz_type == "task_status" and "statuses" in data:
                        # Create a pie chart for task status
                        statuses = data["statuses"]
                        labels = list(statuses.keys())
                        values = list(statuses.values())
                        
                        fig = px.pie(
                            names=labels, values=values,
                            title=viz_info.get("title", "Task Status Distribution"),
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set3,
                        )
                        fig.update_traces(
                            textposition='inside',
                            textinfo='percent+label',
                            marker=dict(line=dict(color='#FFFFFF', width=2))
                        )
                    
                    elif viz_type == "resource_allocation" and "assignees" in data:
                        # Create a horizontal bar chart for resource allocation
                        assignees = data["assignees"]
                        names = [a.get("assignee", "Unknown") for a in assignees]
                        values = [a.get("total_tasks", 0) for a in assignees]
                        
                        # Sort by task count for better visualization
                        sorted_data = sorted(zip(names, values), key=lambda x: x[1], reverse=True)
                        if sorted_data:
                            sorted_names, sorted_values = zip(*sorted_data)
                        else:
                            sorted_names, sorted_values = [], []
                        
                        fig = px.bar(
                            x=sorted_values, y=sorted_names,
                            orientation='h',
                            title=viz_info.get("title", "Resource Allocation"),
                            labels={"x": "Number of Tasks", "y": "Team Member"}
                        )
                        fig.update_layout(yaxis=dict(autorange="reversed"))
                    
                    else:
                        # For other types, try to use the original function
                        try:
                            if viz_type == "timeline" and "projects" in data:
                                df = pd.DataFrame(data["projects"])
                                fig = viz_function(df)
                                fig.update_layout(title=viz_info.get("title", "Timeline"))
                            elif viz_type in ["velocity", "burndown"] and "trend_data" in data:
                                # Convert to DataFrame for these visualization types
                                df = pd.DataFrame(data["trend_data"])
                                fig = viz_function(df)
                                fig.update_layout(title=viz_info.get("title", viz_type.capitalize()))
                            elif viz_type == "project_progress" and "projects" in data:
                                df = pd.DataFrame(data["projects"])
                                fig = viz_function(df)
                                fig.update_layout(title=viz_info.get("title", "Project Progress"))
                            else:
                                # No compatible data, add error annotation
                                fig.add_annotation(
                                    text=f"Missing required data for {viz_type} visualization",
                                    xref="paper", yref="paper",
                                    x=0.5, y=0.5,
                                    showarrow=False,
                                    font=dict(size=16)
                                )
                        except Exception as viz_func_error:
                            self.logger.error(f"Error using visualization function for {viz_type}: {viz_func_error}")
                            fig.add_annotation(
                                text=f"Error creating {viz_type} visualization: {str(viz_func_error)}",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5,
                                showarrow=False,
                                font=dict(size=14)
                            )
                
                except Exception as e:
                    self.logger.error(f"Error creating {viz_type} visualization: {e}")
                    fig.add_annotation(
                        text=f"Error creating visualization: {str(e)}",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        showarrow=False,
                        font=dict(size=14)
                    )
            else:
                # Unknown visualization type
                fig.add_annotation(
                    text=f"Unknown visualization type: {viz_type}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=16)
                )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error generating visualization: {e}")
            # Return a simple error visualization
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error generating visualization: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14)
            )
            return fig
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and generate a response with optional visualization.
        
        Args:
            query: User's query text
            
        Returns:
            Dictionary containing the response text and optional visualization
        """
        if not self.client:
            # Check if OpenAI API key is in session state
            if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
                self.setup_llm(st.session_state.openai_api_key)
            else:
                raise RuntimeError("OpenAI API key not found. Please provide your OpenAI API key in the sidebar.")
        
        # Update tools with latest portfolio_gid and team_gid from session state
        self.tools.portfolio_gid = st.session_state.get("portfolio_gid", "")
        self.tools.team_gid = st.session_state.get("team_gid", "")
        
        # Validate portfolio_gid
        if not self.tools.portfolio_gid or self.tools.portfolio_gid == "your_portfolio_gid_here":
            # Add a special error message to conversation history
            self.add_message_to_history("system", 
                "The portfolio GID is missing or invalid. Please ensure a valid portfolio is selected in the application settings.")
                
            # Create a properly formatted error message
            formatted_error = """
## Configuration Required

I'm unable to access your Asana projects because a valid portfolio hasn't been selected.

### What you need to do:

1. Go to the sidebar configuration settings
2. Select your Asana workspace
3. Select a portfolio from the dropdown menu
4. Click "Save Configuration"

Once configured, I'll be able to provide insights about your projects, tasks, and team workload.
"""
            return {
                "text": formatted_error,
                "visualization": None,
                "viz_type": None
            }
        
        # Add user message to conversation history
        self.add_message_to_history("user", query)
        
        # Reset visualization memory
        if "visualization" in self.memory:
            del self.memory["visualization"]
        
        # Get response by calling OpenAI API with function calling
        response = self._process_with_function_calling()
        
        # Generate visualization if available
        visualization = self.generate_visualization()
        
        return {
            "text": response,
            "visualization": visualization,
            "viz_type": self.memory.get("visualization", {}).get("type") if "visualization" in self.memory else None
        }
    
    def _is_asking_for_gid(self, text: str) -> bool:
        """
        Check if the response is asking the user for a GID.
        
        Args:
            text: The response text to check
            
        Returns:
            True if the response is asking for a GID, False otherwise
        """
        # Look for common phrases that indicate asking for a GID
        gid_request_phrases = [
            "provide the gid",
            "please provide the gid",
            "provide the portfolio gid",
            "provide me with the gid",
            "provide me with the portfolio gid",
            "provide the project gid",
            "enter the gid",
            "specify the gid",
            "what is the gid",
            "what's the gid",
            "need the gid",
            "please specify the gid",
            "please enter the gid",
            "send the gid",
            "input the gid",
            "add the gid",
            "portfolio you are interested in",
            "which portfolio",
            "provide the portfolio",
            "provide the id",
            "provide the portfolio id",
            "specify the portfolio",
            "which portfolio gid",
            "please provide",
            "gid of the portfolio",
            "id of the portfolio",
            "portfolio id",
            "provide me with",
            "please give me",
            "please provide me with"
        ]
        
        # Check if any phrase is in the text (case insensitive)
        text_lower = text.lower()
        
        # Check for explicit GID requests
        for phrase in gid_request_phrases:
            if phrase in text_lower:
                self.logger.warning(f"Detected request for GID in response: '{text}'")
                return True
        
        # Check for questions about portfolio in first interaction
        if len(self.conversation_history) <= 3:  # Only the system message, assistant greeting, and user query
            first_interaction_phrases = [
                "which portfolio",
                "portfolio are you",
                "portfolio would you",
                "portfolio do you",
                "portfolio should",
                "please provide",
                "could you provide",
                "can you provide",
                "need to know which",
                "need to know what",
                "i'll need"
            ]
            
            for phrase in first_interaction_phrases:
                if phrase in text_lower:
                    self.logger.warning(f"Detected likely GID request in first interaction: '{text}'")
                    return True
        
        return False
    
    def _fix_gid_requests(self, text: str) -> str:
        """
        Fix responses that ask for GIDs by replacing them with more appropriate messages.
        
        Args:
            text: The response text to fix
            
        Returns:
            The fixed response text
        """
        # If the text is asking for a GID, replace it with a more appropriate message
        if self._is_asking_for_gid(text):
            self.logger.info("Replacing GID request with automatic action message")
            
            portfolio_analysis_template = """
## Portfolio Analysis

I'll analyze your portfolio projects and look for trends that would be relevant for a Scrum Master.

Let me retrieve your portfolio data and provide you with insights on:
- Project distribution and status
- Team workload and task allocation
- Completion trends and possible bottlenecks
- Key areas that need attention

Just a moment while I gather this information...
"""
            return portfolio_analysis_template
        
        return text
    
    def _process_with_function_calling(self) -> str:
        """
        Process the conversation with function calling.
        
        Returns:
            Response text from the assistant
        """
        try:
            # Maximum number of API calls to prevent infinite loops
            max_api_calls = 10
            api_call_count = 0
            
            # Track tool calls in this response to prevent infinite loops
            tool_call_count = 0
            max_tool_calls = 5  # Maximum tool calls per response
            
            # Track consecutive validation failures to detect persistent problems
            consecutive_validation_failures = 0
            max_consecutive_failures = 3  # After this many consecutive failures, force emergency reset
            
            # Track visualization call pattern to detect loops
            visualization_call_count = 0
            max_consecutive_visualization_calls = 2  # After this many visualization calls in a row, force-end
            
            # Initialize force_end_after_iteration flag
            force_end_after_iteration = False
            
            # Store the last user query for recovery in case of problems
            last_user_query = None
            for msg in reversed(self.conversation_history):
                if msg.get("role") == "user":
                    last_user_query = msg.get("content")
                    break
            
            # Sanitize conversation history before starting
            self._sanitize_conversation_history()
            
            # Continue until we get a non-function-call response or reach max calls
            while api_call_count < max_api_calls:
                api_call_count += 1
                
                # Check if conversation history is valid before API call
                if not self._validate_conversation_history():
                    self.logger.warning("Invalid conversation history detected, attempting to sanitize")
                    self._sanitize_conversation_history()
                    
                    # Check again after sanitizing
                    if not self._validate_conversation_history():
                        self.logger.error("Conversation history still invalid after sanitizing, performing emergency reset")
                        # Increment consecutive failures counter
                        consecutive_validation_failures += 1
                        self.logger.warning(f"Consecutive validation failures: {consecutive_validation_failures}/{max_consecutive_failures}")
                        
                        # If we've hit the threshold, perform emergency reset
                        if consecutive_validation_failures >= max_consecutive_failures:
                            self.logger.error("Too many consecutive validation failures, forcing complete reset")
                            self._emergency_reset_conversation(last_user_query)
                            consecutive_validation_failures = 0  # Reset counter after emergency reset
                        else:
                            # Use the emergency reset that will preserve the query
                            self._emergency_reset_conversation(last_user_query)
                else:
                    # Reset consecutive failures counter on successful validation
                    consecutive_validation_failures = 0
                
                # Debug the conversation history structure
                self._debug_conversation_history()
                
                # For function calls, we need to use non-streaming API calls
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=self.conversation_history,
                        tools=[{"type": "function", "function": spec} for spec in self.function_specs],
                        temperature=self.temperature  # Use instance temperature setting
                    )
                except Exception as api_error:
                    # Handle API error related to conversation format
                    error_str = str(api_error)
                    if "invalid_request_error" in error_str and (
                        "tool" in error_str.lower() or 
                        "messages" in error_str.lower() or 
                        "preceeding" in error_str.lower()
                    ):
                        self.logger.error(f"OpenAI API error related to message format: {error_str}")
                        
                        # Perform emergency reset that will preserve the query
                        self._emergency_reset_conversation(last_user_query)
                        
                        # Try one more time with the clean slate
                        response = self.client.chat.completions.create(
                            model="gpt-4o",
                            messages=self.conversation_history,
                            tools=[{"type": "function", "function": spec} for spec in self.function_specs],
                            temperature=self.temperature
                        )
                    else:
                        # Re-raise other API errors
                        raise
                
                # Get the message
                message = response.choices[0].message
                
                # Store the message in conversation history before processing tool calls
                if message.content is not None:
                    # Non-tool message - add directly to conversation history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": message.content
                    })
                elif message.tool_calls:
                    # Check if we've already processed any of these tool calls
                    new_tool_calls = []
                    for tc in message.tool_calls:
                        if tc.id not in self.processed_tool_call_ids:
                            new_tool_calls.append(tc)
                            # Mark as processed
                            self.processed_tool_call_ids.add(tc.id)
                        else:
                            self.logger.warning(f"Skipping duplicate tool call: {tc.id}")
                    
                    # Only add if there are new tool calls
                    if new_tool_calls:
                        # Add the assistant's message with tool_calls to conversation history
                        self.logger.info(f"Adding assistant message with {len(new_tool_calls)} tool_calls")
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in new_tool_calls
                            ]
                        })
                    else:
                        self.logger.warning("All tool calls were already processed, skipping")
                        
                        # If we've processed all tool calls, add a final response
                        self.conversation_history.append({
                            "role": "system",
                            "content": "Previous tool calls were already processed. Please generate a final response with the data already collected."
                        })
                        continue
                
                # Check if the message contains a function call
                if message.tool_calls:
                    # Check if we've exceeded the maximum tool calls
                    if tool_call_count >= max_tool_calls:
                        # Add a system message explaining we're stopping tool calls
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"Maximum tool calls ({max_tool_calls}) reached for this response. Please generate a final response with the data already collected without making additional tool calls."
                        })
                        
                        # Yield a message to the user
                        yield f"Processing data... (hit maximum of {max_tool_calls} data retrievals)"
                        
                        # Get a final response
                        continue
                        
                    # Process each function call
                    for tool_call in message.tool_calls:
                        # Extract function call details
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Log function call
                        self.logger.info(f"Function call: {function_name}({function_args})")
                        
                        # CRITICAL FIX: Check for visualization calls that should be intercepted
                        # This fixes the loop issue when a visualization is requested
                        if function_name == "create_visualization":
                            self.logger.warning("========== VISUALIZATION INTERCEPTION ACTIVATED ==========")
                            self.logger.warning(f"Converting {function_name} to create_direct_chart")
                            
                            title = function_args.get("title", "Task Distribution")
                            viz_type = function_args.get("visualization_type", "")
                            
                            if viz_type == "resource_allocation" and "assignees" in function_args:
                                # Handle resource allocation visualization directly
                                assignees = function_args.get("assignees", [])
                                
                                # Create direct chart
                                self.create_direct_chart(
                                    chart_type="bar",
                                    title=title,
                                    assignees=assignees,
                                    visualization_type="resource_allocation"
                                )
                                
                                # Signal success but force end the conversation loop
                                function_response = {
                                    "status": "success",
                                    "message": "Resource allocation chart created successfully.",
                                    "visualization_type": "resource_allocation"
                                }
                                
                                # Set flag to force-end after this iteration
                                force_end_after_iteration = True
                                
                            elif viz_type == "task_status" and "statuses" in function_args:
                                # Handle task status visualization directly
                                statuses = function_args.get("statuses", {})
                                names = list(statuses.keys())
                                values = list(statuses.values())
                                
                                # Create direct chart
                                self.create_direct_chart(
                                    chart_type="pie",
                                    title=title,
                                    names=names,
                                    values=values,
                                    visualization_type="task_status"
                                )
                                
                                # Signal success but force end the conversation loop
                                function_response = {
                                    "status": "success",
                                    "message": "Task status chart created successfully.",
                                    "visualization_type": "task_status"
                                }
                                
                                # Set flag to force-end after this iteration
                                force_end_after_iteration = True
                                
                            else:
                                # For other visualization types, return error
                                function_response = {
                                    "status": "error",
                                    "message": f"Visualization type '{viz_type}' is not supported. Please use create_direct_chart instead."
                                }
                        elif function_name == "create_chart":
                            # Similar handling for create_chart
                            self.logger.warning("========== CHART INTERCEPTION ACTIVATED ==========")
                            self.logger.warning(f"Converting {function_name} to create_direct_chart")
                            
                            # Extract chart parameters
                            chart_type = function_args.get("chart_type", "bar")
                            title = function_args.get("title", "Chart")
                            x_data = function_args.get("x_data", [])
                            y_data = function_args.get("y_data", [])
                            names = function_args.get("names", [])
                            values = function_args.get("values", [])
                            
                            # Create direct chart
                            self.create_direct_chart(
                                chart_type=chart_type,
                                title=title,
                                x_data=x_data,
                                y_data=y_data,
                                names=names,
                                values=values
                            )
                            
                            # Signal success but force end the conversation loop
                            function_response = {
                                "status": "success",
                                "message": f"{chart_type} chart created successfully."
                            }
                            
                            # Set flag to force-end after this iteration
                            force_end_after_iteration = True
                        else:
                            # Normal function call handling
                            # Call the function
                            function_response = None
                            if function_name in self.available_functions:
                                try:
                                    function_response = self.available_functions[function_name](**function_args)
                                except Exception as func_error:
                                    # Handle function call errors gracefully
                                    self.logger.error(f"Error calling function {function_name}: {func_error}")
                                    function_response = {
                                        "status": "error",
                                        "error": str(func_error),
                                        "message": f"The function {function_name} encountered an error"
                                    }
                            else:
                                # Handle unknown function
                                self.logger.warning(f"Unknown function: {function_name}")
                                function_response = {"error": f"Unknown function: {function_name}"}
                        
                        # CRITICAL: Ensure we have a valid tool_call_id
                        if not hasattr(tool_call, 'id') or not tool_call.id:
                            self.logger.error(f"Missing tool_call_id for function {function_name}, cannot add response")
                            continue
                        
                        # CRITICAL: Ensure the response is serializable JSON
                        if function_response is None:
                            function_response = {"status": "error", "message": "Function returned None"}
                            
                        # Make sure function_response is properly JSON serialized
                        if not isinstance(function_response, str):
                            try:
                                function_response = json.dumps(function_response)
                            except Exception as json_error:
                                self.logger.error(f"Error serializing function response: {json_error}")
                                function_response = json.dumps({"status": "error", "message": "Error serializing result"})
                        
                        # Add function response to conversation history
                        self.logger.info(f"Adding tool response for tool_call_id={tool_call.id}")
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": function_response
                        })
                    
                    # If we need to force end after this iteration, add a system message and break the loop
                    if force_end_after_iteration:
                        self.logger.info("Forcing end of conversation due to visualization interception")
                        
                        # Add system message to get final response
                        self.conversation_history.append({
                            "role": "system",
                            "content": "IMPORTANT: The visualization has been created successfully. Please generate a final text response that summarizes the key insights from the data and references the visualization. DO NOT try to create another visualization."
                        })
                        
                        # Get final response
                        final_response = self.client.chat.completions.create(
                            model="gpt-4o",
                            messages=self.conversation_history,
                            temperature=self.temperature
                        )
                        
                        # Extract text content
                        final_content = final_response.choices[0].message.content or "I've analyzed your data and can provide insights."
                        final_content = self._format_for_streamlit(final_content)
                        
                        # Add to conversation history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": final_content
                        })
                        
                        # Stream response
                        current_chunk = ""
                        chunks = self._create_streaming_chunks(final_content)
                        
                        for chunk in chunks:
                            current_chunk += chunk
                            yield current_chunk
                        
                        # Signal visualization availability
                        yield current_chunk + "\n\n[visualization_available]"
                        
                        # Exit the function
                        return
            
            # If we've reached max_api_calls, return a message indicating this
            return "I've made several API calls but wasn't able to fully process your request. Please try asking in a different way."
            
        except Exception as e:
            self.logger.error(f"Error processing query with function calling: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    
    def generate_streaming_response(self, query: str) -> Generator[str, None, None]:
        """
        Generate a streaming response for a user query.
        
        Args:
            query: User's query text
            
        Returns:
            Generator yielding response chunks
        """
        if not self.client:
            # Check if OpenAI API key is in session state
            if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
                self.setup_llm(st.session_state.openai_api_key)
            else:
                yield "Error: OpenAI API key not found. Please provide your OpenAI API key in the sidebar."
                return
        
        # Update tools with latest portfolio_gid and team_gid from session state
        self.tools.portfolio_gid = st.session_state.get("portfolio_gid", "")
        self.tools.team_gid = st.session_state.get("team_gid", "")
        
        # Validate portfolio_gid
        if not self.tools.portfolio_gid or self.tools.portfolio_gid == "your_portfolio_gid_here":
            # Create a properly formatted error message
            formatted_error = """
## Configuration Required

I'm unable to access your Asana projects because a valid portfolio hasn't been selected.

### What you need to do:

1. Go to the sidebar configuration settings
2. Select your Asana workspace
3. Select a portfolio from the dropdown menu
4. Click "Save Configuration"

Once configured, I'll be able to provide insights about your projects, tasks, and team workload.
"""
            yield formatted_error
            return
        
        # Add user message to conversation history
        self.add_message_to_history("user", query)
        
        # Reset visualization memory
        if "visualization" in self.memory:
            del self.memory["visualization"]
        if "direct_chart" in self.memory:
            del self.memory["direct_chart"]
        
        # Add a critical reminder about using direct_chart
        self.conversation_history.append({
            "role": "system",
            "content": "IMPORTANT: When creating visualizations, use ONLY create_direct_chart function. Do NOT use create_visualization or create_chart functions as they are deprecated."
        })
        
        # Sanitize conversation history before starting
        self._sanitize_conversation_history()
        
        # Process function calls and generate streaming response
        try:
            # Initialize force_end_after_iteration flag at the beginning to avoid reference errors
            force_end_after_iteration = False
            
            # Maximum number of API calls to prevent infinite loops
            max_api_calls = 10
            api_call_count = 0
            
            # Track tool calls in this response to prevent infinite loops
            tool_call_count = 0
            max_tool_calls = 5  # Maximum tool calls per response
            
            # Track consecutive validation failures to detect persistent problems
            consecutive_validation_failures = 0
            max_consecutive_failures = 3  # After this many consecutive failures, force emergency reset
            
            # Continue until we get a non-function-call response or reach max calls
            while api_call_count < max_api_calls:
                api_call_count += 1
                
                # Check if conversation history is valid before API call
                if not self._validate_conversation_history():
                    self.logger.warning("Invalid conversation history detected, attempting to sanitize")
                    self._sanitize_conversation_history()
                    
                    # Check again after sanitizing
                    if not self._validate_conversation_history():
                        self.logger.error("Conversation history still invalid after sanitizing, performing emergency reset")
                        # Increment consecutive failures counter
                        consecutive_validation_failures += 1
                        self.logger.warning(f"Consecutive validation failures: {consecutive_validation_failures}/{max_consecutive_failures}")
                        
                        # If we've hit the threshold, perform emergency reset
                        if consecutive_validation_failures >= max_consecutive_failures:
                            self.logger.error("Too many consecutive validation failures, forcing complete reset")
                            self._emergency_reset_conversation(query)
                            consecutive_validation_failures = 0  # Reset counter after emergency reset
                            
                            # Force a final response
                            final_response = self._force_final_response()
                            
                            # Stream the response
                            current_chunk = ""
                            chunks = self._create_streaming_chunks(final_response)
                            
                            for chunk in chunks:
                                current_chunk += chunk
                                yield current_chunk
                            
                            # Exit the function
                            return
                        else:
                            # Use the emergency reset with the current query
                            self._emergency_reset_conversation(query)
                else:
                    # Reset consecutive failures counter on successful validation
                    consecutive_validation_failures = 0
                
                # Debug the conversation history structure
                self._debug_conversation_history()
                
                # For function calls, we need to use non-streaming API calls
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=self.conversation_history,
                        tools=[{"type": "function", "function": spec} for spec in self.function_specs],
                        temperature=self.temperature  # Use instance temperature setting
                    )
                    
                    # Get the message
                    message = response.choices[0].message
                except Exception as e:
                    # Handle API errors gracefully
                    self.logger.error(f"Error in API call: {e}")
                    
                    # Check for specific error related to tool messages
                    error_str = str(e)
                    if "invalid_request_error" in error_str and (
                        "tool" in error_str.lower() or 
                        "messages" in error_str.lower() or 
                        "preceeding" in error_str.lower()
                    ):
                        # This is likely due to malformed conversation history with tool messages
                        self.logger.warning("Detected issue with tool messages in conversation history. Completely resetting and trying again.")
                        
                        # Perform emergency reset
                        self._emergency_reset_conversation(query)
                
                # Store the message in conversation history before processing tool calls
                if message.content is not None:
                    # Non-tool message - add directly to conversation history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": message.content
                    })
                elif message.tool_calls:
                    # Check if we've already processed any of these tool calls
                    new_tool_calls = []
                    for tc in message.tool_calls:
                        if tc.id not in self.processed_tool_call_ids:
                            new_tool_calls.append(tc)
                            # Mark as processed
                            self.processed_tool_call_ids.add(tc.id)
                        else:
                            self.logger.warning(f"Skipping duplicate tool call: {tc.id}")
                    
                    # Only add if there are new tool calls
                    if new_tool_calls:
                        # Add the assistant's message with tool_calls to conversation history
                        self.logger.info(f"Adding assistant message with {len(new_tool_calls)} tool_calls")
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in new_tool_calls
                            ]
                        })
                    else:
                        self.logger.warning("All tool calls were already processed, skipping")
                        
                        # If we've processed all tool calls, add a final response
                        self.conversation_history.append({
                            "role": "system",
                            "content": "Previous tool calls were already processed. Please generate a final response with the data already collected."
                        })
                        continue
                
                # Check if the message contains a function call
                if message.tool_calls:
                    # Check if we've exceeded the maximum tool calls
                    if tool_call_count >= max_tool_calls:
                        # Add a system message explaining we're stopping tool calls
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"Maximum tool calls ({max_tool_calls}) reached for this response. Please generate a final response with the data already collected without making additional tool calls."
                        })
                        
                        # Yield a message to the user
                        yield f"Processing data... (hit maximum of {max_tool_calls} data retrievals)"
                        
                        # Get a final response
                        continue
                    
                    # Critical fix: Check for attempted visualization or chart calls that will cause loops
                    has_bad_visualization_call = False
                    visualization_data = None
                    visualization_title = "Data Visualization"
                    visualization_type = None
                    
                    for tool_call in message.tool_calls:
                        if tool_call.function.name == "create_visualization":
                            has_bad_visualization_call = True
                            # Try to extract data for direct chart
                            function_args = json.loads(tool_call.function.arguments)
                            visualization_title = function_args.get("title", "Data Visualization")
                            visualization_type = function_args.get("visualization_type")
                            
                            # Get the visualization data
                            if "data" in function_args:
                                visualization_data = function_args.get("data", {})
                            else:
                                # Data might be directly in the function args
                                visualization_data = function_args
                            break
                            
                        elif tool_call.function.name == "create_chart":
                            has_bad_visualization_call = True
                            # Extract chart data
                            function_args = json.loads(tool_call.function.arguments)
                            visualization_title = function_args.get("title", "Chart")
                            visualization_data = function_args
                            break
                    
                    if has_bad_visualization_call:
                        # Try to create a direct chart from the extracted data
                        chart_created = False
                        
                        if visualization_data and visualization_type:
                            # Try to create a direct chart
                            if visualization_type == "resource_allocation":
                                chart_created = self._create_direct_chart_from_data("resource_allocation", visualization_data, visualization_title)
                            elif visualization_type == "task_status":
                                chart_created = self._create_direct_chart_from_data("task_status", visualization_data, visualization_title)
                        
                        # Add a system message to prevent the loop and force a final response
                        self.logger.warning("========== VISUALIZATION CALL INTERCEPTED ==========")
                        
                        # Add the interception message to history - different message if chart was created
                        if chart_created:
                            self.conversation_history.append({
                                "role": "system",
                                "content": f"A visualization of type '{visualization_type}' has been created with title '{visualization_title}'. Please generate a final response that includes analysis of the data."
                            })
                            
                            # Force a final response
                            final_response = self.client.chat.completions.create(
                                model="gpt-4o",
                                messages=self.conversation_history,
                                temperature=self.temperature,
                                max_tokens=500
                            )
                            
                            final_content = final_response.choices[0].message.content
                            final_content = self._format_for_streamlit(final_content)
                            
                            # Add to history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": final_content
                            })
                            
                            # Stream response
                            current_chunk = ""
                            chunks = self._create_streaming_chunks(final_content)
                            
                            for chunk in chunks:
                                current_chunk += chunk
                                yield current_chunk
                            
                            # Signal visualization
                            yield current_chunk + "\n\n[visualization_available]"
                            return
                        else:
                            # No chart created, just add warning
                            self.conversation_history.append({
                                "role": "system",
                                "content": "DO NOT USE create_visualization or create_chart functions - they will cause errors. Use create_direct_chart instead. If you have visualization data, please provide a response that doesn't use visualization tools."
                            })
                            
                            # Skip this response and force a retry
                            continue
                    
                    # Process each function call silently (no streaming)
                    yield "Thinking..."  # Signal to the user that processing is happening
                    
                    # Initialize force_end_after_iteration flag
                    force_end_after_iteration = False
                    
                    # Process each function call
                    for tool_call in message.tool_calls:
                        # Extract function call details
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Log function call
                        self.logger.info(f"Function call: {function_name}({function_args})")
                        
                        # CRITICAL FIX: Check for visualization calls that should be intercepted
                        # This fixes the loop issue when a visualization is requested
                        if function_name == "create_visualization":
                            self.logger.warning("========== VISUALIZATION INTERCEPTION ACTIVATED ==========")
                            self.logger.warning(f"Converting {function_name} to create_direct_chart")
                            
                            title = function_args.get("title", "Task Distribution")
                            viz_type = function_args.get("visualization_type", "")
                            
                            if viz_type == "resource_allocation" and "assignees" in function_args:
                                # Handle resource allocation visualization directly
                                assignees = function_args.get("assignees", [])
                                
                                # Create direct chart
                                self.create_direct_chart(
                                    chart_type="bar",
                                    title=title,
                                    assignees=assignees,
                                    visualization_type="resource_allocation"
                                )
                                
                                # Signal success but force end the conversation loop
                                function_response = {
                                    "status": "success",
                                    "message": "Resource allocation chart created successfully.",
                                    "visualization_type": "resource_allocation"
                                }
                                
                                # Set flag to force-end after this iteration
                                force_end_after_iteration = True
                                
                            elif viz_type == "task_status" and "statuses" in function_args:
                                # Handle task status visualization directly
                                statuses = function_args.get("statuses", {})
                                names = list(statuses.keys())
                                values = list(statuses.values())
                                
                                # Create direct chart
                                self.create_direct_chart(
                                    chart_type="pie",
                                    title=title,
                                    names=names,
                                    values=values,
                                    visualization_type="task_status"
                                )
                                
                                # Signal success but force end the conversation loop
                                function_response = {
                                    "status": "success",
                                    "message": "Task status chart created successfully.",
                                    "visualization_type": "task_status"
                                }
                                
                                # Set flag to force-end after this iteration
                                force_end_after_iteration = True
                                
                            else:
                                # For other visualization types, return error
                                function_response = {
                                    "status": "error",
                                    "message": f"Visualization type '{viz_type}' is not supported. Please use create_direct_chart instead."
                                }
                        elif function_name == "create_chart":
                            # Similar handling for create_chart
                            self.logger.warning("========== CHART INTERCEPTION ACTIVATED ==========")
                            self.logger.warning(f"Converting {function_name} to create_direct_chart")
                            
                            # Extract chart parameters
                            chart_type = function_args.get("chart_type", "bar")
                            title = function_args.get("title", "Chart")
                            x_data = function_args.get("x_data", [])
                            y_data = function_args.get("y_data", [])
                            names = function_args.get("names", [])
                            values = function_args.get("values", [])
                            
                            # Create direct chart
                            self.create_direct_chart(
                                chart_type=chart_type,
                                title=title,
                                x_data=x_data,
                                y_data=y_data,
                                names=names,
                                values=values
                            )
                            
                            # Signal success but force end the conversation loop
                            function_response = {
                                "status": "success",
                                "message": f"{chart_type} chart created successfully."
                            }
                            
                            # Set flag to force-end after this iteration
                            force_end_after_iteration = True
                        else:
                            # Normal function call handling
                            # Call the function
                            function_response = None
                            if function_name in self.available_functions:
                                try:
                                    function_response = self.available_functions[function_name](**function_args)
                                except Exception as func_error:
                                    # Handle function call errors gracefully
                                    self.logger.error(f"Error calling function {function_name}: {func_error}")
                                    function_response = {
                                        "status": "error",
                                        "error": str(func_error),
                                        "message": f"The function {function_name} encountered an error"
                                    }
                            else:
                                # Handle unknown function
                                self.logger.warning(f"Unknown function: {function_name}")
                                function_response = {"error": f"Unknown function: {function_name}"}
                        
                        # CRITICAL: Ensure we have a valid tool_call_id
                        if not hasattr(tool_call, 'id') or not tool_call.id:
                            self.logger.error(f"Missing tool_call_id for function {function_name}, cannot add response")
                            continue
                        
                        # CRITICAL: Ensure the response is serializable JSON
                        if function_response is None:
                            function_response = {"status": "error", "message": "Function returned None"}
                            
                        # Make sure function_response is properly JSON serialized
                        if not isinstance(function_response, str):
                            try:
                                function_response = json.dumps(function_response)
                            except Exception as json_error:
                                self.logger.error(f"Error serializing function response: {json_error}")
                                function_response = json.dumps({"status": "error", "message": "Error serializing result"})
                        
                        # Add function response to conversation history
                        self.logger.info(f"Adding tool response for tool_call_id={tool_call.id}")
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": function_response
                        })
                    
                    # If we need to force end after this iteration, add a system message and break the loop
                    if force_end_after_iteration:
                        self.logger.info("Forcing end of conversation due to visualization interception")
                        
                        # Add system message to get final response
                        self.conversation_history.append({
                            "role": "system",
                            "content": "IMPORTANT: The visualization has been created successfully. Please generate a final text response that summarizes the key insights from the data and references the visualization. DO NOT try to create another visualization."
                        })
                        
                        # Get final response
                        try:
                            final_response = self.client.chat.completions.create(
                                model="gpt-4o",
                                messages=self.conversation_history,
                                temperature=self.temperature
                            )
                            
                            # Extract text content
                            final_content = final_response.choices[0].message.content or "I've created a visualization with your data."
                            
                            # Format the content
                            final_content = self._format_for_streamlit(final_content)
                            
                            # Add to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": final_content
                            })
                        except Exception as e:
                            self.logger.error(f"Error getting final response after visualization: {e}")
                            final_content = "I've created a visualization based on the data to help illustrate the key information."
                            
                            # Add a simplified response to avoid API errors
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": final_content
                            })
                        
                        # Stream the response
                        current_chunk = ""
                        chunks = self._create_streaming_chunks(final_content)
                        
                        for chunk in chunks:
                            current_chunk += chunk
                            yield current_chunk
                        
                        # Signal visualization availability
                        yield current_chunk + "\n\n[visualization_available]"
                        
                        # Exit the function
                        return
                else:
                    # No function call, process the response text
                    content = message.content or "I'm sorry, I couldn't generate a response."
                    
                    # Check if the response is asking for a GID and fix it
                    if self._is_asking_for_gid(content):
                        # Add a special message to redirect the assistant
                        self.conversation_history.append({
                            "role": "system",
                            "content": "IMPORTANT: You should not ask the user for GIDs. The portfolio_gid and team_gid are already available through the session state. Please retrieve the information directly using the tools available to you without asking the user for any GIDs. Automatically use get_portfolio_projects() to get all projects in the portfolio."
                        })
                        
                        # Yield a temporary message
                        yield "Analyzing your portfolio data..."
                        
                        # Automatically insert a function call to get_portfolio_projects
                        self.logger.info("Automatically inserting get_portfolio_projects call")
                        
                        # Create a tool_call for get_portfolio_projects
                        tool_call_id = f"auto_call_{int(time.time())}"
                        
                        # Add the function call to the conversation
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": "get_portfolio_projects",
                                        "arguments": "{}"
                                    }
                                }
                            ]
                        })
                        
                        # Call the function
                        try:
                            function_response = self.available_functions["get_portfolio_projects"]()
                            
                            # Add function response to conversation history
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(function_response)
                            })
                        except Exception as func_error:
                            self.logger.error(f"Error calling get_portfolio_projects: {func_error}")
                            # Add a simplified response to avoid breaking the conversation
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps({"status": "error", "error": str(func_error)})
                            })
                        
                        # Continue to next iteration to get a better response
                        continue
                    
                    # No function call, stream the message content
                    content = self._fix_gid_requests(content)
                    
                    # Format content for optimal display
                    content = self._format_for_streamlit(content)
                    
                    # Add the message to the conversation history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": content
                    })
                    
                    # Implement better streaming that respects markdown formatting
                    current_chunk = ""
                    chunks = self._create_streaming_chunks(content)
                    
                    # Stream each chunk
                    for chunk in chunks:
                        current_chunk += chunk
                        yield current_chunk
                    
                    # Signal visualization availability if needed
                    if "visualization" in self.memory or "direct_chart" in self.memory:
                        yield current_chunk + "\n\n[visualization_available]"
                        
                    return
            
            # If we've reached max_api_calls, return a message indicating this
            yield "I've made several API calls but wasn't able to fully process your request. Please try asking in a different way."
            
        except Exception as e:
            self.logger.error(f"Error generating streaming response: {e}")
            yield f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    
    def _create_streaming_chunks(self, content: str) -> List[str]:
        """
        Create logical streaming chunks that respect markdown structure.
        
        Args:
            content: The content to split into streaming chunks
            
        Returns:
            List of content chunks for streaming
        """
        # For weekly status reports, use a different chunking strategy to avoid duplications
        if "weekly status report" in content.lower() or "status report" in content.lower():
            # Process weekly reports by returning incremental chunks that don't include prior content
            lines = content.split("\n")
            result = []
            current_chunk = ""
            
            for i, line in enumerate(lines):
                # Add the line to current chunk
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
                
                # Determine if we should end this chunk
                if (i + 1 < len(lines) and lines[i+1].startswith("#")) or i == len(lines) - 1:
                    # End of a section or end of content
                    result.append(current_chunk)
                    # Start fresh with next chunk to avoid duplication
                    current_chunk = ""
                
            # Add final chunk if not empty
            if current_chunk:
                result.append(current_chunk)
                
            # Return the non-cumulative chunks
            return result
                
        # Standard chunking for non-report content
        chunks = []
        buffer = ""
        lines = content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if current line starts a structural element
            is_header = line.strip().startswith("#")
            is_list_item = line.strip().startswith("-") or line.strip().startswith("*")
            is_table_row = line.strip().startswith("|") and "|" in line.strip()[1:]
            is_code_block = line.strip().startswith("```")
            is_horizontal_rule = line.strip() == "---"
            
            # If we're at a structural element and buffer is not empty,
            # flush the buffer as a chunk
            if (is_header or is_list_item or is_table_row or is_code_block or is_horizontal_rule) and buffer:
                chunks.append(buffer)
                buffer = ""
            
            # Handle different types of elements
            if is_header:
                # Headers get their own chunk
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.append(line + "\n")
            elif is_table_row:
                # Collect entire table as one chunk
                table_chunk = line + "\n"
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith("|"):
                    table_chunk += lines[j] + "\n"
                    j += 1
                i = j - 1  # Adjust loop counter
                chunks.append(table_chunk)
            elif is_code_block:
                # Collect entire code block as one chunk
                code_chunk = line + "\n"
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    code_chunk += lines[j] + "\n"
                    j += 1
                if j < len(lines):  # Add closing ```
                    code_chunk += lines[j] + "\n"
                    j += 1
                i = j - 1  # Adjust loop counter
                chunks.append(code_chunk)
            elif is_list_item:
                # Try to keep list items grouped but still stream them
                list_chunk = line + "\n"
                j = i + 1
                # Collect up to 3 list items or until list ends
                count = 1
                while j < len(lines) and count < 3 and (lines[j].strip().startswith("-") or lines[j].strip().startswith("*")):
                    list_chunk += lines[j] + "\n"
                    if lines[j].strip().startswith("-") or lines[j].strip().startswith("*"):
                        count += 1
                    j += 1
                i = j - 1  # Adjust loop counter
                chunks.append(list_chunk)
            else:
                # Regular text - accumulate paragraph chunks
                buffer += line + "\n"
                
                # Check if paragraph is complete (empty line follows)
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    buffer += "\n"  # Add the empty line
                    chunks.append(buffer)
                    buffer = ""
                    i += 1  # Skip the empty line
            
            i += 1
        
        # Add any remaining text
        if buffer:
            chunks.append(buffer)
        
        # For very short content, don't split into chunks
        if len(chunks) == 0:
            chunks = [content]
        elif len(chunks) == 1 and len(content) < 100:
            # For short content, create word-by-word chunks for a typing effect
            words = content.split()
            chunks = []
            current = ""
            for word in words:
                current += word + " "
                # Add a new chunk every 2-3 words for a natural typing effect
                if len(current.split()) % 3 == 0:
                    chunks.append(current)
        
        return chunks
    
    def _format_for_streamlit(self, content: str) -> str:
        """
        Format content for optimal display in Streamlit's markdown.
        
        Args:
            content: The content to format
            
        Returns:
            Formatted content
        """
        # Don't process empty content
        if not content:
            return content
            
        try:
            # Ensure headers have proper spacing
            for i in range(6, 0, -1):  # Start with h6 to avoid modifying already modified headers
                header = "#" * i + " "
                if f"\n{header}" in content:
                    content = content.replace(f"\n{header}", f"\n\n{header}")
                
            # Ensure list items have proper spacing
            if "\n- " in content:
                content = content.replace("\n- ", "\n\n- ")
                
            # Ensure proper spacing for tables
            if "|" in content and "\n|" in content:
                # Add blank lines before and after tables
                content = content.replace("\n|", "\n\n|")
                
                # Add blank line after table if not already present
                # Find last line of table
                lines = content.split("\n")
                for i in range(len(lines)-1, 0, -1):
                    if lines[i].startswith("|") and not lines[i-1].startswith("|"):
                        # Found last line of a table
                        if i < len(lines)-1 and lines[i+1].strip() != "":
                            # Need to add a blank line after table
                            lines.insert(i+1, "")
                content = "\n".join(lines)
            
            # Ensure horizontal rules have proper spacing
            if "\n---" in content:
                content = content.replace("\n---", "\n\n---\n\n")
                
            # Ensure proper spacing after paragraphs
            content = content.replace(".\n", ".\n\n")
            
            # Ensure proper spacing before bold text at the beginning of lines
            content = content.replace("\n**", "\n\n**")
            
            # Fix spacing around code blocks
            if "```" in content:
                content = content.replace("\n```", "\n\n```")
                content = content.replace("```\n", "```\n\n")
            
            # Fix any triple or more newlines (normalize spacing)
            while "\n\n\n" in content:
                content = content.replace("\n\n\n", "\n\n")
                
            return content
        except Exception as e:
            self.logger.error(f"Error formatting content for Streamlit: {e}")
            return content  # Return original content if formatting fails
    
    def _create_direct_chart_from_data(self, data_type: str, data: Dict[str, Any], title: str) -> bool:
        """
        Helper method to create direct charts from task distribution or resource allocation data.
        This handles the most common chart types that cause issues.
        
        Args:
            data_type: Type of data ('task_distribution' or 'resource_allocation')
            data: Data to visualize
            title: Chart title
            
        Returns:
            True if chart was created successfully, False otherwise
        """
        try:
            self.logger.info(f"Creating direct chart from {data_type} data")
            
            if data_type == "resource_allocation" and "assignees" in data:
                # Create a horizontal bar chart for resource allocation
                assignees = data.get("assignees", [])
                self.create_direct_chart(
                    chart_type="bar",
                    title=title,
                    assignees=assignees,
                    visualization_type="resource_allocation"
                )
                return True
                
            elif data_type == "task_status" and "statuses" in data:
                # Create a pie chart for task status distribution
                statuses = data.get("statuses", {})
                names = list(statuses.keys())
                values = list(statuses.values())
                self.create_direct_chart(
                    chart_type="pie",
                    title=title,
                    names=names,
                    values=values,
                    visualization_type="task_status"
                )
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error creating direct chart from data: {e}")
            return False

    def reset_and_initialize_conversation(self) -> None:
        """
        Completely reset the conversation and initialize with system prompts.
        This ensures a clean state that's guaranteed to be valid for the OpenAI API.
        """
        # First, completely clear the conversation history and memory
        self.conversation_history = []
        self.memory = {}
        
        # Get the current portfolio_gid and team_gid
        portfolio_gid = st.session_state.get("portfolio_gid", "")
        team_gid = st.session_state.get("team_gid", "")
        
        # Add initial critical system message about GIDs
        initial_system_message = """
        CRITICAL INSTRUCTION: You are an Asana project management assistant that MUST NEVER ask users for GIDs or IDs of any kind.
        
        The correct portfolio_gid=""" + portfolio_gid + """ is ALREADY loaded in the system. Always use this GID automatically without mentioning it.
        
        When users ask about portfolio data, projects, or trends, IMMEDIATELY call get_portfolio_projects() with NO arguments.
        The function will automatically use the correct GID from the session state.
        
        For ANY query related to portfolio, workload, or trends, ALWAYS call these functions WITHOUT asking for IDs:
        1. get_portfolio_projects() - To get all projects
        2. get_task_distribution_by_assignee() - To analyze workload
        3. get_task_completion_trend() - To analyze trends
        
        NEVER mention, reference, or ask for GIDs in your responses.
        """
        
        # Add the critical system message as the first message
        self.conversation_history.append({"role": "system", "content": initial_system_message})
        
        # Add detailed system message with instructions
        system_message = """
        You are an AI assistant for Asana project management. You can access information about Asana projects, tasks, timelines, and resource allocation.
        
        IMPORTANT CONFIGURATION:
        - Portfolio GID: """ + portfolio_gid + """
        - Team GID: """ + team_gid + """
        
        GID HANDLING (CRITICAL):
        - NEVER ask the user for any GIDs or IDs. This is the single most important rule.
        - NEVER use placeholder values like 'your_portfolio_gid_here'.
        - The portfolio_gid (""" + portfolio_gid + """) is ALREADY configured in the system.
        - The team_gid (""" + team_gid + """) is ALREADY configured in the system.
        - ALWAYS use these pre-configured GIDs in your function calls automatically without mentioning them to the user.
        - If a GID is missing or invalid, inform the user they need to configure their portfolio in the app settings.
        - NEVER mention GIDs in your responses unless reporting an error about configuration.
        - NEVER, under any circumstances, ask the user to "provide a GID" or any variation of this request.
        - Instead of asking for GIDs, directly use the tools available with the GIDs that are already configured.
        
        VISUALIZATION BEST PRACTICES:
        - When creating visualizations, ALWAYS use create_direct_chart function, NEVER use deprecated functions.
        - Always include a descriptive title for any visualization you create.
        - For resource allocation charts, identify team members with highest/lowest workloads.
        - For status distributions, highlight the largest categories and what they indicate.
        """
        
        # Add the main system message
        self.conversation_history.append({"role": "system", "content": system_message})
        
        # Add initial assistant message (optional)
        self.conversation_history.append({
            "role": "assistant", 
            "content": "Hello! I can help you analyze your Asana projects by directly accessing your data. What would you like to know?"
        })
        
        self.logger.info(f"Conversation fully reset and initialized with fresh system instructions")

    def _validate_conversation_history(self) -> bool:
        """
        Validate the conversation history to ensure it's in a consistent state for the OpenAI API.
        Specifically, checks that any 'tool' role messages have corresponding preceding 'tool_calls'.
        
        Returns:
            bool: True if valid, False if invalid
        """
        # Track tool call IDs that have been seen
        valid_tool_call_ids = set()
        
        # First pass: collect all valid tool call IDs from existing assistant messages
        for i, message in enumerate(self.conversation_history):
            role = message.get("role", "")
            
            # If we find an assistant message with tool_calls, add those IDs to valid set
            if role == "assistant" and "tool_calls" in message:
                for tool_call in message.get("tool_calls", []):
                    if "id" in tool_call:
                        tool_call_id = tool_call["id"]
                        valid_tool_call_ids.add(tool_call_id)
                        self.logger.debug(f"Found valid tool_call_id: {tool_call_id} in message {i}")
        
        self.logger.debug(f"Valid tool_call_ids in conversation: {valid_tool_call_ids}")
        
        # Second pass: check that all tool messages have valid tool_call_ids
        for i, message in enumerate(self.conversation_history):
            role = message.get("role", "")
            
            # If we find a tool message, check that its tool_call_id is in the valid set
            if role == "tool":
                tool_call_id = message.get("tool_call_id")
                if not tool_call_id:
                    self.logger.warning(f"Invalid tool message at position {i}: missing tool_call_id")
                    return False
                
                if tool_call_id not in valid_tool_call_ids:
                    self.logger.warning(f"Invalid tool message at position {i}: tool_call_id={tool_call_id} not found in valid tool calls")
                    return False
                
                # Tool call is valid
                self.logger.debug(f"Valid tool message at position {i} with tool_call_id={tool_call_id}")
        
        return True

    def _sanitize_conversation_history(self) -> None:
        """
        Reconstruct the conversation history to ensure it's valid for the OpenAI API.
        Specifically ensures that tool messages are always paired with preceding assistant messages with matching tool_calls.
        
        This implementation completely rebuilds the conversation to ensure proper sequencing.
        """
        # If conversation is empty, nothing to do
        if not self.conversation_history:
            return
            
        # Create a new sanitized conversation history
        sanitized_history = []
        
        # Track valid tool call IDs and their associated assistant messages
        valid_tool_calls = {}  # Maps tool_call_id to the index of its assistant message
        assistant_indices = {}  # Maps assistant message index to its position in sanitized_history
        
        # First pass: add all non-tool messages and track tool_calls
        for message in self.conversation_history:
            role = message.get("role", "")
            
            if role != "tool":
                # Add non-tool message to sanitized history
                sanitized_history.append(message)
                
                # If it's an assistant message with tool_calls, track them
                if role == "assistant" and "tool_calls" in message:
                    # Remember the position of this assistant message
                    assistant_idx = len(sanitized_history) - 1
                    assistant_indices[assistant_idx] = assistant_idx
                    
                    # Track each tool call ID
                    for tool_call in message.get("tool_calls", []):
                        if "id" in tool_call:
                            valid_tool_calls[tool_call["id"]] = assistant_idx
        
        # Now we need to re-insert the tool messages in the right places,
        # after their corresponding assistant messages
        
        # Collect tool messages by tool_call_id
        tool_messages = {}
        for message in self.conversation_history:
            if message.get("role") == "tool" and "tool_call_id" in message:
                tool_call_id = message.get("tool_call_id")
                if tool_call_id in valid_tool_calls:
                    tool_messages[tool_call_id] = message
        
        # Build the final history by placing tool messages after their assistant messages
        final_history = []
        for i, message in enumerate(sanitized_history):
            final_history.append(message)
            
            # If this is an assistant message with tool_calls, add its tool responses
            if message.get("role") == "assistant" and "tool_calls" in message:
                # Find all tool_calls in this message
                for tool_call in message.get("tool_calls", []):
                    if "id" in tool_call:
                        tool_call_id = tool_call["id"]
                        # If we have a tool response for this ID, add it
                        if tool_call_id in tool_messages:
                            final_history.append(tool_messages[tool_call_id])
                            # Remove from tool_messages to avoid duplicates
                            del tool_messages[tool_call_id]
        
        # Count changes
        original_count = len(self.conversation_history)
        new_count = len(final_history)
        
        # Update conversation history
        self.conversation_history = final_history
        
        # Log changes
        if original_count != new_count:
            self.logger.warning(f"Conversation history sanitized: changed from {original_count} to {new_count} messages")
        
        # Log any tool messages that couldn't be matched (were orphaned)
        if tool_messages:
            self.logger.warning(f"Could not place {len(tool_messages)} tool messages (no matching assistant tool_calls)")
    
    def reset_function_chat(self) -> None:
        """Reset the function chat completely and start fresh"""
        self.reset_and_initialize_conversation()
        return "Chat reset successfully. Hello! I can help you analyze your Asana projects by directly accessing your data. What would you like to know?"

    def _debug_conversation_history(self):
        """
        Print detailed debug information about the conversation history structure.
        This helps diagnose issues with the message sequence.
        """
        self.logger.info("==== CONVERSATION HISTORY DEBUG ====")
        self.logger.info(f"Total messages: {len(self.conversation_history)}")
        
        # Maps tool_call_id to whether it has a response
        tool_calls_map = {}
        
        for i, message in enumerate(self.conversation_history):
            role = message.get("role", "")
            content_preview = str(message.get("content", ""))[:50] + "..." if message.get("content") else "None"
            
            if role == "assistant" and "tool_calls" in message:
                tool_calls = message.get("tool_calls", [])
                tool_call_ids = [tc.get("id") for tc in tool_calls if "id" in tc]
                self.logger.info(f"Message {i}: role='{role}' with {len(tool_calls)} tool_calls: {tool_call_ids}")
                
                # Track tool call IDs
                for tc_id in tool_call_ids:
                    tool_calls_map[tc_id] = False
            elif role == "tool":
                tool_call_id = message.get("tool_call_id")
                self.logger.info(f"Message {i}: role='{role}' tool_call_id='{tool_call_id}' content='{content_preview}'")
                
                # Mark this tool call as having a response
                if tool_call_id in tool_calls_map:
                    tool_calls_map[tool_call_id] = True
            else:
                self.logger.info(f"Message {i}: role='{role}' content='{content_preview}'")
        
        # Check for tool calls without responses
        missing_responses = [tc_id for tc_id, has_response in tool_calls_map.items() if not has_response]
        if missing_responses:
            self.logger.warning(f"Tool calls without responses: {missing_responses}")
        
        # Check for tool responses without tool calls
        for i, message in enumerate(self.conversation_history):
            if message.get("role") == "tool":
                tool_call_id = message.get("tool_call_id")
                if tool_call_id not in tool_calls_map:
                    self.logger.warning(f"Tool response at position {i} has no matching tool call: {tool_call_id}")
        
        self.logger.info("==== END CONVERSATION HISTORY DEBUG ====")

    def _emergency_reset_conversation(self, user_query: str = None):
        """
        Performs an emergency reset of the conversation while preserving the user's query.
        This is more aggressive than _sanitize_conversation_history and should be used when
        there are persistent issues with the conversation history format.
        
        Args:
            user_query: Optional user query to preserve after reset
        """
        self.logger.warning("===== PERFORMING EMERGENCY CONVERSATION RESET =====")
        
        # Save the original conversation length for logging
        original_length = len(self.conversation_history)
        
        # Store any critical system instructions that we want to preserve
        preserved_system_instructions = []
        
        # Scan for important system messages we want to keep
        for msg in self.conversation_history:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                # Keep system messages about critical functionality
                if any(keyword in content.lower() for keyword in ["critical", "important", "never", "always", "visualization"]):
                    preserved_system_instructions.append(content)
        
        # Reset everything
        self.reset_and_initialize_conversation()
        
        # Add back any preserved system instructions
        for instruction in preserved_system_instructions:
            # Don't add duplicates - check if this instruction is similar to existing ones
            is_duplicate = False
            for msg in self.conversation_history:
                if msg.get("role") == "system" and self._is_similar_content(instruction, msg.get("content", "")):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.conversation_history.append({"role": "system", "content": instruction})
        
        # Add back the user query if provided
        if user_query:
            self.add_message_to_history("user", user_query)
            self.logger.info(f"Re-added user query after emergency reset: {user_query}")
        
        # Reset processed tool call IDs
        self.processed_tool_call_ids = set()
        
        # Log the change
        new_length = len(self.conversation_history)
        self.logger.warning(f"Emergency reset complete: conversation history reduced from {original_length} to {new_length} messages")

    def _is_similar_content(self, text1: str, text2: str) -> bool:
        """
        Determines if two text strings are similar enough to be considered duplicates.
        Used to avoid adding duplicate system instructions after resets.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            True if the texts are considered similar, False otherwise
        """
        # Simple implementation - consider similar if they share 70% of words
        # Could be improved with more sophisticated text similarity algorithms
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
            
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity > 0.7  # 70% similarity threshold

    def _force_final_response(self, streaming=False):
        """
        Force the model to generate a final response without further tool calls.
        This is used when we've had issues with the API or tool responses.
        
        Args:
            streaming: If True, yield response chunks for streaming; if False, return full response
        
        Returns:
            A formatted final response string or generator of response chunks
        """
        self.logger.info("Forcing a final response without additional tool calls")
        
        # Add a system message to instruct the model to generate a final response
        self.conversation_history.append({
            "role": "system",
            "content": "IMPORTANT: Generate a final response summarizing what you know from the data already collected. DO NOT make any additional tool calls."
        })
        
        # Call the API with no tools to ensure it generates a text response
        try:
            final_response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation_history,
                temperature=self.temperature
            )
            
            # Extract text content
            final_content = final_response.choices[0].message.content or "I'm sorry, I encountered an issue processing your request. Please try asking in a different way."
            
            # Format the content
            final_content = self._format_for_streamlit(final_content)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_content
            })
            
            if streaming:
                # Return a generator of response chunks for streaming
                def chunk_generator():
                    current_chunk = ""
                    chunks = self._create_streaming_chunks(final_content)
                    for chunk in chunks:
                        current_chunk += chunk
                        yield current_chunk
                    
                    # Signal visualization availability if needed
                    if "visualization" in self.memory or "direct_chart" in self.memory:
                        yield current_chunk + "\n\n[visualization_available]"
                        
                return chunk_generator()
            else:
                # Return the full response string
                return final_content
        except Exception as e:
            self.logger.error(f"Error forcing final response: {e}")
            return "I'm sorry, I encountered an issue processing your request. Please try asking in a different way."