"""
Resource Utilization Component for Resource Allocation Page.

This module provides visualizations and metrics for resource utilization across projects,
including workload distribution, capacity analysis, and allocation efficiency.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime, timedelta
from streamlit_extras.metric_cards import style_metric_cards

def create_resource_utilization_metrics(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create resource utilization metrics and visualizations.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    st.markdown("### Resource Utilization")
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Create resource utilization summary
    create_resource_utilization_summary(df)
    
    # Create workload distribution visualization
    create_workload_distribution(df)

def create_resource_utilization_summary(df: pd.DataFrame) -> None:
    """
    Create summary metrics for resource utilization.
    
    Args:
        df: DataFrame with task data
    """
    # Calculate metrics
    active_tasks = df[df["status"] != "Completed"]
    total_resources = df["assignee"].nunique()
    
    # Calculate average tasks per resource
    avg_tasks_per_resource = len(active_tasks) / total_resources if total_resources > 0 else 0
    
    # Calculate resource utilization percentage (assuming max capacity is 10 tasks per resource)
    max_capacity = 10
    utilization_percentage = (avg_tasks_per_resource / max_capacity) * 100
    utilization_percentage = min(utilization_percentage, 100)  # Cap at 100%
    
    # Calculate workload distribution (standard deviation of tasks per resource)
    tasks_per_resource = active_tasks["assignee"].value_counts()
    workload_std = tasks_per_resource.std() if len(tasks_per_resource) > 1 else 0
    
    # Calculate allocation efficiency (lower std deviation is better)
    max_std = 5  # Maximum expected standard deviation
    allocation_efficiency = max(0, 100 - (workload_std / max_std * 100))
    
    # Create metrics row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Resource Utilization",
            value=f"{utilization_percentage:.1f}%",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Avg Tasks/Resource",
            value=f"{avg_tasks_per_resource:.1f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Allocation Efficiency",
            value=f"{allocation_efficiency:.1f}%",
            delta=None
        )
    
    # Apply styling
    style_metric_cards()
    
    # Add explanation
    with st.expander("Understanding Resource Utilization Metrics"):
        st.markdown("""
        **Resource Utilization Metrics:**
        
        - **Resource Utilization**: Percentage of total resource capacity being used, based on active tasks.
          Assumes a maximum capacity of 10 active tasks per resource.
        
        - **Avg Tasks/Resource**: Average number of active tasks assigned to each team member.
        
        - **Allocation Efficiency**: Measures how evenly tasks are distributed among team members.
          Higher values indicate more balanced workloads.
        """)

def create_workload_distribution(df: pd.DataFrame) -> None:
    """
    Create workload distribution visualization.
    
    Args:
        df: DataFrame with task data
    """
    # Filter for active tasks
    active_tasks = df[df["status"] != "Completed"]
    
    # Get tasks per resource
    tasks_per_resource = active_tasks.groupby("assignee").size().reset_index(name="count")
    tasks_per_resource.columns = ["Team Member", "Active Tasks"]
    
    # Sort by task count
    tasks_per_resource = tasks_per_resource.sort_values("Active Tasks", ascending=False)
    
    # Create visualization
    if not tasks_per_resource.empty:
        # Calculate average
        avg_tasks = tasks_per_resource["Active Tasks"].mean()
        
        # Create figure
        fig = go.Figure()
        
        # Add bar chart
        fig.add_trace(
            go.Bar(
                x=tasks_per_resource["Team Member"],
                y=tasks_per_resource["Active Tasks"],
                marker_color="lightblue",
                name="Active Tasks"
            )
        )
        
        # Add average line
        fig.add_trace(
            go.Scatter(
                x=tasks_per_resource["Team Member"],
                y=[avg_tasks] * len(tasks_per_resource),
                mode="lines",
                line=dict(color="red", width=2, dash="dash"),
                name="Team Average"
            )
        )
        
        # Update layout
        fig.update_layout(
            title="Workload Distribution by Team Member",
            xaxis_title="Team Member",
            yaxis_title="Number of Active Tasks",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add workload analysis
        create_workload_analysis(tasks_per_resource, avg_tasks)
    else:
        st.info("No workload distribution data available.")

def create_workload_analysis(tasks_per_resource: pd.DataFrame, avg_tasks: float) -> None:
    """
    Create workload analysis based on task distribution.
    
    Args:
        tasks_per_resource: DataFrame with tasks per resource
        avg_tasks: Average tasks per resource
    """
    # Calculate overloaded and underutilized resources
    overloaded = tasks_per_resource[tasks_per_resource["Active Tasks"] > avg_tasks * 1.5]
    underutilized = tasks_per_resource[tasks_per_resource["Active Tasks"] < avg_tasks * 0.5]
    
    # Create analysis
    st.markdown("#### Workload Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Potentially Overloaded Team Members:**")
        
        if not overloaded.empty:
            for _, row in overloaded.iterrows():
                st.markdown(f"- **{row['Team Member']}**: {row['Active Tasks']} tasks (team avg: {avg_tasks:.1f})")
        else:
            st.markdown("No team members appear to be overloaded.")
    
    with col2:
        st.markdown("**Potentially Underutilized Team Members:**")
        
        if not underutilized.empty:
            for _, row in underutilized.iterrows():
                st.markdown(f"- **{row['Team Member']}**: {row['Active Tasks']} tasks (team avg: {avg_tasks:.1f})")
        else:
            st.markdown("No team members appear to be underutilized.") 