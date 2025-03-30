"""
Resource Allocation Page for Asana Portfolio Dashboard.

This module provides the main interface for the resource allocation page,
which displays team member performance, project allocation, and resource utilization.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

# Import resource allocation components
from src.pages.resource_components.team_member_metrics import create_team_member_metrics
from src.pages.resource_components.project_allocation import create_project_allocation_metrics
from src.pages.resource_components.performance_trends import create_performance_trends
from src.pages.resource_components.resource_utilization import create_resource_utilization_metrics

def create_resource_allocation_page(
    df: pd.DataFrame, 
    project_details: List[Dict[str, Any]]
) -> None:
    """
    Create the resource allocation page with all components.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    # Page header
    st.markdown("# Resource Allocation")
    st.markdown("Analyze team member performance and project resource allocation")
    
    # Create filters
    create_resource_filters(df)
    
    # Apply filters to data
    filtered_df = apply_filters(df)
    
    # Create main sections
    col1, col2 = st.columns(2)
    
    with col1:
        # Team member metrics
        create_team_member_metrics(filtered_df)
    
    with col2:
        # Resource utilization metrics
        create_resource_utilization_metrics(filtered_df, project_details)
    
    # Project allocation metrics
    create_project_allocation_metrics(filtered_df, project_details)
    
    # Performance trends
    create_performance_trends(filtered_df)

def create_resource_filters(df: pd.DataFrame) -> None:
    """
    Create filters for the resource allocation page.
    
    Args:
        df: DataFrame with task data
    """
    st.markdown("### Filters")
    
    # Create filter columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Time period filter
        time_periods = ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year", "All Time"]
        selected_time_period = st.selectbox(
            "Time Period", 
            time_periods,
            key="resource_time_period"
        )
    
    with col2:
        # Team member filter
        team_members = ["All Team Members"] + sorted(df["assignee"].unique().tolist())
        selected_team_member = st.selectbox(
            "Team Member",
            team_members,
            key="resource_team_member"
        )
    
    with col3:
        # Project filter
        projects = ["All Projects"] + sorted(df["project"].unique().tolist())
        selected_project = st.selectbox(
            "Project",
            projects,
            key="resource_project"
        )
    
    # Store filter selections in session state
    st.session_state.resource_filters = {
        "time_period": selected_time_period,
        "team_member": selected_team_member,
        "project": selected_project
    }

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply filters to the data.
    
    Args:
        df: DataFrame with task data
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    # Get filter values from session state
    filters = st.session_state.get("resource_filters", {})
    
    # Apply time period filter
    if time_period := filters.get("time_period"):
        if time_period != "All Time":
            # Calculate the start date based on the selected time period
            now = pd.Timestamp.now(tz="UTC")
            
            if time_period == "Last 30 Days":
                start_date = now - pd.Timedelta(days=30)
            elif time_period == "Last 90 Days":
                start_date = now - pd.Timedelta(days=90)
            elif time_period == "Last 6 Months":
                start_date = now - pd.Timedelta(days=180)
            elif time_period == "Last Year":
                start_date = now - pd.Timedelta(days=365)
            
            # Filter tasks created within the time period
            filtered_df = filtered_df[filtered_df["created_at"] >= start_date]
    
    # Apply team member filter
    if team_member := filters.get("team_member"):
        if team_member != "All Team Members":
            filtered_df = filtered_df[filtered_df["assignee"] == team_member]
    
    # Apply project filter
    if project := filters.get("project"):
        if project != "All Projects":
            filtered_df = filtered_df[filtered_df["project"] == project]
    
    return filtered_df 