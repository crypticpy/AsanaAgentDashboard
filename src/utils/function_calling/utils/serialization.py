"""
Serialization utilities for converting Python objects to JSON.

This module provides utilities for converting Python objects, especially dataclasses,
to JSON-serializable formats.
"""
import json
import logging
import dataclasses
from typing import Any, Dict, List, Optional, Union, Callable

logger = logging.getLogger(__name__)


def dataclass_to_dict(obj: Any) -> Any:
    """
    Recursively convert a dataclass object to a dictionary.
    
    Args:
        obj: Object to convert (can be a dataclass, list, dict, or primitive type)
        
    Returns:
        JSON-serializable version of the object
    """
    if dataclasses.is_dataclass(obj):
        # Convert dataclass to dict
        result = {}
        for field in dataclasses.fields(obj):
            field_value = getattr(obj, field.name)
            result[field.name] = dataclass_to_dict(field_value)
        return result
    elif isinstance(obj, list):
        # Convert list elements
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        # Convert dict values
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    else:
        # Return primitive types as is
        return obj


class DataclassJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle dataclass objects."""
    
    def default(self, obj: Any) -> Any:
        """
        Convert dataclass objects to dictionaries for JSON serialization.
        
        Args:
            obj: Object to encode
            
        Returns:
            JSON-serializable version of the object
        """
        if dataclasses.is_dataclass(obj):
            return dataclass_to_dict(obj)
        # Let the base class handle other types or raise TypeError
        return super().default(obj)


def to_serializable(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable format.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable version of the object
    """
    try:
        # Try to convert dataclass objects
        if dataclasses.is_dataclass(obj):
            return dataclass_to_dict(obj)
        
        # Handle numpy integer types (int64, etc)
        # Check for numpy module using a string to avoid import errors if numpy is not installed
        if hasattr(obj, 'dtype') and hasattr(obj, 'item') and 'int' in str(obj.dtype):
            # Convert numpy int types to Python int
            return int(obj)
        
        # Try to serialize to JSON to check serializability
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError) as e:
        logger.warning(f"Object not directly serializable: {type(obj).__name__}, error: {str(e)}")
        
        # If it's a dictionary with dataclass values, convert the values
        if isinstance(obj, dict):
            return {k: to_serializable(v) for k, v in obj.items()}
        # If it's a list with dataclass items, convert the items
        elif isinstance(obj, list):
            return [to_serializable(item) for item in obj]
        # If it has a dictionary representation, use that
        elif hasattr(obj, "__dict__"):
            return to_serializable(obj.__dict__)
        # If it has a serialization method, use that
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        # As a last resort, convert to string
        else:
            logger.warning(f"Falling back to string representation for {type(obj).__name__}")
            return str(obj)


def serialize_response(response: Any) -> Dict[str, Any]:
    """
    Serialize a function response to a JSON-serializable dictionary.
    
    Args:
        response: Response from a function call (can be any type)
        
    Returns:
        JSON-serializable dictionary
    """
    try:
        # Check if it's already a dict
        if isinstance(response, dict):
            # Ensure all values are serializable
            return {k: to_serializable(v) for k, v in response.items()}
        
        # Check if it's a dataclass
        if dataclasses.is_dataclass(response):
            return dataclass_to_dict(response)
        
        # Try to convert to JSON to check serializability
        json.dumps(response)
        return {"result": response, "status": "success"}
    except Exception as e:
        logger.error(f"Error serializing response: {str(e)}")
        return {
            "status": "error",
            "error": f"Could not serialize response: {str(e)}",
            "result": str(response)
        }


def json_dumps(obj: Any) -> str:
    """
    Convert an object to a JSON string, handling dataclass objects.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(to_serializable(obj))
    except Exception as e:
        logger.error(f"Error serializing to JSON: {str(e)}")
        # Fallback to a basic error response
        return json.dumps({
            "status": "error",
            "error": f"JSON serialization error: {str(e)}"
        }) 