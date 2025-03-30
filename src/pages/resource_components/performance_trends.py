"""
Performance Trends Component for Resource Allocation Page.

This module provides visualizations for team member performance trends over time,
including task completion velocity, acceleration/deceleration analysis, and performance benchmarks.
This component now features enhanced team member scorecards with detailed velocity metrics,
allocation trending, and comparative analysis.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from streamlit_extras.metric_cards import style_metric_cards

def create_performance_trends(df: pd.DataFrame) -> None:
    """
    Create performance trend visualizations for team members.
    
    Args:
        df: DataFrame with task data
    """
    st.markdown("### Performance Trends")
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Get team member filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_team_member = filters.get("team_member", "All Team Members")
    
    # Create team member scorecards
    create_team_member_scorecards(df, selected_team_member)
    
    # Add team velocity comparison
    create_team_velocity_comparison(df, selected_team_member)
def create_team_member_scorecards(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create detailed performance scorecards for team members, showing task completion rates,
    project allocation, and trending information.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    
    # Filter data based on selected team member
    if selected_team_member != "All Team Members":
        # Create scorecard for the selected team member
        member_df = df[df["assignee"] == selected_team_member].copy()
        if member_df.empty:
            st.info(f"No task data available for {selected_team_member}.")
            return
        
        create_individual_scorecard(member_df, selected_team_member, df)
    else:
        # Create a tab for each team member (limit to top 5 for performance)
        team_members = df["assignee"].value_counts().head(5).index.tolist()
        
        if not team_members:
            st.info("No team member data available.")
            return
        
        # Create tabs for team members
        tabs = st.tabs(team_members)
        
        # Create scorecard for each team member in their respective tab
        for idx, member in enumerate(team_members):
            with tabs[idx]:
                member_df = df[df["assignee"] == member].copy()
                if not member_df.empty:
                    create_individual_scorecard(member_df, member, df)
                else:
                    st.info(f"No task data available for {member}.")

def create_individual_scorecard(member_df: pd.DataFrame, member_name: str, full_df: pd.DataFrame) -> None:
    """
    Create a performance scorecard for an individual team member.
    
    Args:
        member_df: DataFrame with tasks for this team member
        member_name: Name of the team member
        full_df: Complete DataFrame with all team members for comparison
    """
    # Calculate key metrics
    assigned_tasks = len(member_df)
    completed_tasks = len(member_df[member_df["status"] == "Completed"])
    in_progress_tasks = assigned_tasks - completed_tasks
    completion_rate = (completed_tasks / assigned_tasks) * 100 if assigned_tasks > 0 else 0
    
    # Project allocation
    projects = member_df["project"].unique()
    project_count = len(projects)
    
    # Calculate daily/monthly completion rates
    daily_rates = calculate_completion_rates(member_df, "daily")
    monthly_rates = calculate_completion_rates(member_df, "monthly")
    
    # Calculate team averages for comparison
    team_completion_rate = calculate_team_average(full_df, "completion_rate")
    team_daily_rate = calculate_team_average(full_df, "daily_rate")
    team_monthly_rate = calculate_team_average(full_df, "monthly_rate")
    team_project_count = calculate_team_average(full_df, "project_count")
    
    # Create the scorecard
    st.subheader(f"Performance Scorecard: {member_name}")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Projects Assigned",
            value=project_count,
            delta=f"{project_count - team_project_count:.1f} vs avg" if team_project_count > 0 else None
        )
    
    with col2:
        st.metric(
            label="Total Tasks",
            value=assigned_tasks,
            delta=None
        )
    
    with col3:
        st.metric(
            label="Completed Tasks",
            value=completed_tasks,
            delta=None
        )
    
    with col4:
        delta_value = completion_rate - team_completion_rate if team_completion_rate > 0 else None
        st.metric(
            label="Completion Rate",
            value=f"{completion_rate:.1f}%",
            delta=f"{delta_value:.1f}%" if delta_value is not None else None,
            delta_color="normal"
        )
    
    # Apply styling to the metric cards
    style_metric_cards()
    
    # Velocity metrics
    st.markdown("#### Velocity Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        current_daily_rate = daily_rates.get("current", 0)
        previous_daily_rate = daily_rates.get("previous", 0)
        daily_trend = calculate_trend(current_daily_rate, previous_daily_rate)
        
        st.metric(
            label="Tasks/Day",
            value=f"{current_daily_rate:.2f}",
            delta=f"{daily_trend:.2f}",
            delta_color="normal" if daily_trend >= 0 else "inverse"
        )
    
    with col2:
        current_monthly_rate = monthly_rates.get("current", 0)
        previous_monthly_rate = monthly_rates.get("previous", 0)
        monthly_trend = calculate_trend(current_monthly_rate, previous_monthly_rate)
        
        st.metric(
            label="Tasks/Month",
            value=f"{current_monthly_rate:.1f}",
            delta=f"{monthly_trend:.1f}",
            delta_color="normal" if monthly_trend >= 0 else "inverse"
        )
    
    with col3:
        # Compare to team average
        team_diff = current_daily_rate - team_daily_rate if team_daily_rate > 0 else 0
        st.metric(
            label="vs. Team Average",
            value=f"{team_diff:.2f} tasks/day",
            delta=f"{(team_diff / team_daily_rate) * 100:.1f}%" if team_daily_rate > 0 else None,
            delta_color="normal" if team_diff >= 0 else "inverse"
        )
    
    # Visualize task status distribution
    create_task_status_distribution(member_df)
    
    # Show projects with task counts
    create_project_task_distribution(member_df)
    
    # Create performance trend visualization
    create_performance_trend_visualization(member_df, member_name)
    
    # Create performance acceleration analysis
    create_performance_acceleration_analysis(member_df, member_name)

def calculate_completion_rates(df: pd.DataFrame, period: str) -> Dict[str, float]:
    """
    Calculate task completion rates for a given period (daily or monthly).
    
    Args:
        df: DataFrame with task data for a team member
        period: "daily" or "monthly"
    
    Returns:
        Dictionary with current and previous period rates
    """
    # Filter completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        return {"current": 0, "previous": 0}
    
    # Calculate current time and period boundaries
    now = pd.Timestamp.now(tz="UTC")
    
    if period == "daily":
        # Last 7 days vs previous 7 days
        current_start = now - pd.Timedelta(days=7)
        previous_start = current_start - pd.Timedelta(days=7)
        days_divisor = 7
    else:  # monthly
        # Last 30 days vs previous 30 days
        current_start = now - pd.Timedelta(days=30)
        previous_start = current_start - pd.Timedelta(days=30)
        days_divisor = 30
    
    # Current period
    current_period_tasks = completed_tasks[
        (completed_tasks["completed_at"] >= current_start) & 
        (completed_tasks["completed_at"] <= now)
    ]
    current_rate = len(current_period_tasks) / days_divisor
    
    # Previous period
    previous_period_tasks = completed_tasks[
        (completed_tasks["completed_at"] >= previous_start) & 
        (completed_tasks["completed_at"] < current_start)
    ]
    previous_rate = len(previous_period_tasks) / days_divisor
    
    return {"current": current_rate, "previous": previous_rate}

def calculate_team_average(df: pd.DataFrame, metric_type: str) -> float:
    """
    Calculate team average for a specific metric type.
    
    Args:
        df: Full DataFrame with all team members
        metric_type: Type of metric to calculate average for
    
    Returns:
        Average value for the metric
    """
    if df.empty:
        return 0
    
    if metric_type == "completion_rate":
        # Calculate completion rate for each team member
        team_rates = []
        for member in df["assignee"].unique():
            member_df = df[df["assignee"] == member]
            if len(member_df) > 0:
                completed = len(member_df[member_df["status"] == "Completed"])
                total = len(member_df)
                rate = (completed / total) * 100 if total > 0 else 0
                team_rates.append(rate)
        
        return np.mean(team_rates) if team_rates else 0
    
    elif metric_type == "daily_rate":
        # Calculate daily completion rate for each team member
        team_rates = []
        for member in df["assignee"].unique():
            member_df = df[df["assignee"] == member]
            if not member_df.empty:
                rates = calculate_completion_rates(member_df, "daily")
                team_rates.append(rates["current"])
        
        return np.mean(team_rates) if team_rates else 0
    
    elif metric_type == "monthly_rate":
        # Calculate monthly completion rate for each team member
        team_rates = []
        for member in df["assignee"].unique():
            member_df = df[df["assignee"] == member]
            if not member_df.empty:
                rates = calculate_completion_rates(member_df, "monthly")
                team_rates.append(rates["current"])
        
        return np.mean(team_rates) if team_rates else 0
    
    elif metric_type == "project_count":
        # Calculate average number of projects per team member
        project_counts = []
        for member in df["assignee"].unique():
            member_df = df[df["assignee"] == member]
            project_count = member_df["project"].nunique()
            project_counts.append(project_count)
        
        return np.mean(project_counts) if project_counts else 0
    
    return 0

def calculate_trend(current: float, previous: float) -> float:
    """
    Calculate trend (change) between current and previous values.
    
    Args:
        current: Current value
        previous: Previous value
    
    Returns:
        Absolute change value
    """
    if previous == 0:
        return current
    return current - previous

def create_task_status_distribution(df: pd.DataFrame) -> None:
    """
    Create a visualization of task status distribution.
    
    Args:
        df: DataFrame with task data for a team member
    """
    # Group by status and count
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    
    # Create horizontal bar chart
    fig = px.bar(
        status_counts,
        y="Status",
        x="Count",
        color="Status",
        title="Task Status Distribution",
        orientation="h",
        height=200,
        color_discrete_map={"Completed": "#4CAF50", "In Progress": "#FFC107"}
    )
    
    fig.update_layout(
        xaxis_title="Number of Tasks",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_project_task_distribution(df: pd.DataFrame) -> None:
    """
    Create a visualization of task distribution across projects.
    
    Args:
        df: DataFrame with task data for a team member
    """
    # Group by project and status
    project_status = df.groupby(["project", "status"]).size().reset_index(name="count")
    
    # Create grouped bar chart
    fig = px.bar(
        project_status,
        x="project",
        y="count",
        color="status",
        title="Project Task Distribution",
        barmode="group",
        height=300,
        color_discrete_map={"Completed": "#4CAF50", "In Progress": "#FFC107"}
    )
    
    fig.update_layout(
        xaxis_title="Project",
        yaxis_title="Number of Tasks",
        legend_title="Status",
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_performance_trend_visualization(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create performance trend visualization for team members.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    
    # Filter for completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        st.info("No completed tasks available for trend analysis.")
        return
    
    # Filter for selected team member if specified
    if selected_team_member != "All Team Members":
        completed_tasks = completed_tasks[completed_tasks["assignee"] == selected_team_member]
        
        if completed_tasks.empty:
            st.info(f"No completed tasks available for {selected_team_member}.")
            return
    
    # Group by completion date and count tasks
    completed_tasks["completion_date"] = completed_tasks["completed_at"].dt.date
    
    # Get the date range
    min_date = completed_tasks["completion_date"].min()
    max_date = completed_tasks["completion_date"].max()
def create_team_velocity_comparison(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create team velocity comparison visualization, comparing task completion rates
    across team members and highlighting velocity trends.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    st.markdown("### Team Velocity Comparison")
    
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    
    # Calculate velocity metrics for each team member
    velocity_metrics = calculate_team_velocity_metrics(df)
    
    if not velocity_metrics:
        st.info("Insufficient data for team velocity comparison.")
        return
    
    # Convert to DataFrame
    metrics_df = pd.DataFrame(velocity_metrics)
    
    # Create the visualization tabs
    tab1, tab2, tab3 = st.tabs(["Daily Comparison", "Monthly Comparison", "Velocity Trends"])
    
    with tab1:
        # Create daily velocity comparison
        fig = px.bar(
            metrics_df,
            x="team_member",
            y="daily_velocity",
            color="trend",
            title="Daily Task Completion Rate by Team Member",
            labels={
                "team_member": "Team Member",
                "daily_velocity": "Tasks per Day",
                "trend": "Trend"
            },
            height=400,
            color_discrete_map={
                "Improving": "#4CAF50",
                "Stable": "#2196F3",
                "Declining": "#FFC107"
            },
            category_orders={"trend": ["Improving", "Stable", "Declining"]}
        )
        
        # Add horizontal line for team average
        team_avg = metrics_df["daily_velocity"].mean()
        fig.add_hline(
            y=team_avg,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Team Avg: {team_avg:.2f}",
            annotation_position="bottom right"
        )
        
        # Highlight selected team member if specified
        if selected_team_member != "All Team Members":
            for i, row in enumerate(fig.data[0].x):
                if row == selected_team_member:
                    fig.data[0].marker.color = ["rgba(255, 0, 0, 0.7)" if x == selected_team_member else fig.data[0].marker.color[i] for i, x in enumerate(fig.data[0].x)]
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Create monthly velocity comparison
        fig = px.bar(
            metrics_df,
            x="team_member",
            y="monthly_velocity",
            color="trend",
            title="Monthly Task Completion Rate by Team Member",
            labels={
                "team_member": "Team Member",
                "monthly_velocity": "Tasks per Month",
                "trend": "Trend"
            },
            height=400,
            color_discrete_map={
                "Improving": "#4CAF50",
                "Stable": "#2196F3",
                "Declining": "#FFC107"
            },
            category_orders={"trend": ["Improving", "Stable", "Declining"]}
        )
        
        # Add horizontal line for team average
        team_avg = metrics_df["monthly_velocity"].mean()
        fig.add_hline(
            y=team_avg,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Team Avg: {team_avg:.2f}",
            annotation_position="bottom right"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Create velocity trend over time
        create_velocity_trend_over_time(df)

def calculate_team_velocity_metrics(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculate velocity metrics for each team member.
    
    Args:
        df: DataFrame with task data
    
    Returns:
        List of dictionaries with velocity metrics by team member
    """
    velocity_metrics = []
    
    # Get unique team members
    team_members = df["assignee"].unique()
    
    for member in team_members:
        # Filter for this team member
        member_df = df[df["assignee"] == member].copy()
        
        if len(member_df) < 3:  # Skip if too few tasks
            continue
        
        # Calculate daily and monthly velocities
        daily_rates = calculate_completion_rates(member_df, "daily")
        monthly_rates = calculate_completion_rates(member_df, "monthly")
        
        current_daily = daily_rates.get("current", 0)
        previous_daily = daily_rates.get("previous", 0)
        current_monthly = monthly_rates.get("current", 0)
        previous_monthly = monthly_rates.get("previous", 0)
        
        # Calculate velocity change and determine trend
        daily_change = current_daily - previous_daily
        monthly_change = current_monthly - previous_monthly
        
        # Determine trend based on velocity changes
        if daily_change > 0.05 and monthly_change > 0:  # Significant improvement
            trend = "Improving"
        elif daily_change < -0.05 and monthly_change < 0:  # Significant decline
            trend = "Declining"
        else:  # Relatively stable
            trend = "Stable"
        
        velocity_metrics.append({
            "team_member": member,
            "daily_velocity": current_daily,
            "monthly_velocity": current_monthly,
            "daily_change": daily_change,
            "monthly_change": monthly_change,
            "trend": trend
        })
    
    # Sort by daily velocity (descending)
    velocity_metrics = sorted(velocity_metrics, key=lambda x: x["daily_velocity"], reverse=True)
    
    return velocity_metrics

def create_velocity_trend_over_time(df: pd.DataFrame) -> None:
    """
    Create visualization of velocity trends over time.
    
    Args:
        df: DataFrame with task data
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    
    # Filter for completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        st.info("No completed tasks available for velocity trend analysis.")
        return
    
    # Add completion week
    completed_tasks["completion_week"] = completed_tasks["completed_at"].dt.isocalendar().week
    completed_tasks["completion_year"] = completed_tasks["completed_at"].dt.isocalendar().year
    completed_tasks["year_week"] = completed_tasks["completion_year"].astype(str) + "-" + completed_tasks["completion_week"].astype(str).str.zfill(2)
    
    # Get top team members (limit to 5 for readability)
    top_members = completed_tasks["assignee"].value_counts().head(5).index.tolist()
    
    # Filter for top members
    top_member_tasks = completed_tasks[completed_tasks["assignee"].isin(top_members)]
    
    # Group by week and assignee
    weekly_velocity = top_member_tasks.groupby(["year_week", "assignee"]).size().reset_index(name="tasks_completed")
    
    # Sort by year_week
    unique_weeks = sorted(weekly_velocity["year_week"].unique())
    weekly_velocity["year_week"] = pd.Categorical(weekly_velocity["year_week"], categories=unique_weeks, ordered=True)
    weekly_velocity = weekly_velocity.sort_values("year_week")
    
    # Create line chart of weekly velocity
    fig = px.line(
        weekly_velocity,
        x="year_week",
        y="tasks_completed",
        color="assignee",
        title="Weekly Task Completion Velocity",
        labels={
            "year_week": "Week",
            "tasks_completed": "Tasks Completed",
            "assignee": "Team Member"
        },
        height=400,
        markers=True
    )
    
    # Add trendlines
    fig.update_traces(mode="lines+markers")
    
    # Format x-axis
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(0, len(unique_weeks), max(1, len(unique_weeks) // 10))),
            ticktext=[unique_weeks[i] for i in range(0, len(unique_weeks), max(1, len(unique_weeks) // 10))]
        ),
        xaxis_title="Week",
        yaxis_title="Tasks Completed",
        legend_title="Team Member"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_performance_acceleration_analysis(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create performance acceleration analysis for team members.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    
    # Filter for completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        st.info("No completed tasks available for acceleration analysis.")
        return
    
    # Calculate performance metrics for all team members
    performance_metrics = calculate_performance_metrics(completed_tasks)
    
    if not performance_metrics:
        st.info("Insufficient data for performance acceleration analysis.")
        return
    
    # Convert to DataFrame
    metrics_df = pd.DataFrame(performance_metrics)
    
    # Create visualization
    if selected_team_member != "All Team Members":
        # Filter for selected team member
        member_metrics = metrics_df[metrics_df["assignee"] == selected_team_member]
        
        if member_metrics.empty:
            st.info(f"No performance metrics available for {selected_team_member}.")
            return
        
        # Create a gauge chart for acceleration
        acceleration = member_metrics["acceleration"].iloc[0]
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=acceleration,
            title={"text": f"Performance Trend for {selected_team_member}"},
            delta={"reference": 0, "increasing": {"color": "green"}, "decreasing": {"color": "red"}},
            gauge={
                "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "darkblue"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [-100, -33], "color": "red"},
                    {"range": [-33, 33], "color": "yellow"},
                    {"range": [33, 100], "color": "green"}
                ]
            }
        ))
        
        # Update layout
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation
        trend_text = "accelerating" if acceleration > 0 else "decelerating" if acceleration < 0 else "maintaining steady performance"
        
        st.markdown(f"""
        **Performance Trend Analysis:**
        
        {selected_team_member} is **{trend_text}** in task completion rate.
        
        - **Recent Velocity**: {member_metrics["recent_velocity"].iloc[0]:.1f} tasks per week
        - **Historical Velocity**: {member_metrics["historical_velocity"].iloc[0]:.1f} tasks per week
        - **Change**: {acceleration:.1f}%
        """)
    else:
        # Show acceleration for all team members
        # Sort by acceleration
        metrics_df = metrics_df.sort_values("acceleration", ascending=False)
        
        # Create a bar chart
        fig = px.bar(
            metrics_df,
            x="assignee",
            y="acceleration",
            title="Performance Acceleration by Team Member",
            labels={
                "assignee": "Team Member",
                "acceleration": "Performance Acceleration (%)"
            },
            height=400,
            color="acceleration",
            color_continuous_scale="RdYlGn",
            range_color=[-100, 100]
        )
        
        # Add reference line at 0
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        # Update layout
        fig.update_layout(
            xaxis_title="Team Member",
            yaxis_title="Performance Acceleration (%)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation
        with st.expander("Understanding Performance Acceleration"):
            st.markdown("""
            **Performance Acceleration:**
            
            This metric compares recent task completion velocity with historical velocity to determine if a team member is:
            
            - **Accelerating** (positive values): Completing tasks faster than their historical average
            - **Maintaining** (near zero): Consistent with their historical performance
            - **Decelerating** (negative values): Completing tasks slower than their historical average
            
            Each team member is measured against their own historical performance, not against other team members.
            This provides a fair assessment regardless of individual capacity differences.
            """)

def calculate_performance_metrics(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculate performance metrics for team members, including velocity and acceleration.
    
    Args:
        df: DataFrame with completed task data
        
    Returns:
        List of performance metrics by team member
    """
    performance_metrics = []
    
    # Get unique team members
    team_members = df["assignee"].unique()
    
    for member in team_members:
        # Filter for this team member
        member_df = df[df["assignee"] == member].copy()
        
        if len(member_df) < 5:  # Skip if too few tasks
            continue
        
        # Sort by completion date
        member_df = member_df.sort_values("completed_at")
        
        # Calculate recent and historical velocity
        recent_velocity, historical_velocity = calculate_velocity(member_df)
        
        # Calculate acceleration (percentage change)
        if historical_velocity > 0:
            acceleration = ((recent_velocity - historical_velocity) / historical_velocity) * 100
        else:
            acceleration = 0 if recent_velocity == 0 else 100
        
        # Cap acceleration at +/- 100%
        acceleration = max(min(acceleration, 100), -100)
        
        performance_metrics.append({
            "assignee": member,
            "recent_velocity": recent_velocity,
            "historical_velocity": historical_velocity,
            "acceleration": acceleration
        })
    
    return performance_metrics

def calculate_velocity(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Calculate recent and historical velocity for a team member.
    
    Args:
        df: DataFrame with completed task data for a single team member
        
    Returns:
        Tuple of (recent_velocity, historical_velocity)
    """
    # Get the date range
    min_date = df["completed_at"].min()
    max_date = df["completed_at"].max()
    
    # Calculate the midpoint
    midpoint = min_date + (max_date - min_date) / 2
    
    # Split into recent and historical
    recent_df = df[df["completed_at"] >= midpoint]
    historical_df = df[df["completed_at"] < midpoint]
    
    # Calculate velocity (tasks per week)
    recent_velocity = calculate_weekly_velocity(recent_df)
    historical_velocity = calculate_weekly_velocity(historical_df)
    
    return recent_velocity, historical_velocity

def calculate_weekly_velocity(df: pd.DataFrame) -> float:
    """
    Calculate weekly velocity for a set of tasks.
    
    Args:
        df: DataFrame with completed task data
        
    Returns:
        Weekly velocity (tasks per week)
    """
    if df.empty:
        return 0
    
    # Get the date range
    min_date = df["completed_at"].min()
    max_date = df["completed_at"].max()
    
    # Calculate the number of weeks
    days = (max_date - min_date).total_seconds() / (24 * 60 * 60)
    weeks = max(days / 7, 1)  # Ensure at least 1 week to avoid division by zero
    
    # Calculate velocity
    velocity = len(df) / weeks
    
    return velocity 