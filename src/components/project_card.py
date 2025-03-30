"""
Project card component for the Asana Portfolio Dashboard.
"""
import streamlit as st
from typing import Dict, Any
import pandas as pd
from datetime import datetime
import hydralit_components as hc
from streamlit_card import card

def create_project_card(project: Dict[str, Any], df: pd.DataFrame) -> None:
    """
    Create a project card with improved UI.
    
    Args:
        project: Project details
        df: DataFrame of tasks
    """
    # Get completion percentage from project details or calculate it
    total_tasks = project['total_tasks']
    completed_tasks = project['completed_tasks']
    completion_percentage = project.get('completion_percentage')
    if completion_percentage is None:
        completion_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Determine status color and text
    status = project.get('status', 'On Track')
    if status == "Behind":
        status_color = "#F44336"  # Red
        status_text = "Behind Schedule"
    elif status == "At Risk":
        status_color = "#FF9800"  # Orange
        status_text = "At Risk"
    else:
        status_color = "#4CAF50"  # Green
        status_text = "On Track"
    
    # Format dates
    est_completion = project['estimated_completion_date']
    if est_completion and not pd.isna(est_completion):
        est_completion_str = est_completion.strftime('%Y-%m-%d')
        
        # Calculate days until completion
        today = pd.Timestamp.now(tz='UTC')
        days_until = (est_completion - today).days
        if days_until >= 0:
            days_until_str = f"{days_until} days remaining"
        else:
            days_until_str = "Completed"
    else:
        est_completion_str = "Unknown"
        days_until_str = ""
    
    # Get velocity metrics if available
    velocity_metrics = project.get('velocity_metrics', {})
    velocity = velocity_metrics.get('velocity')
    velocity_str = f"{velocity:.2f} tasks/day" if velocity is not None else "Unknown"
    
    # Create card using hydralit_components
    with st.container():
        # Header with project name and status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {project['name']}")
        with col2:
            st.markdown(
                f"<div style='background-color: {status_color}; color: white; padding: 5px 10px; "
                f"border-radius: 5px; text-align: center; font-weight: bold;'>{status_text}</div>",
                unsafe_allow_html=True
            )
        
        # Project details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Owner**")
            st.markdown(f"{project['owner']}")
            
            st.markdown("**Team Members**")
            st.markdown(f"{project['members_count']}")
        with col2:
            st.markdown("**Est. Completion**")
            st.markdown(f"<span style='font-size: 1.1em; font-weight: bold;'>{est_completion_str}</span>", unsafe_allow_html=True)
            if days_until_str:
                st.markdown(f"<span style='color: {'#4CAF50' if status == 'On Track' else status_color};'>{days_until_str}</span>", unsafe_allow_html=True)
            
            # Display velocity if available
            if velocity is not None:
                st.markdown("**Velocity**")
                st.markdown(velocity_str)
        
        # Progress bar
        st.markdown("**Progress**")
        progress_html = f"""
        <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 20px; margin-bottom: 10px;">
            <div style="width: {min(completion_percentage, 100)}%; background-color: {'#4CAF50' if completion_percentage >= 66 else '#FFC107' if completion_percentage >= 33 else '#F44336'}; 
                 height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: white; font-weight: bold;">
                {completion_percentage:.1f}%
            </div>
        </div>
        """
        st.markdown(progress_html, unsafe_allow_html=True)
        
        # Task metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Total Tasks", total_tasks)
        with col2:
            metric_card("Completed", completed_tasks)
        with col3:
            metric_card("Overdue", project['overdue_tasks'], is_negative=True)
        
        st.markdown("---")

def metric_card(title: str, value: Any, is_negative: bool = False) -> None:
    """
    Create a metric card.
    
    Args:
        title: Metric title
        value: Metric value
        is_negative: Whether the metric is negative (for styling)
    """
    color = "#F44336" if is_negative and value > 0 else "#4CAF50"
    
    st.markdown(
        f"""
        <div style="text-align: center;">
            <div style="font-size: 0.9rem; color: #666;">{title}</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def create_project_cards_grid(projects: list, df: pd.DataFrame) -> None:
    """
    Create a grid of project cards.
    
    Args:
        projects: List of project details
        df: DataFrame of tasks
    """
    # Create rows with 2 cards per row
    for i in range(0, len(projects), 2):
        cols = st.columns(2)
        
        # First card in row
        with cols[0]:
            with st.container(border=True):
                create_project_card(projects[i], df)
        
        # Second card in row (if exists)
        if i + 1 < len(projects):
            with cols[1]:
                with st.container(border=True):
                    create_project_card(projects[i + 1], df) 