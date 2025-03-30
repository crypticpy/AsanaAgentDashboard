# src/components/function_chat.py
import streamlit as st
import plotly.graph_objects as go
import json
import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd # Import pandas for type hinting

# Import necessary components from the function calling utility
from src.utils.function_calling.assistant.base import BaseFunctionCallingAssistant
# Removed unused imports for specific chart data models and helper functions
# from src.utils.function_calling.schemas.visualization_schemas import ChartConfig, BarChartData, LineChartData, PieChartData, ScatterChartData, TimelineChartData, HeatmapChartData
# from src.utils.function_calling.tools.helpers import create_bar_chart, create_line_chart, create_pie_chart, create_scatter_chart, create_timeline_chart, create_heatmap_chart

# Configure logging
logger = logging.getLogger("function_chat")

# --- Initialization ---

def initialize_function_chat_state():
    """Initializes session state variables required for the function chat."""
    if "assistant" not in st.session_state:
        st.session_state.assistant = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = None
    if "api_instances" not in st.session_state:
        st.session_state.api_instances = None # Asana client etc.
    if "asana_base_client" not in st.session_state: # Added check for base client
        st.session_state.asana_base_client = None
    if "task_df" not in st.session_state:
        st.session_state.task_df = None # Ensure task_df is initialized

def reset_function_chat():
    """Resets the chat state, clearing messages and the assistant."""
    st.session_state.messages = []
    # Re-initialize assistant if possible, otherwise set to None
    # Use asana_base_client here
    if st.session_state.openai_api_key and st.session_state.asana_base_client and isinstance(st.session_state.task_df, pd.DataFrame):
         try:
            st.session_state.assistant = BaseFunctionCallingAssistant(
                openai_api_key=st.session_state.openai_api_key,
                asana_api_client=st.session_state.asana_base_client, # Corrected key access
                task_df=st.session_state.task_df
            )
            logger.info("Function chat state reset and assistant re-initialized.")
         except Exception as e:
             logger.error(f"Failed to re-initialize assistant on reset: {e}")
             st.session_state.assistant = None
    else:
        st.session_state.assistant = None
        logger.info("Function chat state reset. Assistant set to None as prerequisites missing.")


# --- UI Rendering ---

# Removed the _render_visualization function as it's no longer needed.
# All charts are now handled by deserializing JSON stored in history.

@st.fragment
def render_chat_interface():
    """Renders the chat history and input, handling interactions within a fragment."""
    assistant: Optional[BaseFunctionCallingAssistant] = st.session_state.get("assistant")

    # Ensure assistant is initialized if keys/data are present
    if assistant is None:
        # Check prerequisites before attempting initialization
        if st.session_state.openai_api_key and st.session_state.asana_base_client and isinstance(st.session_state.task_df, pd.DataFrame):
            try:
                st.session_state.assistant = BaseFunctionCallingAssistant(
                    openai_api_key=st.session_state.openai_api_key,
                    asana_api_client=st.session_state.asana_base_client, # Corrected key access
                    task_df=st.session_state.task_df
                )
                assistant = st.session_state.assistant # Update local variable
                logger.info("Function calling assistant initialized successfully within fragment.")
            except Exception as e:
                st.error(f"Failed to initialize AI Assistant within fragment: {e}")
                logger.error(f"Failed to initialize AI Assistant within fragment: {e}", exc_info=True)
                return # Stop rendering if assistant fails to init
        else:
            # Prerequisites still missing, handled by create_function_chat_tab
            # Don't display an error here, the parent function handles the warning.
            return

    # Display chat messages from history
    # History now managed internally by the assistant, but we read from st.session_state for display
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("content"):
                st.markdown(message["content"])

            # --- Modification Start: Render list of visualizations ---
            # Check for the 'visualizations' list in the message
            if "visualizations" in message and isinstance(message["visualizations"], list):
                for viz_data in message["visualizations"]:
                    if isinstance(viz_data, dict) and viz_data.get("type") == "plotly":
                        try:
                            fig_json = viz_data.get("data")
                            if fig_json:
                                # Deserialize the JSON string back into a Plotly Figure
                                fig = go.Figure(json.loads(fig_json))
                                st.plotly_chart(fig, use_container_width=True)
                                logger.debug("Successfully rendered a chart from the visualizations list.")
                            else:
                                logger.warning("Visualization type 'plotly' found in history list but 'data' field is missing or empty.")
                                st.warning("Could not render a previous visualization (missing data).")
                        except json.JSONDecodeError:
                             logger.error("Error decoding historical chart JSON from list.")
                             st.warning("Could not render a previous visualization (invalid format).")
                        except Exception as e:
                            logger.error(f"Error rendering historical chart from list: {e}", exc_info=True)
                            st.warning("Could not render a previous visualization.")
                    else:
                        logger.warning(f"Skipping invalid visualization item in list: {viz_data}")
            # --- Modification End ---

# Removed chat input and interaction logic from fragment.
# Fragment is now only responsible for displaying history.


def create_function_chat_tab():
    """Creates the content for the Advanced Chat tab."""
    st.header("🤖 Asana AI Assistant")
    st.caption("Ask questions about your projects, tasks, and resources.")

    # Check for necessary API keys and data before rendering the chat interface
    if not st.session_state.get("openai_api_key"):
        st.warning("Please enter your OpenAI API Key in the sidebar to enable the AI Assistant.")
        return
    # Check for the base client specifically
    if not st.session_state.get("asana_base_client"):
         st.warning("Asana client not initialized. Please ensure Asana API Key and Portfolio GID are set in the sidebar.")
         return
    if not isinstance(st.session_state.get("task_df"), pd.DataFrame) or st.session_state.task_df.empty:
         st.warning("Asana task data not loaded or is empty. Please ensure Asana API Key and Portfolio GID are set and data has been fetched.")
         return

    # Render the chat interface using the fragment
    render_chat_interface()

    # Chat input and interaction logic - moved outside the fragment
    assistant: Optional[BaseFunctionCallingAssistant] = st.session_state.get("assistant")

    # Add a processing flag to prevent re-running assistant on reruns not triggered by new input
    if 'processing_prompt' not in st.session_state:
        st.session_state.processing_prompt = False

    if prompt := st.chat_input("Ask about your Asana projects..."):
        if assistant is None:
            st.warning("AI Assistant is not ready. Please check configuration in the sidebar.")
        else:
            # Add user message to state, set flag, and rerun for immediate display
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.processing_prompt = True # Flag that we need to process this
            st.rerun() # Rerun to show the user message before processing

    # Check if we need to process a prompt (flag set in the block above)
    if st.session_state.processing_prompt:
        # Reset the flag immediately
        st.session_state.processing_prompt = False

        if assistant and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            last_prompt = st.session_state.messages[-1]["content"]

            # Display thinking spinner and placeholders while processing
            # Use st.empty() outside chat_message for better control during reruns
            status_placeholder = st.empty()
            status_placeholder.markdown("Thinking...") # Initial placeholder text

            final_content = None
            final_viz_json = None # Changed variable name

            try:
                # Run the assistant logic (handles history internally, calls LLM, tools)
                assistant.run_assistant(last_prompt)

                # After run_assistant completes, check memory for chart data
                # and get the last response text
                final_content = assistant.get_last_response()

                # --- Modification Start: Handle multiple charts ---
                # Check memory for the list of chart JSONs
                final_visualizations = [] # Initialize list to hold visualization dicts
                if "charts_json_list" in assistant.memory:
                    charts_list = assistant.memory.pop("charts_json_list", [])
                    if isinstance(charts_list, list):
                        logger.info(f"Retrieved {len(charts_list)} chart(s) from 'charts_json_list' in memory.")
                        for chart_json in charts_list:
                            if chart_json:
                                final_visualizations.append({"type": "plotly", "data": chart_json})
                            else:
                                logger.warning("Found an empty item in charts_json_list.")
                    else:
                        logger.warning("'charts_json_list' in memory was not a list.")
                # --- Modification End ---


                # Prepare the final message for session state
                final_assistant_message_content = final_content or "Processing complete."
                final_assistant_message = {
                    "role": "assistant",
                    "content": final_assistant_message_content
                }
                # --- Modification Start: Attach list of visualizations ---
                if final_visualizations:
                    # Store the list of visualization dicts
                    final_assistant_message["visualizations"] = final_visualizations # Note the 's'
                # --- Modification End ---

                # Append the complete final message to the display history
                st.session_state.messages.append(final_assistant_message)
                # Updated log message to reflect multiple visualizations potentially
                logger.debug(f"Appended final assistant message to st.session_state.messages: Role={final_assistant_message['role']}, Content={'<content present>' if final_assistant_message.get('content') else '<no content>'}, Viz Count={len(final_assistant_message.get('visualizations', []))}")


                # Clear the thinking message
                status_placeholder.empty()

                # Trigger one final rerun to render the complete history including the new assistant message
                st.rerun()


            except Exception as e:
                logger.error(f"Error during assistant run or response handling: {e}", exc_info=True)
                error_msg = f"An error occurred while processing your request: {e}"
                status_placeholder.error(error_msg) # Show error prominently
                # Add error message to history
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                # No rerun here, let the error message persist until next user input

    # Add a button to clear chat history outside the fragment
    if st.button("Clear Chat History"):
        reset_function_chat()
        st.rerun()