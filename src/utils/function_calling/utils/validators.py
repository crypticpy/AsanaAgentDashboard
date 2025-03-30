"""
Validator functions for input validation.

This module provides functions for validating various types of input data
before they are used in function calls or API requests.
"""
import logging
import re
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar

from datetime import datetime

logger = logging.getLogger("asana_validators")

# Type variable for generic functions
T = TypeVar('T')


def validate_gid(gid: Optional[str]) -> bool:
    """
    Validate that a GID is properly formatted.
    
    Args:
        gid: GID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not gid:
        return False
    
    # Asana GIDs are numeric
    return bool(re.match(r"^\d+$", gid))


def validate_date_string(date_str: Optional[str]) -> bool:
    """
    Validate that a date string is properly formatted.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not date_str:
        return False
    
    # Check if date follows YYYY-MM-DD format
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    
    try:
        # Try to parse the date
        datetime.fromisoformat(date_str)
        return True
    except ValueError:
        return False


def validate_int_range(value: Optional[int], min_value: Optional[int] = None, 
                       max_value: Optional[int] = None) -> bool:
    """
    Validate that an integer is within a specified range.
    
    Args:
        value: Integer to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return False
    
    if not isinstance(value, int):
        return False
    
    if min_value is not None and value < min_value:
        return False
    
    if max_value is not None and value > max_value:
        return False
    
    return True


def validate_non_empty_string(text: Optional[str]) -> bool:
    """
    Validate that a string is not empty.
    
    Args:
        text: String to validate
        
    Returns:
        True if valid, False otherwise
    """
    if text is None:
        return False
    
    if not isinstance(text, str):
        return False
    
    return bool(text.strip())


def validate_function_args(func: Callable[..., T], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate arguments for a function call.
    
    Args:
        func: Function to validate arguments for
        args: Arguments dictionary
        
    Returns:
        Validated and cleaned arguments dictionary
    """
    import inspect
    
    # Get function signature
    sig = inspect.signature(func)
    
    # Create validated args dictionary
    validated_args = {}
    
    # Validate each parameter
    for param_name, param in sig.parameters.items():
        # Skip self parameter for instance methods
        if param_name == "self":
            continue
        
        # Check if parameter is in args
        if param_name in args:
            value = args[param_name]
            
            # Add to validated args
            validated_args[param_name] = value
        elif param.default != inspect.Parameter.empty:
            # Use default value
            validated_args[param_name] = param.default
    
    return validated_args


def validate_chart_data(chart_type: str, data: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate chart data for a specific chart type.
    
    Args:
        chart_type: Type of chart
        data: Chart data
        
    Returns:
        Dictionary with validation status and error message
    """
    result = {"valid": "true", "error": ""}
    
    if chart_type == "bar":
        if "x_values" not in data or "y_values" not in data:
            result["valid"] = "false"
            result["error"] = "Bar chart requires x_values and y_values"
        elif len(data["x_values"]) != len(data["y_values"]):
            result["valid"] = "false"
            result["error"] = "x_values and y_values must have the same length"
    
    elif chart_type == "line":
        if "x_values" not in data or "y_values" not in data:
            result["valid"] = "false"
            result["error"] = "Line chart requires x_values and y_values"
        elif not isinstance(data["y_values"], list) or not all(isinstance(y, list) for y in data["y_values"]):
            result["valid"] = "false"
            result["error"] = "y_values must be a list of lists for line charts"
        elif any(len(data["x_values"]) != len(y) for y in data["y_values"]):
            result["valid"] = "false"
            result["error"] = "Each series in y_values must have the same length as x_values"
    
    elif chart_type == "pie":
        if "labels" not in data or "values" not in data:
            result["valid"] = "false"
            result["error"] = "Pie chart requires labels and values"
        elif len(data["labels"]) != len(data["values"]):
            result["valid"] = "false"
            result["error"] = "labels and values must have the same length"
        elif any(v < 0 for v in data["values"]):
            result["valid"] = "false"
            result["error"] = "Pie chart values cannot be negative"
    
    elif chart_type == "scatter":
        if "x_values" not in data or "y_values" not in data:
            result["valid"] = "false"
            result["error"] = "Scatter chart requires x_values and y_values"
        elif len(data["x_values"]) != len(data["y_values"]):
            result["valid"] = "false"
            result["error"] = "x_values and y_values must have the same length"
    
    elif chart_type == "timeline":
        if "tasks" not in data or "start_dates" not in data or "end_dates" not in data:
            result["valid"] = "false"
            result["error"] = "Timeline chart requires tasks, start_dates, and end_dates"
        elif not (len(data["tasks"]) == len(data["start_dates"]) == len(data["end_dates"])):
            result["valid"] = "false"
            result["error"] = "tasks, start_dates, and end_dates must have the same length"
    
    elif chart_type == "heatmap":
        if "x_values" not in data or "y_values" not in data or "z_values" not in data:
            result["valid"] = "false"
            result["error"] = "Heatmap chart requires x_values, y_values, and z_values"
        elif len(data["y_values"]) != len(data["z_values"]):
            result["valid"] = "false"
            result["error"] = "y_values and z_values must have the same length"
        elif any(len(row) != len(data["x_values"]) for row in data["z_values"]):
            result["valid"] = "false"
            result["error"] = "Each row in z_values must have the same length as x_values"
    
    else:
        result["valid"] = "false"
        result["error"] = f"Unsupported chart type: {chart_type}"
    
    return result


def validate_boolean(value: Any) -> Optional[bool]:
    """
    Validate and convert a value to a boolean.
    
    Args:
        value: Value to validate
        
    Returns:
        Boolean value or None if invalid
    """
    if value is None:
        return None
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ('true', 't', 'yes', 'y', '1'):
            return True
        if value in ('false', 'f', 'no', 'n', '0'):
            return False
    
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
    
    return None


def validate_tool_definition(tool_def: Dict[str, Any]) -> List[str]:
    """
    Validate that a tool definition has all required fields according to OpenAI's API.
    
    Args:
        tool_def: The tool definition to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    # Check type field
    if "type" not in tool_def:
        errors.append("Tool definition must include 'type' field")
    elif tool_def["type"] != "function":
        errors.append(f"Tool type must be 'function', got '{tool_def['type']}'")
    
    # Check function field
    if "function" not in tool_def:
        errors.append("Tool definition must include 'function' field")
        return errors  # Can't continue validation without function field
    
    function = tool_def["function"]
    
    # Check function name
    if "name" not in function:
        errors.append("Function must have a name")
    elif not isinstance(function["name"], str):
        errors.append("Function name must be a string")
    
    # Check function description
    if "description" not in function:
        errors.append("Function must have a description")
    elif not isinstance(function["description"], str):
        errors.append("Function description must be a string")
    
    # Check function parameters
    if "parameters" not in function:
        errors.append("Function must have parameters")
        return errors  # Can't continue validation without parameters
    
    parameters = function["parameters"]
    
    # Check parameters type
    if "type" not in parameters:
        errors.append("Parameters must have a type")
    elif parameters["type"] != "object":
        errors.append(f"Parameters type must be 'object', got '{parameters['type']}'")
    
    # Check parameters properties
    if "properties" not in parameters:
        errors.append("Parameters must have properties")
    elif not isinstance(parameters["properties"], dict):
        errors.append("Parameters properties must be an object")
    
    return errors


def validate_tool_definitions(tool_defs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Validate a list of tool definitions.
    
    Args:
        tool_defs: List of tool definitions to validate
        
    Returns:
        Dictionary mapping tool names to lists of validation errors
    """
    validation_results = {}
    
    for i, tool_def in enumerate(tool_defs):
        errors = validate_tool_definition(tool_def)
        
        # Use tool name if available, otherwise index
        tool_name = tool_def.get("function", {}).get("name", f"Tool_{i}")
        
        if errors:
            validation_results[tool_name] = errors
    
    return validation_results
