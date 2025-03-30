"""
Asana Portfolio Dashboard - Main Application
"""
import streamlit as st

# Set page config first
st.set_page_config(
    page_title="Asana Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import asana
from typing import Dict, Any, List, Optional
import plotly.graph_objects as go
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asana_dashboard")

# Import custom modules
from src.styles.custom import apply_custom_css, apply_theme
from src.components.sidebar import create_sidebar
from src.components.project_card import create_project_cards_grid
from src.components.dashboard_metrics import create_summary_metrics, create_recent_activity_metrics, create_top_resources_metrics
# Removed: from src.components.function_chat import create_function_chat_tab (UI moved to pages/)
from src.components.function_chat import initialize_function_chat_state, reset_function_chat # Keep state init/reset
from src.utils.asana_api import setup_asana_client, initialize_api_instances, get_portfolio_projects, get_tasks, process_tasks
from src.utils.data_processing import estimate_project_completion, get_project_details
from src.utils.visualizations import (
    create_interactive_timeline, create_velocity_chart, create_burndown_chart,
    create_resource_allocation_chart, create_task_status_distribution, create_project_progress_bars
)
# Import resource allocation page
from src.pages.resource_allocation_page import create_resource_allocation_page
# Import new fiscal overview component
from src.components.fiscal_overview import create_fiscal_overview

# Apply custom theme and CSS
apply_theme()
apply_custom_css()

def main():
    """
    Main function to run the Streamlit app.
    """
    # Initialize chat state
    initialize_function_chat_state()
    
    # Create sidebar and get configuration
    api_token, portfolio_gid, team_gid, openai_api_key = create_sidebar()
    
    # Store OpenAI API key in session state for chat assistant to use
    st.session_state.openai_api_key = openai_api_key

    # Dashboard header
    st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
    st.title("Asana Portfolio Dashboard")
    st.markdown("A comprehensive view of your Asana projects and tasks")
    st.markdown('</div>', unsafe_allow_html=True)

    # Display notice about required keys
    with st.expander("Required API Keys and IDs", expanded=not api_token or not portfolio_gid or not openai_api_key):
        st.markdown("""
        ### Required API Keys and IDs
        
        To use all features of this dashboard, you'll need to provide the following:
        
        1. **Asana API Token** - Required for accessing your Asana data
           - Get it from [Asana Developer Console](https://app.asana.com/0/developer-console)
           - Current status: {asana_status}
        
        2. **Portfolio GID** - Required for accessing your Asana portfolio
           - Find it in the URL when viewing your portfolio in Asana
           - Current status: {portfolio_status}
        
        3. **Team GID** - Optional, used for team-specific features
           - Find it in the URL when viewing your team in Asana
           - Current status: {team_status}
        
        4. **OpenAI API Key** - Required for AI assistant features
           - Get it from [OpenAI API Keys](https://platform.openai.com/api-keys)
           - Current status: {openai_status}
        
        Enter these in the sidebar and click "Save Configuration" to get started.
        """.format(
            asana_status="✅ Provided" if api_token else "❌ Missing",
            portfolio_status="✅ Provided" if portfolio_gid else "❌ Missing",
            team_status="✅ Provided" if team_gid else "⚠️ Optional",
            openai_status="✅ Provided" if openai_api_key else "❌ Missing (required for AI features)"
        ))

    # Check if API token and portfolio GID are provided
    if not api_token or not portfolio_gid:
        st.warning("Please enter your Asana API Token and Portfolio GID in the sidebar to get started.")
        st.stop()

    # Set up Asana client
    client = setup_asana_client(api_token)
    api_instances = initialize_api_instances(client)

    # Store base client and API instances in session state for chat assistant to use
    st.session_state.asana_base_client = client # Store the base client
    st.session_state.api_instances = api_instances

    # Get data
    with st.spinner("Fetching data from Asana..."):
        try:
            # Get projects
            projects = get_portfolio_projects(api_instances["_portfolios_api"], portfolio_gid)

            if not projects:
                st.error("No projects found in the portfolio. Please check your Portfolio GID.")
                st.stop()

            # Get tasks for each project
            all_tasks = []
            for project in projects:
                if project_tasks := get_tasks(
                    api_instances["_tasks_api"], project["gid"]
                ):
                    processed_tasks = process_tasks(project_tasks, project["name"], project["gid"])
                    all_tasks.extend(processed_tasks)

            # Create DataFrame
            df = pd.DataFrame(all_tasks)

            # Convert date columns to datetime
            date_columns = ['due_date', 'created_at', 'completed_at']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], utc=True)

            # Estimate project completion
            project_estimates = estimate_project_completion(df)

            # Get project details
            project_details = []
            for _, project in project_estimates.iterrows():
                details = get_project_details(
                    project, 
                    api_instances["_projects_api"], 
                    api_instances["_portfolios_api"], 
                    portfolio_gid, 
                    df
                )
                project_details.append(details)
                
            # Store data in session state for chat component to access
            st.session_state.task_df = df
            st.session_state.project_estimates = project_estimates
            st.session_state.project_details = project_details
            
            logger.info("Data loaded successfully")

        except Exception as e:
            st.error(f"Error fetching data from Asana: {e}")
            logger.error(f"Error fetching data from Asana: {e}", exc_info=True)
            st.stop()

    # Create dashboard
    create_dashboard(df, project_estimates, project_details)

def create_dashboard(df: pd.DataFrame, project_estimates: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create the dashboard with tabs for different views.
    
    Args:
        df: DataFrame with task data
        project_estimates: DataFrame with project completion estimates
        project_details: List of detailed project information
    """
    # Create tabs - Removed "Advanced Chat" as it's now a separate page
    tab_names = ["Overview", "Projects", "Tasks", "Resource Allocation"]

    # Use session state to keep track of the current tab
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = 0
    
    # Create tab buttons with custom styling
    cols = st.columns(len(tab_names))
    for i, tab_name in enumerate(tab_names):
        # Determine if this tab is active
        is_active = st.session_state.current_tab == i
        
        # Create button with appropriate styling
        button_style = "primary" if is_active else "secondary"
        if cols[i].button(tab_name, key=f"tab_{i}", type=button_style, use_container_width=True):
            st.session_state.current_tab = i
            # Rerun always needed to update the active tab highlight
            st.rerun()
    
    # Add separator
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Tab 1: Overview
    if st.session_state.current_tab == 0:
        # Use the new fiscal overview component instead of the old overview
        create_fiscal_overview(df, project_estimates)
    
    # Tab 2: Projects
    elif st.session_state.current_tab == 1:
        # Project filters
        st.markdown("### Project Filters")
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range filter
            date_range = st.date_input(
                "Date Range",
                value=(
                    df['created_at'].min().date() if not df.empty and 'created_at' in df else None,
                    df['due_date'].max().date() if not df.empty and 'due_date' in df else None
                ),
                key="project_date_range"
            )
        
        with col2:
            # Status filter
            status_options = ["All", "On Track", "At Risk", "Behind"]
            status_filter = st.selectbox(
                "Status",
                status_options,
                key="project_status_filter"
            )
        
        # Filter projects based on selected filters
        filtered_projects = project_details.copy()
        
        # Apply status filter
        if status_filter != "All":
            filtered_projects = [p for p in filtered_projects if p.get('status') == status_filter]
        
        # Show project cards
        if filtered_projects:
            create_project_cards_grid(filtered_projects, df)
        else:
            st.info("No projects match the selected filters")
        
        # Show project timeline
        st.markdown("### Project Timeline")
        timeline_fig = create_interactive_timeline(project_estimates)
        st.plotly_chart(timeline_fig, use_container_width=True)
        
        # Show project progress
        st.markdown("### Project Progress")
        progress_fig = create_project_progress_bars(project_details)
        st.plotly_chart(progress_fig, use_container_width=True)
    
    # Tab 3: Tasks
    elif st.session_state.current_tab == 2:
        # Task filters
        st.markdown("### Task Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Project filter
            project_options = ["All"] + sorted(df['project'].unique().tolist())
            selected_project = st.selectbox(
                "Project",
                project_options,
                key="task_project_filter"
            )
        
        with col2:
            # Status filter
            status_options = ["All"] + sorted(df['status'].unique().tolist())
            selected_status = st.selectbox(
                "Status",
                status_options,
                key="task_status_filter"
            )
        
        with col3:
            # Assignee filter
            assignee_options = ["All"] + sorted(df['assignee'].unique().tolist())
            selected_assignee = st.selectbox(
                "Assignee",
                assignee_options,
                key="task_assignee_filter"
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_project != "All":
            filtered_df = filtered_df[filtered_df['project'] == selected_project]
        
        if selected_status != "All":
            filtered_df = filtered_df[filtered_df['status'] == selected_status]
        
        if selected_assignee != "All":
            filtered_df = filtered_df[filtered_df['assignee'] == selected_assignee]
        
        # Display filtered tasks
        if not filtered_df.empty:
            # Show task status distribution
            st.markdown("### Task Status Distribution")
            status_fig = create_task_status_distribution(filtered_df)
            st.plotly_chart(status_fig, use_container_width=True)
            
            # Show velocity chart
            st.markdown("### Velocity Chart")
            velocity_fig = create_velocity_chart(filtered_df)
            st.plotly_chart(velocity_fig, use_container_width=True)
            
            # Show burndown chart
            st.markdown("### Burndown Chart")
            burndown_fig = create_burndown_chart(filtered_df)
            st.plotly_chart(burndown_fig, use_container_width=True)
            
            # Show task table
            st.markdown("### Task List")
            
            # Select columns to display
            display_cols = ['name', 'project', 'status', 'assignee', 'due_date']
            
            # Format date columns
            display_df = filtered_df[display_cols].copy()
            if 'due_date' in display_df.columns:
                display_df['due_date'] = display_df['due_date'].dt.strftime('%Y-%m-%d')
            
            # Display the table
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No tasks match the selected filters")
    
    # Tab 4: Resource Allocation
    elif st.session_state.current_tab == 3:
        create_resource_allocation_page(df, project_details)
    
    # Tab 5: Advanced Chat (Removed - now in pages/1_💬_Advanced_Chat.py)
    # elif st.session_state.current_tab == 4:
    #     create_function_chat_tab()

if __name__ == "__main__":
    main()