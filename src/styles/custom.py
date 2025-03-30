"""
Custom styling for the Asana Portfolio Dashboard.
"""
import streamlit as st

def apply_theme():
    """Apply a custom theme to the Streamlit app."""
    # Set the theme
    st.markdown("""
        <style>
        :root {
            --primary-color: #FF5263;
            --background-color: #f5f7f9;
            --secondary-background-color: #ffffff;
            --text-color: #31333F;
            --font: "Inter", sans-serif;
        }
        </style>
    """, unsafe_allow_html=True)

def apply_custom_css():
    """Apply custom CSS to the Streamlit app."""
    # Custom CSS
    st.markdown("""
        <style>
        /* General styling */
        .dashboard-header {
            padding: 1rem 0;
            margin-bottom: 2rem;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 4px 4px 0 0;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #FF5263 !important;
            color: white !important;
        }
        
        /* Project card styling */
        .project-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .project-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .project-card h3 {
            margin-top: 0;
            color: #31333F;
        }
        
        .project-card .metrics {
            display: flex;
            justify-content: space-between;
            margin-top: 1rem;
        }
        
        .project-card .metric {
            text-align: center;
        }
        
        .project-card .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #FF5263;
        }
        
        .project-card .metric-label {
            font-size: 0.8rem;
            color: #6B7280;
        }
        
        /* Status badge styling */
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status-on-track {
            background-color: #10B981;
            color: white;
        }
        
        .status-at-risk {
            background-color: #F59E0B;
            color: white;
        }
        
        .status-behind {
            background-color: #EF4444;
            color: white;
        }
        
        .status-completed {
            background-color: #6366F1;
            color: white;
        }
        
        .status-not-started {
            background-color: #9CA3AF;
            color: white;
        }
        
        /* Metric card styling */
        .metric-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            text-align: center;
        }
        
        .metric-card h3 {
            margin-top: 0;
            color: #6B7280;
            font-size: 1rem;
            font-weight: 500;
        }
        
        .metric-card .value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #31333F;
            margin: 0.5rem 0;
        }
        
        .metric-card .trend {
            font-size: 0.875rem;
            color: #10B981;
        }
        
        .metric-card .trend.negative {
            color: #EF4444;
        }
        
        /* Chat interface styling */
        .chat-container {
            border-radius: 10px;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            padding: 1rem;
            margin-bottom: 1rem;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .chat-message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border-radius: 8px;
        }
        
        .chat-message.user {
            background-color: #F3F4F6;
            margin-left: 2rem;
        }
        
        .chat-message.assistant {
            background-color: #EFF6FF;
            margin-right: 2rem;
        }
        
        .chat-input {
            display: flex;
            margin-top: 1rem;
        }
        
        .chat-input input {
            flex-grow: 1;
            padding: 0.75rem;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            margin-right: 0.5rem;
        }
        
        .chat-input button {
            background-color: #FF5263;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            cursor: pointer;
        }
        
        /* Fix for Streamlit chat message styling */
        [data-testid="stChatMessage"] {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        
        /* Prevent page reloads on form submission */
        form {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        
        /* Ensure chat messages display in correct order */
        .stChatMessageContent {
            display: flex;
            flex-direction: column;
        }
        
        /* Ensure chat input doesn't cause page reloads */
        .stTextInput input {
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
        }
        
        /* Ensure chat container doesn't overflow */
        [data-testid="stVerticalBlock"] {
            overflow-y: visible !important;
        }
        
        /* Ensure tabs don't reload the page */
        [data-baseweb="tab-panel"] {
            overflow: visible !important;
        }
        
        /* Ensure chat messages are displayed in the correct order */
        [data-testid="stChatMessageContainer"] {
            display: flex;
            flex-direction: column;
        }
        
        /* Ensure chat input is always visible */
        [data-testid="stChatInput"] {
            position: sticky;
            bottom: 0;
            background-color: white;
            padding: 1rem 0;
            z-index: 100;
        }
        
        /* Ensure visualizations are displayed correctly */
        .js-plotly-plot {
            margin-top: 1rem;
        }
        
        /* Style radio buttons as tabs */
        div.row-widget.stRadio > div {
            display: flex;
            flex-direction: row;
            justify-content: center;
            gap: 8px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        div.row-widget.stRadio > div > label {
            background-color: #f8f9fa;
            border-radius: 4px 4px 0 0;
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid #e0e0e0;
            border-bottom: none;
            margin-bottom: -1px;
            transition: all 0.2s ease;
        }
        
        div.row-widget.stRadio > div > label:hover {
            background-color: #e9ecef;
        }
        
        div.row-widget.stRadio > div > label[data-baseweb="radio"] > div {
            display: none;
        }
        
        div.row-widget.stRadio > div > label[aria-checked="true"] {
            background-color: #FF5263 !important;
            color: white !important;
            border-color: #FF5263;
            font-weight: bold;
        }
        
        /* Hide the radio button label */
        div.row-widget.stRadio > label {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True) 