"""
Formatting utilities for message and data processing.

This module provides utilities for formatting messages, responses, and data
for display to the user or for processing by the model.
"""
import json
import re
from typing import Dict, Any, List, Optional, Union

import pandas as pd
from datetime import datetime, timedelta


def format_json_for_display(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
    """
    Format JSON data for display to the user.
    
    Args:
        data: JSON data to format
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=2)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def format_message_for_display(message: Dict[str, Any]) -> str:
    """
    Format a message for display to the user.
    
    Args:
        message: Message dictionary
        
    Returns:
        Formatted message string
    """
    if "content" in message and message["content"]:
        return message["content"]
    
    return ""


def format_table_for_display(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format tabular data for display.
    
    Args:
        data: List of dictionaries containing tabular data
        
    Returns:
        Pandas DataFrame
    """
    if not data:
        return pd.DataFrame()
    
    return pd.DataFrame(data)


def format_time_ago(timestamp: Union[str, datetime]) -> str:
    """
    Format a timestamp as a human-readable "time ago" string.
    
    Args:
        timestamp: Timestamp to format
        
    Returns:
        Human-readable time ago string
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return "Invalid date"
    
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from a markdown text.
    
    Args:
        text: Markdown text containing code blocks
        
    Returns:
        List of dictionaries containing language and code
    """
    # Regular expression to match code blocks
    pattern = r"```([\w-]*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    
    code_blocks = []
    for language, code in matches:
        code_blocks.append({
            "language": language.strip() or "text",
            "code": code.strip()
        })
    
    return code_blocks


def format_dataframe_as_markdown(df: pd.DataFrame) -> str:
    """
    Format a pandas DataFrame as a markdown table.
    
    Args:
        df: DataFrame to format
        
    Returns:
        Markdown table string
    """
    if df.empty:
        return "No data available"
    
    markdown = "| " + " | ".join(df.columns) + " |\n"
    markdown += "| " + " | ".join(["---" for _ in df.columns]) + " |\n"
    
    for _, row in df.iterrows():
        markdown += "| " + " | ".join([str(cell) for cell in row]) + " |\n"
    
    return markdown


def clean_html_tags(text: str) -> str:
    """
    Remove HTML tags from text.
    
    Args:
        text: Text containing HTML tags
        
    Returns:
        Cleaned text
    """
    return re.sub(r"<[^>]+>", "", text)


def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds as a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    if hours < 24:
        if minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
    
    days = hours // 24
    hours = hours % 24
    
    if hours == 0:
        return f"{days} day{'s' if days != 1 else ''}"
    
    return f"{days} day{'s' if days != 1 else ''} and {hours} hour{'s' if hours != 1 else ''}"
