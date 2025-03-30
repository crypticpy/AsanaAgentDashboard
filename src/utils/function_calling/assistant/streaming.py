"""
Streaming conversation handler for function calling assistant.

This module extends the base assistant with streaming conversation capabilities
for a more interactive user experience.
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional, Generator, Union, Callable

import streamlit as st
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam

from src.utils.function_calling.assistant.base import BaseFunctionCallingAssistant


class StreamingConversationHandler:
    """
    Streaming conversation handler for function calling assistant.
    
    This class provides methods for streaming responses from the OpenAI API
    and handling the conversation flow with function calling.
    
    Warning:
        This streaming implementation is not currently used in the application.
        The application has switched to using the non-streaming implementation instead.
        This code is kept for potential future use but may not be fully compatible 
        with the latest OpenAI API changes.
    """
    
    def __init__(self, assistant: BaseFunctionCallingAssistant):
        """
        Initialize the streaming conversation handler.
        
        Args:
            assistant: Base function calling assistant instance
        """
        self.assistant = assistant
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize placeholders for streaming
        self.current_message_parts = []
        
        # Initialize statistics
        self.tool_call_count = 0
        self.token_count = 0
    
    def stream_chat_completion(self, messages: List[Dict[str, Any]]) -> Generator[ChatCompletionChunk, None, None]:
        """
        Stream a chat completion from the OpenAI API.
        
        Args:
            messages: List of message dictionaries
            
        Yields:
            ChatCompletionChunk objects
        """
        if not self.assistant.client:
            self.logger.error("LLM client not set up, call setup_llm first")
            raise ValueError("LLM client not set up, call setup_llm first")
        
        # Call the API with streaming enabled
        stream = self.assistant.client.chat.completions.create(
            model=self.assistant.model,
            messages=messages,
            tools=self.assistant.function_definitions,
            temperature=self.assistant.temperature,
            stream=True
        )
        
        # Return the stream
        for chunk in stream:
            yield chunk
    
    def process_streamed_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """
        Process tool calls with streaming updates.
        
        Args:
            tool_calls: List of tool call dictionaries
            
        Yields:
            Status updates during processing
        """
        if not tool_calls:
            return
        
        for i, tool_call in enumerate(tool_calls):
            # Skip if already processed
            tool_call_id = tool_call.get("id", "")
            if tool_call_id in self.assistant.processed_tool_call_ids:
                self.logger.debug(f"Skipping already processed tool call: {tool_call_id}")
                continue
            
            # Mark as processed
            self.assistant.processed_tool_call_ids.add(tool_call_id)
            
            # Get function details
            function_name = tool_call.get("function", {}).get("name", "")
            function_args_str = tool_call.get("function", {}).get("arguments", "{}")
            
            # Update statistics
            self.tool_call_count += 1
            
            # Yield status update - starting function call
            yield {
                "status": "calling_function",
                "function_name": function_name,
                "index": i,
                "total": len(tool_calls)
            }
            
            try:
                # Parse arguments
                function_args = json.loads(function_args_str)
                
                # Check if function is available
                if function_name not in self.assistant.available_functions:
                    error_message = f"Function '{function_name}' not found"
                    self.logger.error(error_message)
                    
                    # Add error response to conversation history
                    tool_response = {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": error_message})
                    }
                    self.assistant.add_message_to_history(tool_response)
                    
                    # Yield status update - function error
                    yield {
                        "status": "function_error",
                        "function_name": function_name,
                        "error": error_message,
                        "index": i,
                        "total": len(tool_calls)
                    }
                    continue
                
                # Call the function
                self.logger.info(f"Calling function: {function_name} with args: {function_args}")
                
                # Record start time
                start_time = time.time()
                
                # Call the function
                function_response = self.assistant.available_functions[function_name](**function_args)
                
                # Record end time
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Add response to conversation history
                tool_response = {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_response)
                }
                self.assistant.add_message_to_history(tool_response)
                
                # Yield status update - function complete
                yield {
                    "status": "function_complete",
                    "function_name": function_name,
                    "execution_time": execution_time,
                    "success": True,
                    "index": i,
                    "total": len(tool_calls),
                    "response": function_response
                }
            except Exception as e:
                self.logger.error(f"Error processing tool call: {str(e)}")
                
                # Add error response to conversation history
                tool_response = {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"error": str(e)})
                }
                self.assistant.add_message_to_history(tool_response)
                
                # Yield status update - function error
                yield {
                    "status": "function_error",
                    "function_name": function_name,
                    "error": str(e),
                    "index": i,
                    "total": len(tool_calls)
                }
    
    def stream_response_with_tool_calls(self, 
                                       prompt: str, 
                                       stream_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
                                      ) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        Stream a response with function calling.
        
        Args:
            prompt: User prompt
            stream_callback: Callback function for streaming updates
            
        Yields:
            Status updates during processing
            
        Returns:
            Final response dictionary
        """
        # Add user message to history
        user_message = {"role": "user", "content": prompt}
        self.assistant.add_message_to_history(user_message)
        
        # Reset streaming state
        self.current_message_parts = []
        collected_message = ""
        collected_tool_calls = []
        current_tool_call = None
        
        # Get a streaming response
        for chunk in self.stream_chat_completion(self.assistant.conversation_history):
            delta = chunk.choices[0].delta
            
            # Handle content
            if delta.content:
                collected_message += delta.content
                self.current_message_parts.append(delta.content)
                
                # Call the callback if provided
                if stream_callback:
                    stream_callback("content", {
                        "content": delta.content,
                        "full_content": collected_message
                    })
                
                # Yield content update
                yield {
                    "type": "content",
                    "content": delta.content,
                    "full_content": collected_message
                }
            
            # Handle tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    # Initialize new tool call if index is new
                    if tc.index is not None:
                        if len(collected_tool_calls) <= tc.index:
                            collected_tool_calls.append({
                                "id": "",
                                "function": {"name": "", "arguments": ""}
                            })
                        current_tool_call = collected_tool_calls[tc.index]
                    
                    # Update ID
                    if tc.id:
                        current_tool_call["id"] = tc.id
                    
                    # Update function name
                    if tc.function and tc.function.name:
                        current_tool_call["function"]["name"] = tc.function.name
                    
                    # Update function arguments
                    if tc.function and tc.function.arguments:
                        current_tool_call["function"]["arguments"] += tc.function.arguments
                    
                    # Call the callback if provided
                    if stream_callback:
                        stream_callback("tool_call", {
                            "tool_calls": collected_tool_calls
                        })
                    
                    # Yield tool call update
                    yield {
                        "type": "tool_call",
                        "tool_calls": collected_tool_calls
                    }
        
        # Final message with all content and tool calls
        full_message = {
            "role": "assistant",
            "content": collected_message or "",  # Ensure we never have None for content
        }
        
        if collected_tool_calls:
            full_message["tool_calls"] = collected_tool_calls
        
        # Add assistant message to history
        self.assistant.add_message_to_history(full_message)
        
        # If there are tool calls, process them
        if collected_tool_calls:
            # Yield processing status
            yield {
                "type": "processing_tools",
                "tool_count": len(collected_tool_calls)
            }
            
            # Process tool calls with streaming updates
            for update in self.process_streamed_tool_calls(collected_tool_calls):
                # Call the callback if provided
                if stream_callback:
                    stream_callback("tool_processing", update)
                
                # Yield tool processing update
                yield {
                    "type": "tool_processing",
                    **update
                }
            
            # Get final response with tool results
            yield {
                "type": "thinking",
                "message": "Thinking..."
            }
            
            # Stream final response
            final_collected_message = ""
            
            try:
                for chunk in self.stream_chat_completion(self.assistant.conversation_history):
                    delta = chunk.choices[0].delta
                    
                    if delta.content:
                        final_collected_message += delta.content
                        
                        # Call the callback if provided
                        if stream_callback:
                            stream_callback("final_content", {
                                "content": delta.content,
                                "full_content": final_collected_message
                            })
                        
                        # Yield content update
                        yield {
                            "type": "final_content",
                            "content": delta.content,
                            "full_content": final_collected_message
                        }
                
                # Add final assistant message to history
                self.assistant.add_message_to_history({
                    "role": "assistant",
                    "content": final_collected_message or ""  # Ensure we never have None
                })
            except Exception as e:
                self.logger.error(f"Error in final response streaming: {str(e)}")
                final_collected_message = f"I'm sorry, I encountered an error while processing the tool results: {str(e)}"
                
                # Add error message to history
                self.assistant.add_message_to_history({
                    "role": "assistant",
                    "content": final_collected_message
                })
            
            # Return final response
            return {
                "role": "assistant",
                "content": final_collected_message,
                "has_tool_calls": True,
                "tool_calls_count": len(collected_tool_calls),
                "tool_call_count": self.tool_call_count
            }
        else:
            # No tool calls, just return the message
            return {
                "role": "assistant",
                "content": collected_message or "",  # Ensure we never have None
                "has_tool_calls": False,
                "tool_calls_count": 0,
                "tool_call_count": 0
            }
