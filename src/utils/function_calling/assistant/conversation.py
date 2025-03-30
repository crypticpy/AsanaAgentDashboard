"""
Conversation management module for function calling assistant.

This module provides functionality for managing conversations with the user,
including storing and retrieving conversation history, system prompts, etc.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import streamlit as st

from src.utils.function_calling.utils.formatting import format_message_for_display


class ConversationManager:
    """
    Conversation manager for the function calling assistant.
    
    This class keeps track of the conversation history and provides methods for
    formatting and managing the conversation.
    """
    
    def __init__(self):
        """
        Initialize the conversation manager.
        """
        self.messages = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.system_prompt = self._get_default_system_prompt()
        self.tool_call_count = 0
        self.token_count = 0
        
        # Initialize statistics
        self.message_count = 0
        self.start_time = datetime.now()
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt.
        
        Returns:
            Default system prompt string
        """
        return (
            "You are an Asana assistant that helps users get information about their "
            "Asana projects, tasks, and teams. You can search for projects, get task "
            "details, and generate reports and visualizations based on Asana data. "
            "When the user asks a question that requires data from Asana, use the "
            "available functions to get the data you need.\n\n"
            "Remember the following:\n"
            "1. Always try to get specific information the user needs using the available functions.\n"
            "2. For tasks related to analytics or reporting, create visualizations when appropriate.\n"
            "3. Be conversational but concise in your responses.\n"
            "4. If you need to show data in a table, format it clearly for readability.\n"
            "5. When you're not sure which project, task, or user the user is referring to, "
            "ask clarifying questions or search for the information."
        )
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt.
        
        Args:
            prompt: System prompt string
        """
        self.system_prompt = prompt
        self.logger.info("System prompt updated")
    
    def get_system_prompt(self) -> str:
        """
        Get the current system prompt.
        
        Returns:
            System prompt string
        """
        return self.system_prompt
    
    def add_system_message(self, content: str) -> Dict[str, Any]:
        """
        Add a system message to the conversation history.
        
        Args:
            content: Message content
            
        Returns:
            Message dictionary
        """
        message = {
            "role": "system",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        self.message_count += 1
        
        return message
    
    def add_user_message(self, content: str) -> Dict[str, Any]:
        """
        Add a user message to the conversation history.
        
        Args:
            content: Message content
            
        Returns:
            Message dictionary
        """
        message = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        self.message_count += 1
        
        return message
    
    def add_assistant_message(self, content: str, 
                             has_tool_calls: bool = False, 
                             tool_calls_count: int = 0) -> Dict[str, Any]:
        """
        Add an assistant message to the conversation history.
        
        Args:
            content: Message content
            has_tool_calls: Whether the message has tool calls
            tool_calls_count: Number of tool calls in the message
            
        Returns:
            Message dictionary
        """
        message = {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "has_tool_calls": has_tool_calls,
            "tool_calls_count": tool_calls_count
        }
        
        self.messages.append(message)
        self.message_count += 1
        
        # Update statistics
        if has_tool_calls:
            self.tool_call_count += tool_calls_count
        
        return message
    
    def add_tool_message(self, name: str, content: Union[str, Dict[str, Any]], 
                        tool_call_id: str) -> Dict[str, Any]:
        """
        Add a tool message to the conversation history.
        
        Args:
            name: Tool name
            content: Tool message content
            tool_call_id: ID of the tool call
            
        Returns:
            Message dictionary
        """
        # Convert content to string if it's a dictionary
        if isinstance(content, dict):
            content_str = json.dumps(content)
        else:
            content_str = content
        
        message = {
            "role": "tool",
            "name": name,
            "content": content_str,
            "tool_call_id": tool_call_id,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        return message
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the full conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.messages
    
    def get_history_for_api(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history formatted for the OpenAI API.
        
        Returns:
            List of message dictionaries formatted for the API
        """
        # Start with the system message
        api_messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add the rest of the messages
        for message in self.messages:
            # Skip system messages (we already added our system prompt)
            if message["role"] == "system":
                continue
            
            # Copy relevant fields for API
            api_message = {
                "role": message["role"],
                "content": message.get("content", "")
            }
            
            # Add tool-specific fields
            if message["role"] == "tool":
                api_message["name"] = message["name"]
                api_message["tool_call_id"] = message["tool_call_id"]
            
            # Add tool_calls if present
            if "tool_calls" in message:
                api_message["tool_calls"] = message["tool_calls"]
            
            api_messages.append(api_message)
        
        return api_messages
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []
        self.message_count = 0
        self.tool_call_count = 0
        self.token_count = 0
        self.start_time = datetime.now()
        self.logger.info("Conversation history cleared")
    
    def get_formatted_history(self) -> List[Dict[str, Any]]:
        """
        Get a formatted version of the conversation history for display.
        
        Returns:
            List of formatted message dictionaries
        """
        formatted_history = []
        
        for message in self.messages:
            # Skip system messages
            if message["role"] == "system":
                continue
            
            # Format the message
            formatted_message = {
                "role": message["role"],
                "content": format_message_for_display(message),
                "timestamp": message.get("timestamp", "")
            }
            
            formatted_history.append(formatted_message)
        
        return formatted_history
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        # Calculate duration
        duration = datetime.now() - self.start_time
        duration_seconds = duration.total_seconds()
        
        # Count messages by role
        user_messages = sum(1 for m in self.messages if m["role"] == "user")
        assistant_messages = sum(1 for m in self.messages if m["role"] == "assistant")
        
        # Reset statistics
        self.tool_call_count = 0
        self.token_count = 0
        
        return {
            "history_length": len(self.get_formatted_history()),
            "message_count": len(self.messages),
            "tool_call_count": self.tool_call_count,
            "token_count": self.token_count,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "duration_seconds": duration_seconds,
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now().isoformat()
        }
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
