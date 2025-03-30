"""
Error handling module for function calling assistant.

This module provides functionality for handling and recovering from errors
that occur during function calling and LLM interaction.
"""
import logging
import traceback
import json
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic, Union

import streamlit as st
from openai.types.chat import ChatCompletion, ChatCompletionMessage

from src.utils.function_calling.utils.formatting import truncate_text


# Define a type variable for the error handler decorator
T = TypeVar('T')


class ErrorManager:
    """
    Error manager for function calling assistant.
    
    This class provides methods for handling and recovering from errors
    that occur during function calling and LLM interaction.
    """
    
    def __init__(self):
        """Initialize the error manager."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize error history
        self.error_history = []
        
        # Set maximum retries
        self.max_retries = 3
    
    def handle_llm_error(self, error: Exception, 
                        prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle errors that occur during LLM API calls.
        
        Args:
            error: Exception that occurred
            prompt: Optional prompt that triggered the error
            
        Returns:
            Error response dictionary
        """
        error_message = str(error)
        error_type = type(error).__name__
        
        # Log the error
        self.logger.error(f"LLM API error: {error_type}: {error_message}")
        if prompt:
            self.logger.debug(f"Prompt that caused error: {truncate_text(prompt, 100)}")
        
        # Add to error history
        self.error_history.append({
            "type": "llm_api",
            "error_type": error_type,
            "error_message": error_message,
            "prompt": prompt,
            "traceback": traceback.format_exc()
        })
        
        # Create error response
        return {
            "role": "assistant",
            "content": "I'm sorry, I encountered an error while processing your request. "
                      "Please try again or rephrase your question.",
            "has_error": True,
            "error_type": error_type,
            "error_message": error_message
        }
    
    def handle_tool_call_error(self, error: Exception,
                             function_name: Optional[str] = None,
                             args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle errors that occur during tool (function) calls.
        
        Args:
            error: Exception that occurred
            function_name: Name of the function that caused the error
            args: Arguments passed to the function
            
        Returns:
            Error response dictionary
        """
        error_message = str(error)
        error_type = type(error).__name__
        
        # Log the error
        self.logger.error(f"Tool call error: {error_type}: {error_message}")
        if function_name:
            self.logger.debug(f"Function that caused error: {function_name}")
        if args:
            self.logger.debug(f"Arguments: {args}")
        
        # Add to error history
        self.error_history.append({
            "type": "tool_call",
            "error_type": error_type,
            "error_message": error_message,
            "function_name": function_name,
            "args": args,
            "traceback": traceback.format_exc()
        })
        
        # Create error response
        return {
            "role": "assistant",
            "content": f"I encountered an error while trying to access Asana data: {error_message}. "
                      "Please check your inputs and try again.",
            "has_error": True,
            "error_type": error_type,
            "error_message": error_message
        }
    
    def handle_rate_limit_error(self, retry_after: Optional[int] = None) -> Dict[str, Any]:
        """
        Handle rate limit errors from the API.
        
        Args:
            retry_after: Optional seconds to wait before retrying
            
        Returns:
            Error response dictionary
        """
        message = "I've hit a rate limit. "
        
        if retry_after:
            message += f"Please try again after {retry_after} seconds."
        else:
            message += "Please try again later."
        
        # Add to error history
        self.error_history.append({
            "type": "rate_limit",
            "retry_after": retry_after
        })
        
        # Create error response
        return {
            "role": "assistant",
            "content": message,
            "has_error": True,
            "error_type": "rate_limit",
            "retry_after": retry_after
        }
    
    def handle_context_length_error(self) -> Dict[str, Any]:
        """
        Handle context length errors from the API.
        
        Returns:
            Error response dictionary
        """
        message = "I've hit the maximum context length. Please start a new conversation."
        
        # Add to error history
        self.error_history.append({
            "type": "context_length"
        })
        
        # Create error response
        return {
            "role": "assistant",
            "content": message,
            "has_error": True,
            "error_type": "context_length"
        }
    
    def handle_invalid_request_error(self, error_message: str) -> Dict[str, Any]:
        """
        Handle invalid request errors from the API.
        
        Args:
            error_message: Error message from the API
            
        Returns:
            Error response dictionary
        """
        # Log the error
        self.logger.error(f"Invalid request error: {error_message}")
        
        # Add to error history
        self.error_history.append({
            "type": "invalid_request",
            "error_message": error_message
        })
        
        # Create error response
        return {
            "role": "assistant",
            "content": "I encountered an error processing your request. Please try again with a simpler query.",
            "has_error": True,
            "error_type": "invalid_request",
            "error_message": error_message
        }
    
    def should_retry(self, error_type: str, retry_count: int) -> bool:
        """
        Determine if a failed operation should be retried.
        
        Args:
            error_type: Type of error that occurred
            retry_count: Number of retries already attempted
            
        Returns:
            True if the operation should be retried, False otherwise
        """
        # Check if we've exceeded the maximum retries
        if retry_count >= self.max_retries:
            return False
        
        # Determine if this error type is retryable
        retryable_errors = [
            "rate_limit",
            "timeout",
            "connection_error",
            "server_error"
        ]
        
        return error_type in retryable_errors
    
    def clear_error_history(self) -> None:
        """Clear the error history."""
        self.error_history = []
        self.logger.info("Error history cleared")
    
    def get_error_history(self) -> List[Dict[str, Any]]:
        """
        Get the error history.
        
        Returns:
            List of error dictionaries
        """
        return self.error_history
    
    def error_handler(self, func: Callable[..., T]) -> Callable[..., Union[T, Dict[str, Any]]]:
        """
        Decorator to handle errors in functions.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function that handles errors
        """
        def wrapper(*args, **kwargs):
            retry_count = 0
            
            while retry_count <= self.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_type = type(e).__name__
                    
                    # Check if we should retry
                    if self.should_retry(error_type, retry_count):
                        retry_count += 1
                        self.logger.info(f"Retrying {func.__name__} after error: {error_type} (attempt {retry_count})")
                        continue
                    
                    # Handle the error
                    if hasattr(args[0], '__name__') and args[0].__name__ == 'function_calling_assistant':
                        # This is an assistant method
                        return self.handle_tool_call_error(e, func.__name__, kwargs)
                    else:
                        # Generic error
                        return self.handle_tool_call_error(e, func.__name__)
            
            # If we get here, we've exhausted retries
            return {
                "status": "error",
                "error": f"Maximum retries ({self.max_retries}) exceeded",
                "function_name": func.__name__
            }
        
        return wrapper
