"""
API helper functions for interacting with the Asana API.

This module provides utility functions for working with the Asana API,
including error handling, rate limiting, and data processing.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Callable, TypeVar, Generic, Union
import json
from functools import wraps

import streamlit as st
import asana
import pandas as pd
from datetime import datetime, timedelta

# Type variable for generic functions
T = TypeVar('T')

logger = logging.getLogger("asana_api_helpers")


def rate_limit(min_interval: float = 1.0):
    """
    Decorator to apply rate limiting to API calls.
    
    Args:
        min_interval: Minimum time interval between calls in seconds
        
    Returns:
        Decorated function
    """
    last_call_time = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get a unique key for this function
            key = func.__name__
            
            # Get current time
            current_time = time.time()
            
            # Check if we need to apply rate limiting
            if key in last_call_time:
                time_since_last_call = current_time - last_call_time[key]
                if time_since_last_call < min_interval:
                    sleep_time = min_interval - time_since_last_call
                    logger.debug(f"Rate limiting {key}: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
            
            # Update last call time
            last_call_time[key] = time.time()
            
            # Call the function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def handle_api_error(func: Callable[..., T]) -> Callable[..., Union[T, Dict[str, Any]]]:
    """
    Decorator to handle API errors gracefully.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that handles API errors
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except asana.error.AsanaError as e:
            logger.error(f"Asana API error in {func.__name__}: {str(e)}")
            # Format a standardized error response
            return {
                "status": "error",
                "error": f"Asana API error: {str(e)}",
                "system_message": "An error occurred while communicating with the Asana API."
            }
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            # Format a standardized error response
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "system_message": "An unexpected error occurred while processing your request."
            }
    
    return wrapper


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested values from a dictionary.
    
    Args:
        data: Dictionary to extract from
        *keys: Keys to traverse
        default: Default value to return if not found
        
    Returns:
        Value or default if not found
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def format_date(date_str: Optional[str]) -> Optional[str]:
    """
    Format a date string from Asana API to a human-readable format.
    
    Args:
        date_str: Date string from Asana API
        
    Returns:
        Formatted date string or None if input is None
    """
    if not date_str:
        return None
    
    try:
        # Asana uses ISO 8601 format for dates
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d')
    except Exception as e:
        logger.warning(f"Error formatting date {date_str}: {e}")
        return date_str


def calculate_date_range(days: int = 30) -> Tuple[str, str]:
    """
    Calculate a date range from now to a number of days in the past.
    
    Args:
        days: Number of days to look back
        
    Returns:
        Tuple of (start_date, end_date) in ISO format
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return start_date.isoformat(), end_date.isoformat()


def parse_gid(gid: Optional[str]) -> Optional[str]:
    """
    Parse and validate a GID.
    
    Args:
        gid: GID string to validate
        
    Returns:
        Validated GID or None if invalid
    """
    if not gid:
        return None
    
    # Remove any non-digit characters
    clean_gid = ''.join(filter(str.isdigit, gid))
    
    # Check if we have a valid GID (Asana GIDs are numeric)
    if clean_gid:
        return clean_gid
    
    return None


def get_portfolio_gid() -> str:
    """
    Get the portfolio GID from session state.
    
    Returns:
        Portfolio GID string
    """
    portfolio_gid = st.session_state.get("portfolio_gid", "")
    
    if not portfolio_gid or portfolio_gid == "your_portfolio_gid_here":
        logger.warning("No valid portfolio GID found in session state")
    
    return portfolio_gid


def get_team_gid() -> str:
    """
    Get the team GID from session state.
    
    Returns:
        Team GID string
    """
    team_gid = st.session_state.get("team_gid", "")
    
    if not team_gid or team_gid == "your_team_gid_here":
        logger.warning("No valid team GID found in session state")
    
    return team_gid


def create_dataframe_from_tasks(tasks: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert a list of task dictionaries to a pandas DataFrame.
    
    Args:
        tasks: List of task dictionaries from Asana API
        
    Returns:
        Pandas DataFrame with task data
    """
    if not tasks:
        return pd.DataFrame()
    
    # Extract relevant fields
    task_data = []
    for task in tasks:
        task_data.append({
            'gid': task.get('gid', ''),
            'name': task.get('name', ''),
            'assignee_name': safe_get(task, 'assignee', 'name', default='Unassigned'),
            'assignee_gid': safe_get(task, 'assignee', 'gid', default=''),
            'due_on': format_date(task.get('due_on')),
            'completed': task.get('completed', False),
            'completed_at': format_date(task.get('completed_at')),
            'created_at': format_date(task.get('created_at'))
        })
    
    return pd.DataFrame(task_data)
