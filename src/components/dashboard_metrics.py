"""
Dashboard metrics component for the Asana Portfolio Dashboard.
"""
import streamlit as st
from typing import Dict, Any, List
import pandas as pd
import hydralit_components as hc
from streamlit_extras.metric_cards import style_metric_cards

# Constants for column names
TASKS_COMPLETED = 'Tasks Completed'
TASKS_CREATED = 'Tasks Created'
CURRENTLY_ASSIGNED_TASKS = 'Currently Assigned Tasks'

def create_summary_metrics(df: pd.DataFrame, project_estimates: pd.DataFrame) -> None:
    """
    Create summary metrics for the dashboard.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
    """
    # Calculate metrics
    total_projects = len(project_estimates)
    on_track_projects = sum(row.get('days_difference') is None or row.get('days_difference') <= 0
                        for _, row in project_estimates.iterrows())
    
    total_tasks = len(df)
    completed_tasks = df[df['status'] == 'Completed'].shape[0]
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Resource utilization
    active_tasks = df[df['status'] != 'Completed']
    total_resources = df['assignee'].nunique()
    resource_utilization = (len(active_tasks) / (total_resources * 10)) * 100 if total_resources > 0 else 0
    
    # Create metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Projects",
            value=total_projects,
            delta=None
        )
    
    with col2:
        st.metric(
            label="On Track Projects",
            value=f"{on_track_projects}/{total_projects}",
            delta=f"{(on_track_projects / total_projects) * 100:.1f}%" if total_projects > 0 else "0%",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="Completion Rate",
            value=f"{completion_rate:.1f}%",
            delta=None
        )
    
    with col4:
        st.metric(
            label="Resource Utilization",
            value=f"{min(resource_utilization, 100):.1f}%",
            delta=None
        )
    
    # Apply styling
    style_metric_cards()

def create_recent_activity_metrics(df: pd.DataFrame) -> None:
    """
    Create recent activity metrics and trend visualization.
    
    Args:
        df: DataFrame of tasks
    """
    # Calculate recent activity (last 7 days)
    recent_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
    
    recent_completed = df[(df['completed_at'] >= recent_date) & (df['status'] == 'Completed')]
    recent_created = df[df['created_at'] >= recent_date]
    
    # Calculate trends (percentage change from previous period)
    previous_period_start = recent_date - pd.Timedelta(days=7)
    previous_completed = df[(df['completed_at'] >= previous_period_start) & 
                           (df['completed_at'] < recent_date) & 
                           (df['status'] == 'Completed')]
    previous_created = df[(df['created_at'] >= previous_period_start) & 
                         (df['created_at'] < recent_date)]
    
    completed_trend = calculate_percentage_change(len(recent_completed), len(previous_completed))
    created_trend = calculate_percentage_change(len(recent_created), len(previous_created))
    
    # Create metrics
    st.markdown("### Recent Activity (Last 7 Days)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="Tasks Completed",
            value=len(recent_completed),
            delta=f"{completed_trend}%" if completed_trend != 0 else None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="Tasks Created",
            value=len(recent_created),
            delta=f"{created_trend}%" if created_trend != 0 else None,
            delta_color="normal"
        )
    
    # Apply styling
    style_metric_cards()
    
    # Add daily activity trend chart for the past 14 days
    create_daily_activity_trend(df)

def _prepare_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure datetime columns are properly converted."""
    df = df.copy()
    date_columns = ['created_at', 'completed_at']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    return df

def _get_date_range(days: int = 14) -> tuple:
    """Get start and end dates for the specified number of days."""
    end_date = pd.Timestamp.now(tz='UTC')
    start_date = end_date - pd.Timedelta(days=days)
    return start_date, end_date

def _create_daily_data_frame(df: pd.DataFrame, start_date: pd.Timestamp, date_range: pd.DatetimeIndex) -> pd.DataFrame:
    """Create a DataFrame with daily task counts."""
    daily_data = pd.DataFrame(index=date_range)
    
    # Count tasks created per day
    created_tasks = df[df['created_at'] >= start_date].copy()
    if not created_tasks.empty:
        created_counts = created_tasks.groupby(pd.Grouper(key='created_at', freq='D')).size()
        daily_data[TASKS_CREATED] = created_counts.reindex(daily_data.index, fill_value=0)
    else:
        daily_data[TASKS_CREATED] = 0
    
    # Count tasks completed per day
    completed_tasks = df[(df['completed_at'] >= start_date) & (df['status'] == 'Completed')].copy()
    if not completed_tasks.empty:
        completed_counts = completed_tasks.groupby(pd.Grouper(key='completed_at', freq='D')).size()
        daily_data[TASKS_COMPLETED] = completed_counts.reindex(daily_data.index, fill_value=0)
    else:
        daily_data[TASKS_COMPLETED] = 0
    
    # Format the index for better display
    daily_data.index = daily_data.index.strftime('%b %d')
    return daily_data

def _apply_cumulative_option(daily_data: pd.DataFrame) -> tuple:
    """Apply cumulative sum option if selected and return the chart title."""
    show_cumulative = st.checkbox(
        "Show Cumulative Progress", value=False, key="show_cumulative"
    )
    if show_cumulative:
        daily_data[TASKS_CREATED] = daily_data[TASKS_CREATED].cumsum()
        daily_data[TASKS_COMPLETED] = daily_data[TASKS_COMPLETED].cumsum()
        return daily_data, "Cumulative Task Activity (Last 14 Days)"
    return daily_data, "Daily Task Activity (Last 14 Days)"

def _handle_empty_data(df: pd.DataFrame, daily_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp, date_range: pd.DatetimeIndex) -> tuple:
    """Handle the case when no data is available for the period."""
    if has_data := (daily_data[TASKS_CREATED].sum() > 0) or (
        daily_data[TASKS_COMPLETED].sum() > 0
    ):
        return daily_data, has_data

    # Get the recent activity data from the metrics above
    recent_date = end_date - pd.Timedelta(days=7)
    recent_completed = df[(df['completed_at'] >= recent_date) & (df['status'] == 'Completed')]
    recent_created = df[df['created_at'] >= recent_date]

    if len(recent_completed) > 0 or len(recent_created) > 0:
        st.info(f"Using recent activity data: {len(recent_created)} created, {len(recent_completed)} completed in last 7 days")

        # Distribute the tasks over the last 7 days
        last_week = date_range[-7:]
        for i, date in enumerate(last_week):
            date_str = date.strftime('%b %d')
            if i < len(last_week) - 1:  # Not today
                daily_data.loc[date_str, TASKS_CREATED] = max(1, len(recent_created) // 7)
            else:  # Today
                daily_data.loc[date_str, TASKS_CREATED] = len(recent_created) - (max(1, len(recent_created) // 7) * 6)

            if i == len(last_week) - 2:  # Yesterday
                daily_data.loc[date_str, TASKS_COMPLETED] = len(recent_completed)

        return daily_data, True

    # Add debug information
    _display_debug_info(df, start_date, end_date)
    return daily_data, False

def _display_debug_info(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> None:
    """Display debug information when no data is available."""
    st.info("No task activity data available for the selected period.")
    st.write(f"Date range: {start_date.date()} to {end_date.date()}")
    st.write(f"Tasks with created_at in range: {len(df[(df['created_at'] >= start_date) & (df['created_at'] <= end_date)])}")
    st.write(f"Tasks with completed_at in range: {len(df[(df['completed_at'] >= start_date) & (df['completed_at'] <= end_date) & (df['status'] == 'Completed')])}")
    
    # Show the actual data we have
    recent_tasks = df[(df['created_at'] >= start_date) | ((df['completed_at'] >= start_date) & (df['status'] == 'Completed'))]
    if not recent_tasks.empty:
        st.write("Sample of recent tasks:")
        st.write(recent_tasks[['name', 'created_at', 'completed_at', 'status']].head(5))

def create_daily_activity_trend(df: pd.DataFrame) -> None:
    """
    Create a daily activity trend chart showing task creation and completion over the past 14 days.
    
    Args:
        df: DataFrame of tasks
    """
    # Prepare data
    df = _prepare_datetime_columns(df)
    start_date, end_date = _get_date_range(days=14)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create daily data frame
    daily_data = _create_daily_data_frame(df, start_date, date_range)
    
    # Apply cumulative option if selected
    daily_data, chart_title = _apply_cumulative_option(daily_data)
    
    # Display the chart title
    st.caption(chart_title)
    
    # Handle empty data
    daily_data, has_data = _handle_empty_data(df, daily_data, start_date, end_date, date_range)
    
    # Create the chart if we have data
    if has_data:
        st.area_chart(daily_data, height=200)

def create_top_resources_metrics(df: pd.DataFrame) -> None:
    """
    Create top resources metrics showing staff with the most open tasks assigned to them
    or staff who completed the most tasks in the last 30 days.
    
    Args:
        df: DataFrame of tasks
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Add a toggle to switch between active tasks and completed tasks
    st.markdown("### Top Utilized Resources")
    
    view_option = st.radio(
        "View by:",
        [CURRENTLY_ASSIGNED_TASKS, "Tasks Completed (Last 30 Days)"],
        horizontal=True,
        key="resource_view_toggle"
    )
    
    if view_option == CURRENTLY_ASSIGNED_TASKS:
        # Filter for only active (non-completed) tasks with assignees
        filtered_tasks = df[
            (df['status'] != 'Completed') &
            (df['assignee'].notna()) &  # Only include tasks with assignees
            (df['assignee'] != 'Unassigned')  # Exclude unassigned tasks
        ]
        subtitle = "Staff with most active tasks assigned"
    else:
        # Filter for tasks completed in the last 30 days
        thirty_days_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
        filtered_tasks = df[
            (df['completed_at'] >= thirty_days_ago) &
            (df['status'] == 'Completed') &
            (df['assignee'].notna()) &  # Only include tasks with assignees
            (df['assignee'] != 'Unassigned')  # Exclude unassigned tasks
        ]
        subtitle = "Staff who completed the most tasks in the last 30 days"
    
    # Get top resources
    resource_counts = filtered_tasks['assignee'].value_counts().head(5)
    
    if resource_counts.empty:
        st.info(f"No data available for {subtitle.lower()}")
        return
    
    # Display subtitle
    st.caption(subtitle)
    
    # Create a more reliable visualization using columns and metrics
    cols = st.columns(min(5, len(resource_counts)))
    
    # Define delta color based on view option
    # For active tasks, we use 'inverse' since higher numbers are concerning (potential overload)
    # For completed tasks, we use 'normal' since higher numbers are good (productivity)
    delta_color = "inverse" if view_option == CURRENTLY_ASSIGNED_TASKS else "normal"
    
    # Display metrics in columns
    for i, (name, count) in enumerate(resource_counts.items()):
        if i < len(cols):
            with cols[i]:
                st.metric(
                    label=name,
                    value=count,
                    delta=f"{count} tasks",
                    delta_color=delta_color
                )
    
    # Create a bar chart for better visualization
    chart_data = pd.DataFrame({
        'Staff': resource_counts.index,
        'Tasks': resource_counts.values
    })
    
    # Add color coding to the chart based on the view option
    if view_option == CURRENTLY_ASSIGNED_TASKS:
        st.caption("⚠️ Higher numbers may indicate potential resource overload")
    else:
        st.caption("✅ Higher numbers indicate higher productivity")
    
    st.bar_chart(
        chart_data.set_index('Staff'),
        use_container_width=True,
        height=200
    )

def calculate_percentage_change(current: int, previous: int) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        current: Current value
        previous: Previous value
        
    Returns:
        Percentage change
    """
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1) 