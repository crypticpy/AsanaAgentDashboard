"""
Team Member Metrics Component for Resource Allocation Page.

This module provides visualizations and metrics for individual team members,
including task completion rates, project allocation, and performance metrics.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime, timedelta
from streamlit_extras.metric_cards import style_metric_cards

def create_team_member_metrics(df: pd.DataFrame) -> None:
    """
    Create team member metrics and visualizations.
    
    Args:
        df: DataFrame with task data
    """
    st.markdown("### Team Member Performance")
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Create team member summary metrics
    create_team_member_summary(df)
    
    # Create team member task distribution
    create_team_member_task_distribution(df)
    
    # Create team member project allocation
    create_team_member_project_allocation(df)

def create_team_member_summary(df: pd.DataFrame) -> None:
    """
    Create summary metrics for team members.
    
    Args:
        df: DataFrame with task data
    """
    # Get team member filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_team_member = filters.get("team_member", "All Team Members")
    
    # Calculate metrics
    total_team_members = df["assignee"].nunique()
    total_tasks = len(df)
    completed_tasks = df[df["status"] == "Completed"].shape[0]
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Calculate average tasks per team member
    avg_tasks_per_member = total_tasks / total_team_members if total_team_members > 0 else 0
    
    # Create metrics row
    if selected_team_member == "All Team Members":
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Team Members",
                value=total_team_members,
                delta=None
            )
        
        with col2:
            st.metric(
                label="Total Tasks",
                value=total_tasks,
                delta=None
            )
        
        with col3:
            st.metric(
                label="Completion Rate",
                value=f"{completion_rate:.1f}%",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Avg Tasks/Member",
                value=f"{avg_tasks_per_member:.1f}",
                delta=None
            )
    else:
        # Filter for the selected team member
        member_df = df[df["assignee"] == selected_team_member]
        
        # Calculate metrics for the selected team member
        member_total_tasks = len(member_df)
        member_completed_tasks = member_df[member_df["status"] == "Completed"].shape[0]
        member_completion_rate = (member_completed_tasks / member_total_tasks) * 100 if member_total_tasks > 0 else 0
        
        # Calculate team average for comparison
        team_completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Calculate delta (difference from team average)
        completion_delta = member_completion_rate - team_completion_rate
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Total Tasks",
                value=member_total_tasks,
                delta=None
            )
        
        with col2:
            st.metric(
                label="Completed Tasks",
                value=member_completed_tasks,
                delta=None
            )
        
        with col3:
            st.metric(
                label="Completion Rate",
                value=f"{member_completion_rate:.1f}%",
                delta=f"{completion_delta:.1f}%" if completion_delta != 0 else None,
                delta_color="normal"
            )
    
    # Apply styling
    style_metric_cards()

def create_team_member_task_distribution(df: pd.DataFrame) -> None:
    """
    Create task distribution visualization for team members.
    
    Args:
        df: DataFrame with task data
    """
    # Get team member counts
    team_member_counts = df.groupby(["assignee", "status"]).size().reset_index(name="count")
    
    # Create visualization
    if not team_member_counts.empty:
        fig = px.bar(
            team_member_counts,
            x="assignee",
            y="count",
            color="status",
            title="Task Distribution by Team Member",
            labels={"assignee": "Team Member", "count": "Number of Tasks", "status": "Status"},
            height=400,
            color_discrete_map={"Completed": "#4CAF50", "In Progress": "#FFC107"}
        )
        
        # Update layout
        fig.update_layout(
            xaxis_title="Team Member",
            yaxis_title="Number of Tasks",
            legend_title="Task Status",
            barmode="stack"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No task distribution data available.")

def create_team_member_project_allocation(df: pd.DataFrame) -> None:
    """
    Create project allocation visualization for team members.
    
    Args:
        df: DataFrame with task data
    """
    # Get team member filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_team_member = filters.get("team_member", "All Team Members")
    
    # If a specific team member is selected, show their project allocation
    if selected_team_member != "All Team Members":
        # Filter for the selected team member
        member_df = df[df["assignee"] == selected_team_member]
        
        # Get project counts
        project_counts = member_df.groupby(["project", "status"]).size().reset_index(name="count")
        
        # Create visualization
        if not project_counts.empty:
            fig = px.pie(
                project_counts,
                values="count",
                names="project",
                title=f"Project Allocation for {selected_team_member}",
                height=400
            )
            
            # Update layout
            fig.update_layout(
                legend_title="Project"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No project allocation data available for {selected_team_member}.")
    else:
        # Show project allocation for all team members
        # Count projects per team member
        projects_per_member = df.groupby("assignee")["project"].nunique().reset_index()
        projects_per_member.columns = ["Team Member", "Number of Projects"]
        
        # Sort by number of projects
        projects_per_member = projects_per_member.sort_values("Number of Projects", ascending=False)
        
        # Create visualization
        if not projects_per_member.empty:
            fig = px.bar(
                projects_per_member,
                x="Team Member",
                y="Number of Projects",
                title="Project Allocation by Team Member",
                height=400,
                color="Number of Projects",
                color_continuous_scale="Viridis"
            )
            
            # Update layout
            fig.update_layout(
                xaxis_title="Team Member",
                yaxis_title="Number of Projects"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No project allocation data available.") 