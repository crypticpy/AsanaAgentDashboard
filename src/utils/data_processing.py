"""
Data processing utilities for the Asana Portfolio Dashboard.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import colorsys
import logging

def estimate_project_completion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate project completion dates based on task data and completion rates.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        DataFrame with project completion estimates
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Ensure datetime columns are properly converted to pandas Timestamp with UTC timezone
    date_columns = ['due_date', 'created_at', 'completed_at', 'project_due_date']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    
    project_estimates = []
    current_date = pd.Timestamp.now(tz='UTC')

    for project_name, project_df in df.groupby('project'):
        # Get total and completed tasks
        total_tasks = len(project_df)
        completed_tasks = len(project_df[project_df['status'] == 'Completed'])
        remaining_tasks = total_tasks - completed_tasks
        
        # Calculate completion percentage
        completion_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Calculate task completion velocity (tasks per day)
        completed_tasks_df = project_df[project_df['status'] == 'Completed']
        
        if len(completed_tasks_df) > 0:
            # Get the earliest created_at and latest completed_at dates
            earliest_task_date = completed_tasks_df['created_at'].min()
            latest_completion_date = completed_tasks_df['completed_at'].max()
            
            # Calculate project duration so far in days
            if earliest_task_date and latest_completion_date:
                project_duration_days = (latest_completion_date - earliest_task_date).total_seconds() / (60 * 60 * 24)
                
                # Calculate velocity: tasks completed per day
                if project_duration_days > 0:
                    velocity = completed_tasks / project_duration_days
                else:
                    # If all tasks were completed on the same day, use a default velocity
                    velocity = 0.5  # Conservative estimate: 1 task per 2 days
            else:
                velocity = 0.5  # Default velocity
                
            # Apply velocity adjustments based on project completion percentage
            if completion_percentage > 80:
                # Projects near completion often accelerate
                velocity_adjustment = 1.2
            elif completion_percentage > 50:
                # Mid-project velocity is usually stable
                velocity_adjustment = 1.0
            elif completion_percentage > 20:
                # Early-mid projects might slow down as complexity increases
                velocity_adjustment = 0.8
            else:
                # Early projects often have slower velocity as team ramps up
                velocity_adjustment = 0.6
                
            # Apply the adjustment
            adjusted_velocity = velocity * velocity_adjustment
            
            # Ensure minimum velocity
            adjusted_velocity = max(adjusted_velocity, 0.1)  # At least 1 task per 10 days
            
            # Calculate days needed to complete remaining tasks
            if adjusted_velocity > 0:
                days_to_completion = remaining_tasks / adjusted_velocity
            else:
                # Fallback if velocity calculation fails
                days_to_completion = remaining_tasks * 5  # Assume 5 days per task
                
            # Apply constraints based on project size and progress
            if remaining_tasks <= 2:
                # Small number of remaining tasks - minimum 3 days per task
                days_to_completion = max(days_to_completion, remaining_tasks * 3)
            elif remaining_tasks >= 20 and completion_percentage < 20:
                # Large projects with little progress - cap maximum estimate
                days_to_completion = min(days_to_completion, 180)  # Cap at 6 months
            elif completion_percentage > 90:
                # Almost complete projects - ensure reasonable timeframe
                days_to_completion = min(days_to_completion, 30)  # Cap at 1 month
                
            # Convert to timedelta
            estimated_completion_time = pd.Timedelta(days=days_to_completion)
            
        else:
            # No completed tasks yet, use a default estimate based on total tasks
            if total_tasks <= 5:
                # Small projects: 5 days per task
                days_per_task = 5
            elif total_tasks <= 15:
                # Medium projects: 7 days per task
                days_per_task = 7
            else:
                # Large projects: 10 days per task
                days_per_task = 10
                
            estimated_completion_time = pd.Timedelta(days=days_per_task * total_tasks)

        # Get project due date if available
        project_due_date = None
        if 'project_due_date' in project_df.columns and not project_df['project_due_date'].empty:
            project_due_date = project_df['project_due_date'].iloc[0]
            if project_due_date is not None and not pd.isna(project_due_date):
                # Ensure project_due_date is a pandas Timestamp with UTC timezone
                if not isinstance(project_due_date, pd.Timestamp):
                    project_due_date = pd.Timestamp(project_due_date, tz='UTC')
                elif project_due_date.tzinfo is None:
                    project_due_date = project_due_date.tz_localize('UTC')

        # Calculate estimated completion date
        estimated_completion_date = current_date + estimated_completion_time if not pd.isna(estimated_completion_time) else pd.NaT

        # For projects that are already complete, use the latest completion date
        if remaining_tasks == 0 and len(completed_tasks_df) > 0:
            estimated_completion_date = completed_tasks_df['completed_at'].max()

        # Compare with due date
        days_difference = None
        if project_due_date is not None and not pd.isna(estimated_completion_date):
            days_difference = (estimated_completion_date - project_due_date).days

        # Store velocity metrics for reference
        velocity_metrics = {
            'velocity': velocity_adjustment * velocity if 'velocity' in locals() else None,
            'days_to_completion': days_to_completion if 'days_to_completion' in locals() else None
        }

        project_estimates.append({
            'project': project_name,
            'avg_task_completion_time': pd.Timedelta(days=1/velocity) if 'velocity' in locals() and velocity > 0 else pd.NaT,
            'remaining_tasks': remaining_tasks,
            'total_tasks': total_tasks,  # Add total_tasks field
            'completion_percentage': completion_percentage,
            'estimated_completion_time': estimated_completion_time,
            'estimated_completion_date': estimated_completion_date,
            'project_due_date': project_due_date,
            'days_difference': days_difference,
            'velocity_metrics': velocity_metrics
        })

    return pd.DataFrame(project_estimates)

def get_total_tasks(project_name: str, df: pd.DataFrame) -> int:
    """
    Get the total number of tasks for a project.
    
    Args:
        project_name: Name of the project
        df: DataFrame of tasks
        
    Returns:
        Total number of tasks
    """
    return df[df['project'] == project_name].shape[0]

def get_completed_tasks(project_name: str, df: pd.DataFrame) -> int:
    """
    Get the number of completed tasks for a project.
    
    Args:
        project_name: Name of the project
        df: DataFrame of tasks
        
    Returns:
        Number of completed tasks
    """
    return df[(df['project'] == project_name) & (df['status'] == 'Completed')].shape[0]

def get_overdue_tasks(project_name: str, df: pd.DataFrame) -> int:
    """
    Get the number of overdue tasks for a project.
    
    Args:
        project_name: Name of the project
        df: DataFrame of tasks
        
    Returns:
        Number of overdue tasks
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Ensure due_date is properly converted to pandas Timestamp with UTC timezone
    if 'due_date' in df.columns and df['due_date'].dtype != 'datetime64[ns, UTC]':
        df['due_date'] = pd.to_datetime(df['due_date'], utc=True)
    
    now = pd.Timestamp.now(tz='UTC')
    return df[(df['project'] == project_name) &
              (df['status'] != 'Completed') &
              (df['due_date'] < now) &
              (df['due_date'].notna())].shape[0]

def calculate_resource_utilization(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate resource utilization based on task assignments.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        Dictionary with utilization metrics
    """
    # Assuming 'assignee' represents resources and we're looking at active tasks
    active_tasks = df[df['status'] != 'Completed']
    resource_utilization = active_tasks['assignee'].value_counts()
    total_resources = df['assignee'].nunique()

    # Calculate utilization percentage (assuming max capacity is 10 tasks per resource)
    utilization_percentage = (len(active_tasks) / (total_resources * 10)) * 100 if total_resources > 0 else 0

    return {
        'utilization_percentage': min(utilization_percentage, 100),  # Cap at 100%
        'top_utilized_resources': resource_utilization.head(5).to_dict()
    }

def get_recent_activity(df: pd.DataFrame, days: int = 7) -> Dict[str, Any]:
    """
    Get recent activity metrics.
    
    Args:
        df: DataFrame of tasks
        days: Number of days to consider as recent
        
    Returns:
        Dictionary with recent activity metrics
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Ensure datetime columns are properly converted to pandas Timestamp with UTC timezone
    date_columns = ['created_at', 'completed_at']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    
    recent_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days)

    recent_completed = df[(df['completed_at'] >= recent_date) & (df['status'] == 'Completed')]
    recent_created = df[df['created_at'] >= recent_date]

    # Calculate trends (percentage change from previous period)
    previous_period_start = recent_date - pd.Timedelta(days=days)
    previous_completed = df[(df['completed_at'] >= previous_period_start) & 
                           (df['completed_at'] < recent_date) & 
                           (df['status'] == 'Completed')]
    previous_created = df[(df['created_at'] >= previous_period_start) & 
                         (df['created_at'] < recent_date)]
    
    completed_trend = calculate_percentage_change(len(recent_completed), len(previous_completed))
    created_trend = calculate_percentage_change(len(recent_created), len(previous_created))

    return {
        'completed_tasks': len(recent_completed),
        'created_tasks': len(recent_created),
        'completed_tasks_trend': completed_trend,
        'created_tasks_trend': created_trend
    }

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

def calculate_time_to_completion_trend(df: pd.DataFrame, months: int = 4) -> pd.DataFrame:
    """
    Calculate time to completion trend over months.
    
    Args:
        df: DataFrame of tasks
        months: Number of months to analyze
        
    Returns:
        DataFrame with time to completion trend
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Ensure datetime columns are properly converted to pandas Timestamp with UTC timezone
    date_columns = ['created_at', 'completed_at']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    
    df['completion_time'] = (df['completed_at'] - df['created_at']).dt.total_seconds() / 86400  # in days

    end_date = pd.Timestamp.now(tz='UTC')
    start_date = end_date - pd.DateOffset(months=months - 1)  # 3 months back + current month

    # Create a date range for each month
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')

    monthly_avg_completion_time = []

    for date in date_range:
        month_end = date + pd.offsets.MonthEnd(1)
        month_data = df[
            (df['completed_at'] >= date) &
            (df['completed_at'] <= month_end) &
            (df['status'] == 'Completed')
            ]
        avg_time = month_data['completion_time'].mean()
        monthly_avg_completion_time.append({
            'date': date,
            'days_to_complete': avg_time if pd.notna(avg_time) else 0
        })

    trend_df = pd.DataFrame(monthly_avg_completion_time)

    # Add a projection for the next month
    if not trend_df.empty:
        last_avg = trend_df['days_to_complete'].iloc[-1]
        next_month = end_date + pd.DateOffset(months=1)
        projection_df = pd.DataFrame([{
            'date': next_month,
            'days_to_complete': last_avg  # Simple projection using last month's average
        }])

        # Use concat instead of append
        trend_df = pd.concat([trend_df, projection_df], ignore_index=True)

    return trend_df

def generate_distinct_colors(n: int) -> List[str]:
    """
    Generate n distinct colors for visualizations.
    
    Args:
        n: Number of colors to generate
        
    Returns:
        List of RGB color strings
    """
    HSV_tuples = [(x * 1.0 / n, 0.5, 0.5) for x in range(n)]
    RGB_tuples = [colorsys.hsv_to_rgb(*x) for x in HSV_tuples]
    return ['rgb({:.0f}, {:.0f}, {:.0f})'.format(x[0] * 255, x[1] * 255, x[2] * 255) for x in RGB_tuples]

def get_project_details(project: Dict[str, Any], _projects_api: Any, _portfolios_api: Any, 
                       portfolio_gid: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get detailed information about a project.
    
    Args:
        project: Project data
        _projects_api: Asana Projects API instance
        _portfolios_api: Asana Portfolios API instance
        portfolio_gid: Portfolio GID
        df: DataFrame of tasks
        
    Returns:
        Dictionary with project details
    """
    from src.utils.asana_api import get_project_owner, get_project_members_count, get_project_gid
    
    project_name = project['project']
    project_gid = df[df['project'] == project_name]['project_gid'].iloc[0] if 'project_gid' in df.columns else None

    # Determine status based on days_difference and completion percentage
    status = "On Track"
    if project.get('days_difference') is not None and project.get('days_difference') > 0:
        if project.get('days_difference') > 30:
            status = "Behind"
        else:
            status = "At Risk"
    
    # Get completion percentage from project data or calculate it
    completion_percentage = project.get('completion_percentage')
    if completion_percentage is None:
        total_tasks = get_total_tasks(project_name, df)
        completed_tasks = get_completed_tasks(project_name, df)
        completion_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
    # Get velocity metrics
    velocity_metrics = project.get('velocity_metrics', {})

    if project_gid is None or project_gid == "Unknown":
        return {
            'name': project_name,
            'gid': "Unknown",
            'owner': "Unknown",
            'members_count': 0,
            'total_tasks': get_total_tasks(project_name, df),
            'completed_tasks': get_completed_tasks(project_name, df),
            'overdue_tasks': get_overdue_tasks(project_name, df),
            'estimated_completion_date': project['estimated_completion_date'],
            'remaining_tasks': project['remaining_tasks'],
            'avg_task_completion_time': project['avg_task_completion_time'],
            'completion_percentage': completion_percentage,
            'status': status,
            'on_track': project.get('on_track', False),
            'days_difference': project['days_difference'],
            'velocity_metrics': velocity_metrics
        }
    else:
        return {
            'name': project_name,
            'gid': project_gid,
            'owner': get_project_owner(project_name, project_gid, _projects_api),
            'members_count': get_project_members_count(project_name, project_gid, _projects_api),
            'total_tasks': get_total_tasks(project_name, df),
            'completed_tasks': get_completed_tasks(project_name, df),
            'overdue_tasks': get_overdue_tasks(project_name, df),
            'estimated_completion_date': project['estimated_completion_date'],
            'remaining_tasks': project['remaining_tasks'],
            'avg_task_completion_time': project['avg_task_completion_time'],
            'completion_percentage': completion_percentage,
            'status': status,
            'on_track': project.get('on_track', False),
            'days_difference': project['days_difference'],
            'velocity_metrics': velocity_metrics
        }

def get_project_owner(project_name: str, project_gid: str, _projects_api: Any) -> str:
    """
    Get the owner of a project.
    
    Args:
        project_name: Name of the project
        project_gid: Project GID
        _projects_api: Asana Projects API instance
        
    Returns:
        Owner name or 'Not assigned'
    """
    try:
        project_details = _projects_api.get_project(project_gid, opts={'fields': ['owner']})
        if project_details.owner:
            return project_details.owner.name
        return "Not assigned"
    except Exception as e:
        logging.error(f"Error getting owner for project {project_name}: {e}")
        return "Not assigned"

def get_project_members_count(project_name: str, project_gid: str, _projects_api: Any) -> int:
    """
    Get the number of members in a project.
    
    Args:
        project_name: Name of the project
        project_gid: Project GID
        _projects_api: Asana Projects API instance
        
    Returns:
        Number of members
    """
    try:
        members = _projects_api.get_project_memberships_for_project(project_gid)
        return len(list(members))
    except Exception as e:
        logging.error(f"Error getting members for project {project_name}: {e}")
        return 0 