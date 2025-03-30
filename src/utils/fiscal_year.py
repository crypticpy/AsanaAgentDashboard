"""
Fiscal year utilities for the Asana Portfolio Dashboard.

These utilities handle calculations related to fiscal years 
(Oct 1 - Sept 30) and quarterly data for the overview dashboard.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

def get_fiscal_year(date: Optional[pd.Timestamp] = None) -> Tuple[int, pd.Timestamp, pd.Timestamp]:
    """
    Get the fiscal year information for a given date.
    Fiscal year runs from Oct 1 to Sept 30.
    
    Args:
        date: Date to calculate fiscal year for, defaults to current date
        
    Returns:
        Tuple of (fiscal_year, start_date, end_date)
    """
    if date is None:
        date = pd.Timestamp.now(tz='UTC')
    
    if date.month >= 10:  # Oct-Dec
        fiscal_year = date.year + 1
        start_date = pd.Timestamp(date.year, 10, 1, tzinfo=date.tzinfo)
    else:  # Jan-Sep
        fiscal_year = date.year
        start_date = pd.Timestamp(date.year - 1, 10, 1, tzinfo=date.tzinfo)
    
    end_date = pd.Timestamp(fiscal_year, 9, 30, tzinfo=date.tzinfo)
    
    return fiscal_year, start_date, end_date

def get_fiscal_quarter(date: Optional[pd.Timestamp] = None) -> Tuple[int, int, pd.Timestamp, pd.Timestamp]:
    """
    Get the fiscal quarter information for a given date.
    
    Q1: Oct-Dec
    Q2: Jan-Mar
    Q3: Apr-Jun
    Q4: Jul-Sep
    
    Args:
        date: Date to calculate fiscal quarter for, defaults to current date
        
    Returns:
        Tuple of (fiscal_year, quarter, start_date, end_date)
    """
    if date is None:
        date = pd.Timestamp.now(tz='UTC')
    
    fiscal_year, fy_start, fy_end = get_fiscal_year(date)
    
    # Determine quarter
    if date.month >= 10 and date.month <= 12:  # Oct-Dec
        quarter = 1
        start_date = pd.Timestamp(date.year, 10, 1, tzinfo=date.tzinfo)
        end_date = pd.Timestamp(date.year, 12, 31, tzinfo=date.tzinfo)
    elif date.month >= 1 and date.month <= 3:  # Jan-Mar
        quarter = 2
        start_date = pd.Timestamp(date.year, 1, 1, tzinfo=date.tzinfo)
        end_date = pd.Timestamp(date.year, 3, 31, tzinfo=date.tzinfo)
    elif date.month >= 4 and date.month <= 6:  # Apr-Jun
        quarter = 3
        start_date = pd.Timestamp(date.year, 4, 1, tzinfo=date.tzinfo)
        end_date = pd.Timestamp(date.year, 6, 30, tzinfo=date.tzinfo)
    else:  # Jul-Sep
        quarter = 4
        start_date = pd.Timestamp(date.year, 7, 1, tzinfo=date.tzinfo)
        end_date = pd.Timestamp(date.year, 9, 30, tzinfo=date.tzinfo)
    
    return fiscal_year, quarter, start_date, end_date

def get_fiscal_year_quarters(fiscal_year: int) -> List[Dict[str, Any]]:
    """
    Get all quarters for a given fiscal year.
    
    Args:
        fiscal_year: The fiscal year to get quarters for
    
    Returns:
        List of dictionaries with quarter information
    """
    calendar_year = fiscal_year - 1
    
    quarters = [
        {
            'quarter': 1,
            'name': f'Q1 FY{fiscal_year}',
            'start_date': pd.Timestamp(calendar_year, 10, 1, tz='UTC'),
            'end_date': pd.Timestamp(calendar_year, 12, 31, tz='UTC')
        },
        {
            'quarter': 2,
            'name': f'Q2 FY{fiscal_year}',
            'start_date': pd.Timestamp(fiscal_year, 1, 1, tz='UTC'),
            'end_date': pd.Timestamp(fiscal_year, 3, 31, tz='UTC')
        },
        {
            'quarter': 3,
            'name': f'Q3 FY{fiscal_year}',
            'start_date': pd.Timestamp(fiscal_year, 4, 1, tz='UTC'),
            'end_date': pd.Timestamp(fiscal_year, 6, 30, tz='UTC')
        },
        {
            'quarter': 4,
            'name': f'Q4 FY{fiscal_year}',
            'start_date': pd.Timestamp(fiscal_year, 7, 1, tz='UTC'),
            'end_date': pd.Timestamp(fiscal_year, 9, 30, tz='UTC')
        }
    ]
    
    return quarters

def get_current_and_surrounding_fiscal_years(num_years: int = 3) -> List[int]:
    """
    Get a list of fiscal years centered around the current fiscal year.
    
    Args:
        num_years: The number of years to return (should be odd to center on current year)
    
    Returns:
        List of fiscal years
    """
    current_fy, _, _ = get_fiscal_year()
    years_before = num_years // 2
    
    return list(range(current_fy - years_before, current_fy + (num_years - years_before)))

def filter_by_fiscal_year(df: pd.DataFrame, fiscal_year: int) -> pd.DataFrame:
    """
    Filter a DataFrame to only include items from the specified fiscal year.
    
    Args:
        df: DataFrame to filter
        fiscal_year: Fiscal year to filter by
        
    Returns:
        Filtered DataFrame
    """
    # Get fiscal year start and end dates
    _, fy_start, fy_end = get_fiscal_year(pd.Timestamp(year=fiscal_year-1, month=10, day=1, tz='UTC'))
    
    # Ensure datetime columns are properly converted
    date_columns = ['created_at', 'completed_at', 'due_date']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    
    # Filter by fiscal year date range
    return df[(df['created_at'] >= fy_start) & (df['created_at'] <= fy_end)]

def calculate_project_health(project: Dict[str, Any], df: pd.DataFrame, current_date: pd.Timestamp, 
                           fiscal_year_end: pd.Timestamp, team_velocity: float) -> Tuple[str, str, float]:
    """
    Calculate project health status based on various factors including velocity and due dates.
    
    Args:
        project: Project data dictionary
        df: DataFrame of tasks
        current_date: Current date
        fiscal_year_end: End date of the fiscal year
        team_velocity: Team's overall velocity (tasks per day)
        
    Returns:
        Tuple of (health_status, reason, confidence_score)
    """
    # Get key project metrics
    project_name = project.get('project', '')
    remaining_tasks = project.get('remaining_tasks', 0) 
    total_tasks = project.get('total_tasks', 0) if 'total_tasks' in project else 0
    
    # For debugging purposes
    #print(f"Project: {project_name}, Remaining: {remaining_tasks}, Total: {total_tasks}")
    
    # Get project-specific tasks
    project_tasks = df[df['project'] == project_name]
    
    # Calculate project-specific velocity if possible
    project_velocity = None
    if 'velocity_metrics' in project and project['velocity_metrics'].get('velocity') is not None:
        project_velocity = project['velocity_metrics'].get('velocity')
    
    # If project-specific velocity not available or too low, use team velocity with a scaling factor
    if project_velocity is None or project_velocity < 0.01:
        if total_tasks > 0:
            # Scale velocity based on project size compared to average project size
            project_velocity = max(team_velocity * (total_tasks / 20), 0.05)  # Minimum of 0.05 tasks/day
        else:
            project_velocity = 0.05  # Minimum default velocity
    
    # 1. Check if project has any tasks defined
    if total_tasks == 0:
        return "Off Track", "No tasks defined", 0.9
    
    # 2. For completed projects, check if they were completed on time
    if remaining_tasks == 0 and total_tasks > 0:
        days_diff = project.get('days_difference')
        if days_diff is not None and days_diff > 0:
            return "Completed Late", f"{days_diff} days late", 1.0
        else:
            return "Completed On Time", "On time", 1.0
    
    # 3. For active projects with tasks remaining
    # Calculate days to completion based on velocity
    if project_velocity > 0 and remaining_tasks > 0:
        days_to_completion = remaining_tasks / project_velocity
        projected_completion = current_date + pd.Timedelta(days=days_to_completion)
    else:
        # Handle case where there's no velocity data but there are remaining tasks
        projected_completion = fiscal_year_end  # Assume completion by fiscal year end
    
    # 4. Check for explicit due date
    due_date = project.get('project_due_date')
    if due_date is not None and not pd.isna(due_date):
        # If due date is after fiscal year end, use the due date as target
        if due_date > fiscal_year_end:
            target_date = due_date
        else:
            target_date = min(due_date, fiscal_year_end)  # Use earlier of due date or fiscal year end
    else:
        # If no due date, project should complete by fiscal year end
        target_date = fiscal_year_end
    
    # 5. For projects with very low velocity, mark as at risk
    if project_velocity < 0.1 and remaining_tasks > 2:  # Less than 1 task per 10 days with multiple tasks remaining
        return "At Risk", "Very low velocity", 0.8
    
    # 6. Check for overdue tasks
    overdue_tasks = project.get('overdue_tasks', 0)
    if overdue_tasks > 0 and overdue_tasks >= max(1, total_tasks * 0.1):  # If ≥10% of tasks are overdue
        return "At Risk", f"{overdue_tasks} overdue tasks", 0.8
    
    # 7. Compare projected completion to target date
    if projected_completion <= current_date and remaining_tasks > 0:
        # Project has remaining tasks but estimated to be done already
        # This might indicate stalled work
        return "At Risk", "Work may be stalled", 0.7
    
    # Calculate days margin for active projects with remaining tasks
    if remaining_tasks > 0:
        days_margin = (target_date - projected_completion).days
        
        if days_margin >= 14:  # 2+ weeks buffer
            return "On Track", f"{days_margin} days buffer", 0.9
        elif days_margin >= 0:  # On track but tight
            return "On Track", "Tight schedule", 0.7
        elif days_margin >= -14:  # Slightly behind
            return "At Risk", f"{-days_margin} days behind", 0.8
        else:  # Significantly behind
            # If far behind schedule, classify as Off Track
            if days_margin < -30:
                return "Off Track", f"{-days_margin} days behind", 0.9
            else:
                return "At Risk", f"{-days_margin} days behind", 0.8
    
    # Default case for any remaining scenarios
    # This might be a project with remaining tasks but unclear status
    return "On Track", "Default status", 0.6

def calculate_portfolio_health(projects: List[Dict[str, Any]], df: pd.DataFrame, fiscal_year: int) -> Dict[str, Any]:
    """
    Calculate overall portfolio health based on project statuses.
    
    Args:
        projects: List of project dictionaries
        df: DataFrame of tasks
        fiscal_year: The fiscal year
        
    Returns:
        Dictionary with portfolio health metrics
    """
    # Get current date and fiscal year end
    current_date = pd.Timestamp.now(tz='UTC')
    _, fy_start, fy_end = get_fiscal_year(pd.Timestamp(year=fiscal_year-1, month=10, day=1, tz='UTC'))
    
    # Project counts
    total_projects = len(projects)
    if total_projects == 0:
        return {
            'health_score': 100, 
            'description': "No projects",
            'status_counts': {},
            'status_details': []
        }
    
    # Calculate team velocity from all completed tasks in the last 90 days
    team_velocity = calculate_velocity(df, window_days=90)
    
    # Count by status
    status_counts = {
        "On Track": 0, 
        "At Risk": 0, 
        "Off Track": 0, 
        "Completed On Time": 0, 
        "Completed Late": 0
    }
    
    status_details = []
    
    # Calculate health for each project
    for project in projects:
        status, reason, confidence = calculate_project_health(
            project, df, current_date, fy_end, team_velocity
        )
        status_counts[status] += 1
        
        # Get velocity for presentation
        velocity = 0.0
        if 'velocity_metrics' in project and project['velocity_metrics'].get('velocity') is not None:
            velocity = project['velocity_metrics'].get('velocity')
        else:
            velocity = team_velocity * 0.5  # Estimated velocity if not available
            
        status_details.append({
            "project": project.get('project', ''),
            "status": status,
            "reason": reason,
            "velocity": velocity,
            "confidence": confidence,
            "remaining_tasks": project.get('remaining_tasks', 0),
            "total_tasks": project.get('total_tasks', 0) if 'total_tasks' in project else 0
        })
    
    # Calculate weighted health score:
    # On Track: 100%, Completed On Time: 100%, At Risk: 50%, Off Track/Completed Late: 0%
    health_points = (
        (status_counts["On Track"] + status_counts["Completed On Time"]) * 100 +
        status_counts["At Risk"] * 50 +
        (status_counts["Off Track"] + status_counts["Completed Late"]) * 0
    )
    
    health_score = health_points / total_projects
    
    # Determine overall portfolio status
    if health_score >= 80:
        description = "Healthy"
    elif health_score >= 50:
        description = "Needs Attention"
    else:
        description = "Critical"
    
    return {
        'health_score': health_score,
        'description': description,
        'status_counts': status_counts,
        'status_details': status_details,
        'team_velocity': team_velocity
    }

def get_projects_by_status(df: pd.DataFrame, project_estimates: pd.DataFrame, fiscal_year: int) -> Dict[str, pd.DataFrame]:
    """
    Separate projects into completed (within the fiscal year) and active categories.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame with project completion estimates
        fiscal_year: The fiscal year to filter by
        
    Returns:
        Dictionary with 'completed' and 'active' project DataFrames
    """
    # Get fiscal year start and end dates
    _, fy_start, fy_end = get_fiscal_year(pd.Timestamp(year=fiscal_year-1, month=10, day=1, tz='UTC'))
    
    # Ensure datetime columns are properly converted
    if 'completed_at' in df.columns and df['completed_at'].dtype != 'datetime64[ns, UTC]':
        df['completed_at'] = pd.to_datetime(df['completed_at'], utc=True)
    
    # Get completed projects (projects with no remaining tasks)
    completed_projects = []
    active_projects = []
    
    for _, project in project_estimates.iterrows():
        project_name = project['project']
        
        # Get tasks for this project
        project_tasks = df[df['project'] == project_name]
        
        # Check if all tasks are completed
        all_completed = (project_tasks['status'] == 'Completed').all() if not project_tasks.empty else False
        
        # Check if any tasks were completed in this fiscal year
        completed_in_fy = project_tasks[
            (project_tasks['status'] == 'Completed') & 
            (project_tasks['completed_at'] >= fy_start) & 
            (project_tasks['completed_at'] <= fy_end)
        ]
        
        if all_completed and not completed_in_fy.empty:
            completed_projects.append(project)
        else:
            active_projects.append(project)
    
    return {
        'completed': pd.DataFrame(completed_projects) if completed_projects else pd.DataFrame(),
        'active': pd.DataFrame(active_projects) if active_projects else pd.DataFrame()
    }

def calculate_velocity(df: pd.DataFrame, window_days: int = 30) -> float:
    """
    Calculate the velocity (tasks completed per day) based on recent history.
    
    Args:
        df: DataFrame of tasks
        window_days: Number of days to look back for velocity calculation
        
    Returns:
        Tasks per day velocity
    """
    # Ensure datetime columns are properly converted
    if 'completed_at' in df.columns and df['completed_at'].dtype != 'datetime64[ns, UTC]':
        df['completed_at'] = pd.to_datetime(df['completed_at'], utc=True)
    
    # Get the cutoff date for the window
    cutoff_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=window_days)
    
    # Filter for completed tasks in the window
    completed_tasks = df[(df['status'] == 'Completed') & (df['completed_at'] >= cutoff_date)]
    
    # Calculate velocity (tasks per day)
    if not completed_tasks.empty:
        return len(completed_tasks) / window_days
    else:
        return 0.1  # Default to 0.1 tasks per day if no data

def calculate_quarterly_metrics(df: pd.DataFrame, fiscal_year: int) -> Dict[str, Any]:
    """
    Calculate metrics aggregated by quarter for the given fiscal year.
    
    Args:
        df: DataFrame of tasks
        fiscal_year: The fiscal year to calculate metrics for
    
    Returns:
        Dictionary with quarterly metrics
    """
    # Get all quarters for the fiscal year
    quarters = get_fiscal_year_quarters(fiscal_year)
    
    # Ensure datetime columns are properly converted
    date_columns = ['created_at', 'completed_at', 'due_date']
    for col in date_columns:
        if col in df.columns and df[col].dtype != 'datetime64[ns, UTC]':
            df[col] = pd.to_datetime(df[col], utc=True)
    
    # Initialize results dictionary
    results = {
        'fiscal_year': fiscal_year,
        'quarters': []
    }
    
    # Calculate metrics for each quarter
    for quarter in quarters:
        start_date = quarter['start_date']
        end_date = quarter['end_date']
        
        # Tasks created in this quarter
        created_in_quarter = df[(df['created_at'] >= start_date) & (df['created_at'] <= end_date)]
        
        # Tasks completed in this quarter
        completed_in_quarter = df[(df['completed_at'] >= start_date) &
                                  (df['completed_at'] <= end_date) &
                                  (df['status'] == 'Completed')]
        
        # Tasks due in this quarter
        due_in_quarter = df[(df['due_date'] >= start_date) & (df['due_date'] <= end_date)]
        
        # Tasks in progress during this quarter
        in_progress_during_quarter = df[
            # Created before or during this quarter, and either:
            ((df['created_at'] <= end_date) &
             # Still not completed, or
             ((df['status'] != 'Completed') |
              # Completed after this quarter started
              ((df['status'] == 'Completed') & (df['completed_at'] >= start_date))))
        ]
        
        # For Kanban/Scrum teams, calculate throughput (task completion rate)
        # instead of comparing to arbitrary due dates
        
        # If there's no due dates set or very few, use a more realistic calculation
        # based on work in progress during the quarter
        if len(due_in_quarter) < len(completed_in_quarter) * 0.3:  # Less than 30% of tasks have due dates
            # Use task throughput as the primary metric for Kanban
            total_tasks_in_quarter = len(in_progress_during_quarter)
            if total_tasks_in_quarter > 0:
                completion_rate = min((len(completed_in_quarter) / total_tasks_in_quarter * 100), 100)
            else:
                completion_rate = 0
                
            # For display and calculation purposes, we'll use the in-progress tasks as the denominator
            tasks_due = total_tasks_in_quarter
        else:
            # If due dates are used consistently, calculate based on what was due
            tasks_due = len(due_in_quarter)
            # Calculate completion rate (capped at 100%)
            completion_rate = min(
                (len(completed_in_quarter) / tasks_due * 100)
                if tasks_due > 0 else 100,
                100
            )
        
        # Calculate metrics
        quarter_metrics = {
            'quarter': quarter['quarter'],
            'name': quarter['name'],
            'start_date': start_date,
            'end_date': end_date,
            'tasks_created': len(created_in_quarter),
            'tasks_completed': len(completed_in_quarter),
            'tasks_due': tasks_due,
            'tasks_in_progress': len(in_progress_during_quarter),
            'completion_rate': completion_rate,
            'projects': created_in_quarter['project'].nunique(),
            'active_resources': created_in_quarter['assignee'].nunique()
        }
        
        results['quarters'].append(quarter_metrics)
    
    # Calculate overall fiscal year metrics
    fy_start = quarters[0]['start_date']
    fy_end = quarters[-1]['end_date']
    
    # Tasks in this fiscal year
    created_in_fy = df[(df['created_at'] >= fy_start) & (df['created_at'] <= fy_end)]
    completed_in_fy = df[(df['completed_at'] >= fy_start) &
                          (df['completed_at'] <= fy_end) &
                          (df['status'] == 'Completed')]
    due_in_fy = df[(df['due_date'] >= fy_start) & (df['due_date'] <= fy_end)]
    
    # Tasks in progress during fiscal year
    in_progress_during_fy = df[
        ((df['created_at'] <= fy_end) &
         ((df['status'] != 'Completed') |
          ((df['status'] == 'Completed') & (df['completed_at'] >= fy_start))))
    ]
    
    # If there's no due dates set or very few, use a more realistic calculation
    # based on work in progress during the fiscal year
    if len(due_in_fy) < len(completed_in_fy) * 0.3:  # Less than 30% of tasks have due dates
        # Use task throughput as the primary metric
        total_tasks_in_fy = len(in_progress_during_fy)
        if total_tasks_in_fy > 0:
            completion_rate = min((len(completed_in_fy) / total_tasks_in_fy * 100), 100)
        else:
            completion_rate = 0
            
        # For display and calculation purposes, we'll use the in-progress tasks as the denominator
        tasks_due = total_tasks_in_fy
    else:
        # If due dates are used consistently, calculate based on what was due
        tasks_due = len(due_in_fy)
        # Calculate completion rate (capped at 100%)
        completion_rate = min(
            (len(completed_in_fy) / tasks_due * 100)
            if tasks_due > 0 else 0,
            100
        )
    
    results['fiscal_year_metrics'] = {
        'tasks_created': len(created_in_fy),
        'tasks_completed': len(completed_in_fy),
        'tasks_due': tasks_due,
        'tasks_in_progress': len(in_progress_during_fy),
        'completion_rate': completion_rate,
        'projects': created_in_fy['project'].nunique(),
        'active_resources': created_in_fy['assignee'].nunique()
    }
    
    return results

def project_future_quarters(df: pd.DataFrame, project_estimates: pd.DataFrame,
                            current_fiscal_year: int) -> Dict[str, Any]:
    """
    Project future quarter performance based on current data, team velocity,
    and project estimates, optimized for Kanban/Scrum methodologies.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame with project completion estimates
        current_fiscal_year: The current fiscal year
        
    Returns:
        Dictionary with projected quarterly metrics
    """
    # Get current date and quarter information
    current_date = pd.Timestamp.now(tz='UTC')
    current_fy, current_quarter, current_quarter_start, current_quarter_end = get_fiscal_quarter(current_date)
    
    # Get all quarters for the fiscal year
    quarters = get_fiscal_year_quarters(current_fiscal_year)
    
    # Get actual metrics for completed quarters
    actual_metrics = calculate_quarterly_metrics(df, current_fiscal_year)
    
    # Calculate team velocity from recent history (last 90 days)
    velocity = calculate_velocity(df, window_days=90)
    
    # Calculate a 30-day velocity for more recent trend
    recent_velocity = calculate_velocity(df, window_days=30)
    
    # Use recent velocity if it's higher than the 90-day velocity (team speeding up)
    # but fall back to 90-day if more stable or if recent is lower
    effective_velocity = max(velocity, recent_velocity) if recent_velocity > 0 else velocity
    
    # Separate projects into completed and active
    projects_by_status = get_projects_by_status(df, project_estimates, current_fiscal_year)
    active_projects = projects_by_status['active']
    
    # For each future quarter, project metrics based on current trends and project estimates
    results = {
        'fiscal_year': current_fiscal_year,
        'quarters': []
    }
    
    # Count currently active tasks (not completed)
    active_tasks = df[df['status'] != 'Completed']
    active_task_count = len(active_tasks)
    
    # Get a list of projects with remaining work
    active_project_list = []
    for _, project in active_projects.iterrows():
        active_project_list.append(project)
    
    # Create a backlog of upcoming work based on active tasks
    backlog = []
    for _, task in active_tasks.iterrows():
        project_name = task.get('project', '')
        assignee = task.get('assignee', '')
        days_to_complete = 1 / effective_velocity if effective_velocity > 0 else 30  # Default to 30 days if no velocity
        backlog.append({
            'task_id': task.get('id', ''),
            'project': project_name,
            'assignee': assignee,
            'days_to_complete': days_to_complete
        })
    
    # Add in estimated future tasks from project data
    for _, project in active_projects.iterrows():
        project_name = project.get('project', '')
        remaining_tasks = project.get('remaining_tasks', 0)
        project_velocity = None
        
        # Try to get project-specific velocity
        if 'velocity_metrics' in project and project['velocity_metrics'].get('velocity') is not None:
            project_velocity = project['velocity_metrics'].get('velocity')
        
        # If no project velocity, use a fraction of team velocity
        if project_velocity is None or project_velocity < 0.01:
            project_velocity = max(effective_velocity * 0.8, 0.05)  # Scale team velocity with a conservative factor
        
        # Estimate days per task based on velocity
        days_per_task = 1 / project_velocity if project_velocity > 0 else 30  # Default to 30 days if no velocity
        
        # Create synthetic backlog tasks for remaining work
        for i in range(remaining_tasks):
            backlog.append({
                'task_id': f"{project_name}_future_{i}",
                'project': project_name,
                'assignee': 'Unassigned',  # These will be assigned later
                'days_to_complete': days_per_task
            })
    
    # Sort backlog by days to complete (shortest first)
    backlog.sort(key=lambda x: x['days_to_complete'])
    
    # For each quarter, allocate backlog tasks based on team capacity
    for quarter in quarters:
        q_num = quarter['quarter']
        quarter_metrics = next((q for q in actual_metrics['quarters'] if q['quarter'] == q_num), None)
        
        # If this is a future quarter or the current quarter (for which we need projections)
        if current_fy < current_fiscal_year or (current_fy == current_fiscal_year and q_num >= current_quarter):
            # For the current quarter, use actual data for the past and project the remainder
            is_current_quarter = (current_fy == current_fiscal_year and q_num == current_quarter)
            
            # Set up quarter date range
            start_date = quarter['start_date']
            end_date = quarter['end_date']
            
            if is_current_quarter:
                # For current quarter, only project from current date to end of quarter
                days_in_quarter = (end_date - current_date).days + 1
                days_elapsed = (current_date - start_date).days
            else:
                # For future quarters, use full quarter duration
                days_in_quarter = (end_date - start_date).days + 1
                days_elapsed = 0
            
            # Calculate team capacity based on number of active resources and their velocity
            # Get average team members from previous quarters
            active_resources = 0
            if quarter_metrics:
                # Use actual data if available
                active_resources = quarter_metrics.get('active_resources', 0)
            elif is_current_quarter:
                # For current quarter, use number of active assignees
                active_resources = len(set(task.get('assignee', '') for task in backlog
                                        if task.get('assignee', '') not in ['', 'Unassigned']))
            else:
                # For future quarters, estimate based on historical data
                historical_resources = [q.get('active_resources', 0) for q in actual_metrics.get('quarters', [])
                                      if not q.get('is_projected', True)]
                if historical_resources:
                    active_resources = int(sum(historical_resources) / len(historical_resources))
                else:
                    # Default if no historical data
                    active_resources = 5
            
            # Ensure minimum of 1 active resource
            active_resources = max(active_resources, 1)
            
            # Calculate team capacity as tasks that can be completed in this quarter
            team_capacity = effective_velocity * days_in_quarter * active_resources
            
            # For current quarter, factor in already completed tasks
            tasks_already_completed = 0
            if is_current_quarter and quarter_metrics:
                tasks_already_completed = quarter_metrics.get('tasks_completed', 0)
                
            # Calculate how many more tasks can be completed in this quarter
            remaining_capacity = max(team_capacity - tasks_already_completed, 0)
            
            # Determine how many backlog tasks can be completed with remaining capacity
            tasks_to_complete = 0
            task_days_sum = 0
            tasks_from_backlog = []
            
            for task in backlog[:]:  # Iterate through a copy to allow removal
                # If we have enough capacity for this task
                if task_days_sum + task['days_to_complete'] <= remaining_capacity:
                    tasks_to_complete += 1
                    task_days_sum += task['days_to_complete']
                    tasks_from_backlog.append(task)
                    backlog.remove(task)  # Remove from backlog as it's now allocated
                if task_days_sum >= remaining_capacity:
                    break  # Stop when we've allocated all our capacity
            
            # For the current quarter, include already completed tasks
            total_completed = tasks_to_complete + tasks_already_completed
            
            # Calculate task creation based on historical data and trend
            tasks_created = 0
            if quarter_metrics:
                # Use actual data for tasks created if available
                tasks_created = quarter_metrics.get('tasks_created', 0)
                
                if is_current_quarter:
                    # For current quarter, project additional task creation for remaining days
                    completed_quarters = [q for q in actual_metrics.get('quarters', [])
                                         if q['quarter'] < current_quarter and not q.get('is_projected', True)]
                    
                    if completed_quarters:
                        # Calculate average task creation rate per day from previous quarters
                        avg_creation_per_day = sum(q['tasks_created'] for q in completed_quarters) / (91 * len(completed_quarters))
                        # Add estimated tasks for remaining days in the quarter
                        additional_tasks = int(avg_creation_per_day * (days_in_quarter - days_elapsed))
                        tasks_created += additional_tasks
            else:
                # For future quarters, estimate based on historical data with a trend line
                historical_created = [q['tasks_created'] for q in actual_metrics.get('quarters', [])
                                     if not q.get('is_projected', True)]
                
                if historical_created:
                    avg_tasks_created = sum(historical_created) / len(historical_created)
                    
                    # Apply a trend based on position in future
                    quarters_in_future = q_num - current_quarter if current_fiscal_year == current_fy else 4
                    
                    if quarters_in_future <= 1:  # Next quarter
                        tasks_created = avg_tasks_created * 0.9  # Slight decrease
                    else:  # Further quarters
                        # More conservative projections for further out quarters
                        tasks_created = avg_tasks_created * (0.85 ** (quarters_in_future - 1))
                else:
                    # Default conservative estimate if no historical data
                    tasks_created = 20
            
            # For Kanban/Scrum, in_progress tasks is a better metric than due dates
            # Calculate tasks in progress, accounting for previously accumulated WIP
            # Get the WIP from the previous quarter if it exists
            previous_wip = 0
            if results['quarters']:
                # Find the most recent quarter in our results
                previous_quarter = results['quarters'][-1]
                previous_wip = previous_quarter.get('tasks_in_progress', 0)
            
            # For the current quarter, properly handle WIP
            if is_current_quarter:
                if quarter_metrics:
                    # For current quarter, get actual WIP count
                    current_wip_count = len(df[df['status'] != 'Completed'])
                    tasks_in_progress = current_wip_count
                else:
                    # If we don't have metrics yet, calculate WIP based on previous + created - completed
                    tasks_in_progress = previous_wip + tasks_created - tasks_to_complete
                    tasks_in_progress = max(tasks_in_progress, 0)  # Ensure non-negative
            else:
                # For future quarters, always carry over WIP from previous quarter
                # and adjust based on projected completion
                tasks_in_progress = previous_wip + tasks_created - tasks_to_complete
                tasks_in_progress = max(tasks_in_progress, 0)  # Ensure non-negative
                
                # For projection purposes, ensure WIP is at least 10% of capacity for healthy flow
                min_healthy_wip = team_capacity * 0.1
                if tasks_in_progress < min_healthy_wip:
                    tasks_in_progress = int(min_healthy_wip)
            # Calculate realistic tasks_due based on team capacity and initial workload
            if is_current_quarter:
                # For current quarter: use actual completed + actual WIP
                if quarter_metrics:
                    tasks_due = max(quarter_metrics.get('tasks_due', total_completed), total_completed)
                else:
                    # Fall back to a reasonable estimate if no metrics available
                    tasks_due = max(total_completed + tasks_in_progress, int(team_capacity * 1.1))
            else:
                # For future quarters: base on team capacity plus a buffer
                estimated_capacity = team_capacity * 1.2  # Add 20% buffer to challenge the team
                tasks_due = max(int(estimated_capacity), total_completed)
            
            # Calculate completion rate as the ratio of throughput to the expected throughput
            completion_rate = (total_completed / tasks_due * 100) if tasks_due > 0 else 0.0
            
            # Cap completion rate at 100%
            completion_rate = min(completion_rate, 100.0)
            
            # Get unique projects for this quarter
            projects_in_quarter = set(task['project'] for task in tasks_from_backlog)
            
            # Add any existing projects from quarter metrics
            if quarter_metrics and 'projects' in quarter_metrics:
                # If we have actual data, use that for project count
                projects_count = quarter_metrics.get('projects', 0)
            else:
                # Otherwise use our projected count
                projects_count = len(projects_in_quarter)
            
            projected_metrics = {
                'quarter': q_num,
                'name': quarter['name'],
                'start_date': start_date,
                'end_date': end_date,
                'tasks_created': int(tasks_created),
                'tasks_completed': int(total_completed),
                'tasks_due': int(tasks_due),
                'tasks_in_progress': int(tasks_in_progress),
                'completion_rate': min(completion_rate, 100),  # Cap at 100%
                'projects': projects_count,
                'active_resources': active_resources,
                'is_projected': True
            }
            
            results['quarters'].append(projected_metrics)
        else:
            # For past quarters, use actual metrics
            if quarter_metrics:
                quarter_metrics['is_projected'] = False
                results['quarters'].append(quarter_metrics)
    
    # Calculate overall fiscal year metrics
    total_tasks_completed = sum(q['tasks_completed'] for q in results['quarters'])
    total_tasks_due = sum(q['tasks_due'] for q in results['quarters'])
    total_tasks_created = sum(q['tasks_created'] for q in results['quarters'])
    total_tasks_in_progress = sum(q.get('tasks_in_progress', 0) for q in results['quarters'])
    
    # Calculate overall completion rate
    if total_tasks_due > 0:
        fy_completion_rate = (total_tasks_completed / total_tasks_due) * 100
    else:
        # Default to 90% if no tasks due (optimistic but realistic)
        fy_completion_rate = 90.0
    
    # For the current fiscal year, also factor in project completion status
    if current_fiscal_year == current_fy:
        total_projects = len(project_estimates)
        if total_projects > 0:
            completed_count = sum(1 for _, project in project_estimates.iterrows()
                                if project.get('remaining_tasks', 0) == 0)
            
            # Weight completion rate by project completion status
            project_completion_pct = (completed_count / total_projects) * 100 if total_projects > 0 else 0
            
            # Balance task-based and project-based completion rates
            fy_completion_rate = (fy_completion_rate * 0.7 + project_completion_pct * 0.3)
    
    # Calculate max projects across quarters for the fiscal year
    max_projects = max((q['projects'] for q in results['quarters']), default=0)
    
    # Calculate max resources across quarters for the fiscal year
    max_resources = max((q['active_resources'] for q in results['quarters']), default=0)
    
    results['fiscal_year_metrics'] = {
        'tasks_created': total_tasks_created,
        'tasks_completed': total_tasks_completed,
        'tasks_due': total_tasks_due,
        'tasks_in_progress': total_tasks_in_progress,
        'completion_rate': min(fy_completion_rate, 100),  # Cap at 100%
        'projects': max_projects,
        'active_resources': max_resources
    }
    
    return results