"""
Advanced Chat Page - Asana Portfolio Dashboard
"""
import streamlit as st

# Set page config FIRST
st.set_page_config(
    page_title="Advanced Chat - Asana Dashboard",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"  # Keep sidebar consistent
)

# Import necessary components and utilities AFTER page config
from src.components.function_chat import create_function_chat_tab, initialize_function_chat_state
from src.styles.custom import apply_custom_css, apply_theme

# Apply custom theme and CSS AFTER page config
apply_theme()
apply_custom_css()


def chat_page():
    """
    Renders the Advanced Chat page.
    """
    st.title("💬 Advanced Chat Assistant")
    st.markdown("Interact with the AI assistant to query Asana data, generate reports, and more.")
    st.markdown("---")

    # Initialize chat state if not already done (e.g., if user lands directly here)
    initialize_function_chat_state()

    # Check if necessary data and API keys are loaded from the main app
    required_state = [
        "task_df", 
        "project_estimates", 
        "project_details", 
        "api_instances", 
        "openai_api_key",
        "asana_base_client" # Added base client check
    ]
    
    missing_state = [key for key in required_state if key not in st.session_state or st.session_state[key] is None]

    if missing_state:
        st.warning(f"""
        The following required data is missing: {', '.join(missing_state)}. 
        Please visit the main **Overview** page first to load the Asana data and configure API keys.
        """)
        st.stop()
        
    if not st.session_state.get("openai_api_key"):
        st.warning("OpenAI API Key is missing. Please configure it on the main page sidebar.")
        st.stop()

    # Render the chat interface component
    create_function_chat_tab()

if __name__ == "__main__":
    chat_page()