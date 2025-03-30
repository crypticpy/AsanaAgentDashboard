"""
Function definitions for Asana API function calling.

This module contains the JSON schema definitions for all functions that can be called
by the LLM through OpenAI's function calling capability.

"""
from typing import List, Dict, Any, Union
# import dataclasses # No longer needed as we use Pydantic models
from pydantic_core import PydanticUndefined # Import the correct sentinel

from src.utils.function_calling.utils.validators import validate_tool_definition, validate_tool_definitions
# Import schema models to dynamically build the chart schema
from src.utils.function_calling.schemas.visualization_schemas import (
    ChartConfig, BarChartData, LineChartData, PieChartData, ScatterChartData,
    TimelineChartData, HeatmapChartData, ChartType
)


# --- Helper to build the flat chart schema ---
def build_direct_chart_properties() -> Dict[str, Any]:
    """Dynamically builds the flat properties schema for create_direct_chart."""
    properties = {
        "chart_type": {
            "type": "string",
            "description": "Type of chart to create.",
            "enum": list(ChartType.__args__) # Get enum values dynamically
        },
        # Add ChartConfig fields (excluding title, handled separately or required)
        "title": {
            "type": "string",
            "description": "Title for the chart."
        },
        "subtitle": {
            "type": "string",
            "description": "Optional subtitle for the chart."
        },
        "x_axis_title": {
            "type": "string",
            "description": "Optional title for the X-axis."
        },
        "y_axis_title": {
            "type": "string",
            "description": "Optional title for the Y-axis."
        },
        "height": {
            "type": "integer",
            "description": "Optional height of the chart in pixels."
        },
        "width": {
            "type": "integer",
            "description": "Optional width of the chart in pixels."
        },
        "show_legend": {
            "type": "boolean",
            "description": "Whether to display the chart legend."
        },
         "color_scheme": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of hex color codes for the chart."
        }
    }

    # Add fields from all specific data models, avoiding duplicates
    all_data_fields = set()
    models_to_inspect = [
        BarChartData, LineChartData, PieChartData, ScatterChartData,
        TimelineChartData, HeatmapChartData
    ]

    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        List[str]: {"type": "array", "items": {"type": "string"}},
        List[Union[int, float]]: {"type": "array", "items": {"type": "number"}},
        List[List[Union[int, float]]]: {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
        List[Union[str, int, float]]: {"type": "array"}, # More generic for mixed lists
        List[Any]: {"type": "array"}, # Fallback for complex lists like colors
        # Add more specific list types if needed
    }

    for model in models_to_inspect:
        # Use Pydantic's model_fields for introspection
        for field_name, field_info in model.model_fields.items():
            if field_name not in all_data_fields and field_name not in properties:
                all_data_fields.add(field_name)
                # Get the type annotation; handle Optional types
                field_type = field_info.annotation
                origin_type = getattr(field_type, '__origin__', None)
                args = getattr(field_type, '__args__', [])

                # Handle Optional[T] by getting T
                if origin_type is Union and len(args) == 2 and type(None) in args:
                     actual_type = next(t for t in args if t is not type(None))
                else:
                     actual_type = field_type

                schema_type = type_mapping.get(actual_type, "string") # Default to string type if not mapped

                # Create base property dictionary with description from FieldInfo if available
                prop_dict = {
                    "description": field_info.description or f"Data field for {model.__name__}. Check specific chart type requirements."
                }

                # Add type information correctly
                if isinstance(schema_type, dict):
                    # Ensure 'items' is defined for arrays, fixing the BadRequestError
                    if schema_type.get("type") == "array" and "items" not in schema_type:
                         # Default to string items if not specified in type_mapping
                         # Special case for 'colors' which can be string or number
                         if field_name == 'colors':
                              # Allowing string or number for colors might be too complex for schema, default to string
                              schema_type["items"] = {"type": "string"}
                         else:
                              schema_type["items"] = {"type": "string"}
                    prop_dict.update(schema_type)
                else:
                    prop_dict["type"] = schema_type

                # Add enum if applicable (like orientation for bar chart)
                if field_name == 'orientation' and model is BarChartData:
                     prop_dict['enum'] = ["vertical", "horizontal"]
                if field_name == 'line_shape' and model is LineChartData:
                     prop_dict['enum'] = ["linear", "spline", "step"]
                # Add default value if present in FieldInfo, using PydanticUndefined
                # Corrected check: PydanticUndefined signifies no default was provided by the user,
                # but the field itself might have a default in the model definition.
                # We should only add 'default' to the schema if the FieldInfo actually has a default value.
                if field_info.default is not PydanticUndefined:
                     # Check if default is not None before adding, unless None is a valid default
                     # For simplicity here, let's assume None isn't a useful default for the schema
                     if field_info.default is not None:
                           prop_dict['default'] = field_info.default

                # Assign the correctly formed dictionary
                properties[field_name] = prop_dict

    return properties

# --- Function Definitions ---

# Project-related function definitions
PROJECT_FUNCTIONS = [
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
        "name": "get_project_gid_by_name",
        "description": "Find a project's GID by searching for its name",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Full or partial name of the project to search for"
                }
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "get_project_info_by_name",
        "description": "Get project details by searching for a project name",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Full or partial name of the project to search for"
                }
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "get_projects_by_owner",
        "description": "Get projects owned by a specific user",
        "parameters": {
            "type": "object",
            "properties": {
                "owner_name": {
                    "type": "string",
                    "description": "Name of the project owner to search for"
                }
            },
            "required": ["owner_name"]
        }
    }
]

# Task-related function definitions
TASK_FUNCTIONS = [
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
                    "description": "Filter for completed tasks (null for all tasks)"
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
        "description": "Search for tasks by name or description across all projects in the portfolio",
        "parameters": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": "Text to search for in task names or descriptions"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 20
                }
            },
            "required": ["search_text"]
        }
    }
]

# User/Assignee-related function definitions
USER_FUNCTIONS = [
    {
        "name": "get_tasks_by_assignee",
        "description": "Get tasks assigned to a specific user",
        "parameters": {
            "type": "object",
            "properties": {
                "assignee_name": {
                    "type": "string",
                    "description": "Name of the assignee to search for"
                },
                "completed": {
                    "type": "boolean",
                    "description": "Filter for completed tasks (null for all tasks)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return",
                    "default": 50
                }
            },
            "required": ["assignee_name"]
        }
    }
]

# Reporting/Analytics function definitions
REPORTING_FUNCTIONS = [
    {
        "name": "get_task_distribution_by_assignee",
        "description": "Get task distribution statistics grouped by assignee",
        "parameters": {
            "type": "object",
            "properties": {
                "project_gid": {
                    "type": "string",
                    "description": "The GID of the project (optional, will get data for all portfolio projects if not provided)"
                },
                "include_completed": {
                    "type": "boolean",
                    "description": "Whether to include completed tasks in the statistics",
                    "default": True
                }
            }
        }
    },
    {
        "name": "get_task_completion_trend",
        "description": "Get task completion trend over time",
        "parameters": {
            "type": "object",
            "properties": {
                "project_gid": {
                    "type": "string",
                    "description": "The GID of the project (optional, will get data for all portfolio projects if not provided)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 30
                }
            }
        }
    },
    {
        "name": "create_direct_chart",
        "description": "Create a visualization chart directly from provided data. Combine data and configuration arguments.",
        "parameters": {
            "type": "object",
            "properties": build_direct_chart_properties(), # Use the helper function
            # Define required fields - adjust as needed for robustness vs LLM flexibility
            "required": ["chart_type", "title"]
            # Consider adding core data fields like x_values/y_values if strictness is desired
            # "required": ["chart_type", "title", "x_values", "y_values"] # Example for bar/line
        }
    }
]

# Combine all function definitions
ALL_FUNCTION_DEFINITIONS = (
    PROJECT_FUNCTIONS +
    TASK_FUNCTIONS +
    USER_FUNCTIONS +
    REPORTING_FUNCTIONS
)

def get_function_definitions() -> List[Dict[str, Any]]:
    """
    Get the full list of function definitions for the assistant.

    Returns:
        List of function definition dictionaries
    """
    # Create properly structured tool definitions for OpenAI API
    function_definitions = []
    for func_def in ALL_FUNCTION_DEFINITIONS:
        # Create a tool entry with proper structure
        tool_definition = {
            "type": "function",
            "function": func_def
        }
        function_definitions.append(tool_definition)

    # Validate tool definitions
    validation_errors = validate_tool_definitions(function_definitions)
    if validation_errors:
        # Log any validation errors
        for tool_name, errors in validation_errors.items():
            for error in errors:
                print(f"Warning: Tool {tool_name} has validation error: {error}")

    return function_definitions

def get_function_definition_by_name(name: str) -> Dict[str, Any]:
    """
    Get a specific function definition by name.

    Args:
        name: Name of the function to retrieve

    Returns:
        Function definition dictionary or empty dict if not found
    """
    for func_def in ALL_FUNCTION_DEFINITIONS:
        if func_def["name"] == name:
            # Create a properly structured tool definition
            tool_definition = {
                "type": "function",
                "function": func_def
            }

            # Validate the tool definition
            errors = validate_tool_definition(tool_definition)
            if errors:
                # Log any validation errors
                for error in errors:
                    print(f"Warning: Tool {name} has validation error: {error}")

            return tool_definition
    return {}
