"""
Function calling assistant modules.

This package provides classes for creating and managing an assistant that can
call functions in the Asana API through OpenAI's function calling capability.
"""

from src.utils.function_calling.assistant.base import BaseFunctionCallingAssistant
from src.utils.function_calling.assistant.conversation import ConversationManager
from src.utils.function_calling.assistant.streaming import StreamingConversationHandler
from src.utils.function_calling.assistant.visualization import VisualizationManager
from src.utils.function_calling.assistant.error_handling import ErrorManager


class FunctionCallingAssistant:
    """
    Main function calling assistant class.
    
    This class combines all the specialized assistant modules into a single interface
    for creating an AI assistant that can call functions in the Asana API.
    """
    
    def __init__(self, api_instances):
        """
        Initialize the function calling assistant.
        
        Args:
            api_instances: Dictionary of Asana API instances
        """
        # Initialize base assistant
        self.base_assistant = BaseFunctionCallingAssistant(api_instances)
        
        # Initialize supporting modules
        self.conversation = ConversationManager()
        self.streaming = StreamingConversationHandler(self.base_assistant)
        self.visualization = VisualizationManager()
        self.error_manager = ErrorManager()
        
        # Store API instances for reference
        self.api_instances = api_instances
        
        # Set up logger
        self.logger = self.base_assistant.logger
        
        # Initialize memory dictionary for compatibility with older interface
        self._memory = {}
    
    def setup(self, api_key=None, model="gpt-4o"):
        """
        Set up the assistant.
        
        Args:
            api_key: OpenAI API key (optional, will use from session state if not provided)
            model: OpenAI model to use
        """
        # Set up the LLM
        self.base_assistant.setup_llm(api_key, model)
        
        # Set system prompt in conversation history
        system_prompt = self.conversation.get_system_prompt()
        self.base_assistant.add_message_to_history({
            "role": "system",
            "content": system_prompt
        })
        
        self.logger.info(f"Assistant set up with model: {model}")
    
    def generate_response(self, prompt):
        """
        Generate a response to a user prompt.
        
        Args:
            prompt: User prompt
            
        Returns:
            Response message dictionary
        """
        try:
            # Add user message to conversation
            self.conversation.add_user_message(prompt)
            
            # Generate response using base assistant
            user_message = {"role": "user", "content": prompt}
            self.base_assistant.add_message_to_history(user_message)
            
            response = self.base_assistant.generate_response_from_prompt(prompt)
            
            # Add assistant response to conversation
            self.conversation.add_assistant_message(
                response["content"],
                response.get("has_tool_calls", False),
                response.get("tool_calls_count", 0)
            )
            
            return response
        except Exception as e:
            # Handle error
            error_response = self.error_manager.handle_llm_error(e, prompt)
            
            # Add error message to conversation
            self.conversation.add_assistant_message(
                error_response["content"],
                False,
                0
            )
            
            return error_response
    
    def stream_response(self, prompt, stream_callback=None):
        """
        Stream a response to a user prompt.
        
        Args:
            prompt: User prompt
            stream_callback: Callback function for streaming updates
            
        Returns:
            Generator yielding response chunks
            
        Warning:
            This method is no longer in use. The application now uses the non-streaming
            generate_response method instead. This is kept for potential future use but
            may not be fully compatible with the latest OpenAI API changes.
        """
        try:
            # Add user message to conversation
            self.conversation.add_user_message(prompt)
            
            # Stream response
            return self.streaming.stream_response_with_tool_calls(prompt, stream_callback)
        except Exception as e:
            # Handle error
            error_response = self.error_manager.handle_llm_error(e, prompt)
            
            # Add error message to conversation
            self.conversation.add_assistant_message(
                error_response["content"],
                False,
                0
            )
            
            # Yield error response
            yield {
                "type": "error",
                "error": str(e),
                "content": error_response["content"]
            }
            
            return error_response
    
    def get_conversation_history(self):
        """
        Get the conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.conversation.get_formatted_history()
    
    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation.clear_history()
        self.base_assistant.clear_conversation_history()
        self.error_manager.clear_error_history()
        
        # Re-add system message
        system_prompt = self.conversation.get_system_prompt()
        self.base_assistant.add_message_to_history({
            "role": "system",
            "content": system_prompt
        })
        
        # Clear memory
        self._memory = {}
        
        self.logger.info("Conversation cleared")
    
    def set_system_prompt(self, prompt):
        """
        Set the system prompt.
        
        Args:
            prompt: System prompt string
        """
        self.conversation.set_system_prompt(prompt)
        
        # Clear conversation and re-add system message
        self.clear_conversation()
    
    def create_visualization(self, function_name, function_args, function_result):
        """
        Create a visualization based on function call results.
        
        Args:
            function_name: Name of the function called
            function_args: Arguments to the function
            function_result: Result of the function call
            
        Returns:
            Plotly figure object or None if no visualization is appropriate
        """
        return self.visualization.detect_and_render_visualization(
            function_name,
            function_args,
            function_result
        )
    
    # =============================================
    # Compatibility methods with old implementation
    # =============================================
    
    @property
    def conversation_history(self):
        """Property to access the conversation history for compatibility."""
        return self.base_assistant.conversation_history
    
    @property
    def memory(self):
        """
        Property to access memory dictionary for compatibility.
        Used for storing visualization data and other temporary information.
        """
        return self._memory
    
    @memory.setter
    def memory(self, value):
        """Setter for memory property."""
        self._memory = value
    
    def reset_and_initialize_conversation(self):
        """
        Reset and initialize the conversation.
        This method is for compatibility with the old implementation.
        """
        # Clear conversation
        self.clear_conversation()
        
        # Set up default system prompt
        default_system_prompt = self.conversation.get_system_prompt()
        self.base_assistant.add_message_to_history({
            "role": "system",
            "content": default_system_prompt
        })
        
        # Clear memory
        self._memory = {}
        
        self.logger.info("Conversation reset and initialized")
    
    def generate_streaming_response(self, query):
        """
        Generate a streaming response.
        This method is for compatibility with the old implementation.
        
        Args:
            query: User query
            
        Returns:
            Generator yielding response chunks
            
        Warning:
            This method is no longer used in the application. The app now uses
            the non-streaming generate_response method instead.
        """
        self.logger.warning("The streaming implementation is not currently used and may not work correctly")
        # Add message to history
        self.conversation.add_user_message(query)
        user_message = {"role": "user", "content": query}
        self.base_assistant.add_message_to_history(user_message)
        
        # Stream response
        response_generator = self.streaming.stream_response_with_tool_calls(query)
        collected_response = ""
        
        # Process response chunks
        for chunk in response_generator:
            # If this is a content chunk, yield it
            if chunk.get("type") == "content" or chunk.get("type") == "final_content":
                content = chunk.get("content", "")
                collected_response += content
                yield collected_response
        
        # Add message to conversation
        self.conversation.add_assistant_message(
            collected_response,
            False,
            0
        )
        
        # Return the final collected response
        return collected_response
    
    def generate_visualization(self):
        """
        Generate a visualization from the data in memory.
        This method is for compatibility with the old implementation.
        
        Returns:
            Plotly figure object or None
        """
        # Check if we have visualization data in memory
        if "visualization" in self._memory:
            return self._memory["visualization"].get("figure")
        
        # If we have direct chart data, try to render it
        if "direct_chart" in self._memory:
            # Get chart data
            chart_data = self._memory["direct_chart"]
            chart_type = chart_data.get("chart_type", "")
            
            # Try to create a figure
            try:
                import plotly.graph_objects as go
                
                # If we have raw chart data, render it
                if "data" in chart_data:
                    return self.visualization.render_chart_from_json(chart_data["data"])
                
                # Otherwise, create a simple placeholder
                fig = go.Figure()
                fig.update_layout(
                    title=chart_data.get("title", "Chart"),
                    annotations=[{
                        "text": f"Chart type: {chart_type}",
                        "showarrow": False,
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5
                    }]
                )
                return fig
            except Exception as e:
                self.logger.error(f"Error rendering direct chart: {e}")
                return None
        
        return None
    
    def _get_visualization_title(self, function_name, data):
        """
        Get a title for the visualization based on the function and data.
        
        Args:
            function_name: Name of the function
            data: Function result data
            
        Returns:
            Title string
        """
        if function_name == "get_task_distribution_by_assignee":
            project_gid = data.get("project_gid")
            if project_gid == "all_projects":
                return "Task Distribution by Assignee (All Projects)"
            return "Task Distribution by Assignee"
        
        elif function_name == "get_task_completion_trend":
            days = data.get("days", 30)
            return f"Task Completion Trend (Last {days} Days)"
        
        elif function_name == "get_project_progress":
            project_name = data.get("project_name", "Project")
            return f"{project_name} Progress"
        
        elif function_name == "get_team_workload":
            return "Team Workload"
        
        return "Visualization"


__all__ = [
    "FunctionCallingAssistant",
    "BaseFunctionCallingAssistant",
    "ConversationManager",
    "StreamingConversationHandler",
    "VisualizationManager",
    "ErrorManager"
]
