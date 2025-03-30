"""
Visualization utilities for the Asana Portfolio Dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any, Optional
import streamlit as st
from datetime import datetime, timedelta
from src.utils.data_processing import generate_distinct_colors

def create_interactive_timeline(project_completion_estimates: pd.DataFrame) -> go.Figure:
    """
    Create an interactive timeline chart for project completion estimates.
    
    Args:
        project_completion_estimates: DataFrame with project completion estimates
        
    Returns:
        Plotly figure object
    """
    # Sort projects by estimated completion date
    sorted_projects = project_completion_estimates.sort_values('estimated_completion_date')
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for each project
    for i, project in sorted_projects.iterrows():
        project_name = project['project']
        
        # Skip projects with no estimated completion date or completed projects
        if pd.isna(project['estimated_completion_date']) or project['remaining_tasks'] == 0:
            continue
            
        # Determine color based on days difference between estimated and due date
        days_diff = project['days_difference'] if not pd.isna(project['days_difference']) else 0
        
        if days_diff > 90:
            color = 'red'  # 90+ days over schedule
        elif days_diff > 30:
            color = 'orange'  # 30-89 days over schedule
        else:
            color = 'green'  # Within 30 days of schedule
        
        # Format dates
        est_date = project['estimated_completion_date'].strftime('%Y-%m-%d') if not pd.isna(project['estimated_completion_date']) else 'Unknown'
        due_date = project['project_due_date'].strftime('%Y-%m-%d') if not pd.isna(project['project_due_date']) else 'No due date'
        
        # Add estimated completion date
        fig.add_trace(go.Scatter(
            x=[project['estimated_completion_date']],
            y=[project_name],
            mode='markers',
            marker=dict(size=15, color=color),
            name=f"{project_name} (Est: {est_date})",
            hovertemplate=f"<b>{project_name}</b><br>Estimated completion: {est_date}<br>Due date: {due_date}<br>Remaining tasks: {project['remaining_tasks']}<extra></extra>"
        ))
        
        # Add due date if available
        if not pd.isna(project['project_due_date']):
            fig.add_trace(go.Scatter(
                x=[project['project_due_date']],
                y=[project_name],
                mode='markers',
                marker=dict(size=15, color='blue', symbol='diamond'),
                name=f"{project_name} (Due: {due_date})",
                hovertemplate=f"<b>{project_name}</b><br>Due date: {due_date}<extra></extra>"
            ))
            
            # Add line connecting estimated and due dates
            fig.add_trace(go.Scatter(
                x=[project['estimated_completion_date'], project['project_due_date']],
                y=[project_name, project_name],
                mode='lines',
                line=dict(color=color, width=2, dash='dot'),
                showlegend=False,
                hoverinfo='none'
            ))
    
    # Add today's date line
    today = pd.Timestamp.now(tz='UTC')
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="gray")
    fig.add_annotation(x=today, y=len(sorted_projects), text="Today", showarrow=False, yshift=10)
    
    # Update layout
    fig.update_layout(
        title="Project Timeline",
        xaxis_title="Date",
        yaxis_title="Project",
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            type="date"
        )
    )
    
    return fig

def create_velocity_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a velocity chart showing tasks completed over time with curved lines
    and smoothed transitions. Includes a project selector to view individual projects.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        Plotly figure object
    """
    # Filter completed tasks
    completed_tasks = df[df['status'] == 'Completed'].copy()
    
    # Skip if no completed tasks
    if completed_tasks.empty:
        fig = go.Figure()
        fig.update_layout(
            title={
                'text': "Velocity Chart (No completed tasks)",
                'font': {'size': 24, 'color': '#333'},
                'y': 0.98,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="Week",
            yaxis_title="Tasks Completed",
            height=650,
            margin=dict(l=10, r=10, t=120, b=250),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='#e0e0e0',
            )
        )
        # Add a message when no data is available
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="No completed tasks found for the selected project",
            showarrow=False,
            font=dict(size=16, color="#666")
        )
        return fig
    
    # Convert to datetime and ensure timezone info
    if completed_tasks['completed_at'].dtype != 'datetime64[ns, UTC]':
        completed_tasks['completed_at'] = pd.to_datetime(completed_tasks['completed_at'], utc=True)
    
    # Group by week and project
    # First convert to datetime without timezone for consistent grouping
    completed_tasks['week'] = completed_tasks['completed_at'].dt.tz_localize(None).dt.to_period('W').dt.start_time
    weekly_completion = completed_tasks.groupby(['week', 'project']).size().reset_index(name='tasks_completed')
    
    # Generate distinct colors for projects
    projects = weekly_completion['project'].unique()
    colors = generate_distinct_colors(len(projects))
    color_map = dict(zip(projects, colors))
    
    # Create figure with white background
    fig = go.Figure()
    
    # Create project selector
    selected_projects = st.multiselect(
        "Select projects to display:",
        options=["All"] + sorted(projects.tolist()),
        default=["All"],
        key="velocity_chart_project_selector"
    )
    
    # Set visibility for each project based on selection
    show_all = "All" in selected_projects
    visible_projects = projects if show_all else [p for p in projects if p in selected_projects]
    
    # Apply smoothing to each project's data
    smoothed_project_data = {}
    for project in projects:
        project_data = weekly_completion[weekly_completion['project'] == project].sort_values('week')
        
        # If there are enough data points, apply smoothing
        if len(project_data) > 2:
            # Apply a rolling window for smoothing (with a window of 2 points)
            project_data = project_data.copy()
            project_data['smoothed_tasks'] = project_data['tasks_completed'].rolling(window=2, min_periods=1).mean()
        else:
            project_data['smoothed_tasks'] = project_data['tasks_completed']
            
        smoothed_project_data[project] = project_data
    
    # Add traces for each project with improved styling and curved lines
    for project in projects:
        project_data = smoothed_project_data[project]
        visible = project in visible_projects
        
        fig.add_trace(
            go.Scatter(
                x=project_data['week'],
                y=project_data['smoothed_tasks'],
                mode='lines+markers',
                name=project,
                line=dict(
                    width=2,
                    color=color_map[project],
                    shape='spline',  # Use spline for curved lines
                    smoothing=1.3    # Adjust smoothing level (0.5-1.3 works best)
                ),
                marker=dict(size=7, line=dict(width=1, color='white')),
                hovertemplate='<b>%{y:.1f}</b> tasks completed<br>Week of %{x}<extra>' + project + '</extra>',
                visible=True if visible else 'legendonly'  # Hide non-selected projects
            )
        )
    
    # Process total data with smoothing
    total_weekly = weekly_completion.groupby('week')['tasks_completed'].sum().reset_index()
    
    # Apply smoothing to total line
    if len(total_weekly) > 2:
        total_weekly['smoothed_tasks'] = total_weekly['tasks_completed'].rolling(window=3, min_periods=1).mean()
    else:
        total_weekly['smoothed_tasks'] = total_weekly['tasks_completed']
    
    # Add total line (always visible and more prominent)
    fig.add_trace(
        go.Scatter(
            x=total_weekly['week'],
            y=total_weekly['smoothed_tasks'],
            mode='lines+markers',
            name='Total (Team Velocity)',
            line=dict(
                width=4,
                dash='solid',
                color='black',
                shape='spline',  # Use spline for curved lines
                smoothing=1.3    # Adjust smoothing level
            ),
            marker=dict(size=10, color='black', line=dict(width=2, color='white')),
            hovertemplate='<b>%{y:.1f}</b> total tasks completed<br>Week of %{x}<extra>Team Velocity</extra>',
            visible=True  # Always visible
        )
    )
    
    # Update layout with improved styling for velocity chart
    fig.update_layout(
        title={
            'text': "Team Velocity (Tasks Completed per Week)",
            'font': {'size': 24, 'color': '#333'},
            'y': 0.98,  # Move title even higher
            'x': 0.5,   # Center the title
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Week",
        yaxis_title="Tasks Completed",
        height=650,  # Increase height further for velocity chart
        margin=dict(l=10, r=10, t=120, b=250),  # Increased bottom margin to accommodate lower legend position
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.45,  # Move legend even further down to avoid overlap with date text
            xanchor="center",
            x=0.5,  # Center the legend
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1,
            font=dict(size=10),  # Smaller font for legend to fit more items
            traceorder="normal",
            tracegroupgap=5,  # Reduce gap between legend groups
            itemsizing="constant",
            itemwidth=30,
            itemclick="toggle"
        ),
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            tickangle=-45,
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            zeroline=True,
            zerolinecolor='#e0e0e0',
            tickfont=dict(size=12)
        )
    )
    
    # Add shaded background for better readability
    fig.update_layout(
        shapes=[
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=1,
                y1=1,
                fillcolor="rgb(250,250,250)",
                opacity=0.5,
                layer="below",
                line_width=0,
            )
        ]
    )
    
    return fig

def create_burndown_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a burndown chart showing remaining tasks over time.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        Plotly figure object
    """
    # Check if dataframe is empty
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title={
                'text': "Burndown Chart (No data)",
                'font': {'size': 24, 'color': '#333'},
                'y': 0.98,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="Date",
            yaxis_title="Number of Tasks",
            height=600,
            margin=dict(l=10, r=10, t=120, b=150),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='#e0e0e0',
            )
        )
        # Add a message when no data is available
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="No data found for the selected project",
            showarrow=False,
            font=dict(size=16, color="#666")
        )
        return fig
    
    # Ensure datetime columns
    if df['created_at'].dtype != 'datetime64[ns, UTC]':
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    if df['completed_at'].dtype != 'datetime64[ns, UTC]':
        df['completed_at'] = pd.to_datetime(df['completed_at'], utc=True)
    
    # Get date range
    start_date = df['created_at'].min().date()
    end_date = pd.Timestamp.now(tz='UTC').date()
    
    # Create date range with timezone information
    date_range = pd.date_range(
        start=pd.Timestamp(start_date, tz='UTC'),
        end=pd.Timestamp(end_date, tz='UTC'),
        freq='D'
    )
    
    # Calculate cumulative tasks created and completed
    burndown_data = []
    
    for date in date_range:
        # Add one day to the date without changing timezone
        date_end = date + timedelta(days=1)
        created_until = df[df['created_at'] < date_end].shape[0]
        completed_until = df[(df['completed_at'] < date_end) & (df['status'] == 'Completed')].shape[0]
        remaining = created_until - completed_until
        
        burndown_data.append({
            'date': date,
            'remaining_tasks': remaining,
            'created_tasks': created_until,
            'completed_tasks': completed_until
        })
    
    burndown_df = pd.DataFrame(burndown_data)
    
    # Create figure with improved styling
    fig = go.Figure()
    
    # Add area for remaining tasks
    fig.add_trace(
        go.Scatter(
            x=burndown_df['date'],
            y=burndown_df['remaining_tasks'],
            mode='lines+markers',
            name='Remaining Tasks',
            line=dict(width=3, color='#1E88E5'),
            marker=dict(size=8, color='#1E88E5', line=dict(width=1, color='white')),
            fill='tozeroy',
            fillcolor='rgba(30, 136, 229, 0.2)',
            hovertemplate='<b>%{y}</b> remaining tasks<br>%{x|%Y-%m-%d}<extra></extra>'
        )
    )
    
    # Add created tasks line
    fig.add_trace(
        go.Scatter(
            x=burndown_df['date'],
            y=burndown_df['created_tasks'],
            mode='lines',
            name='Created Tasks',
            line=dict(width=2, color='#FFA000', dash='dot'),
            hovertemplate='<b>%{y}</b> created tasks<br>%{x|%Y-%m-%d}<extra></extra>'
        )
    )
    
    # Add completed tasks line
    fig.add_trace(
        go.Scatter(
            x=burndown_df['date'],
            y=burndown_df['completed_tasks'],
            mode='lines',
            name='Completed Tasks',
            line=dict(width=2, color='#43A047', dash='dot'),
            hovertemplate='<b>%{y}</b> completed tasks<br>%{x|%Y-%m-%d}<extra></extra>'
        )
    )
    
    # Add today's date line
    today = pd.Timestamp.now(tz='UTC')
    fig.add_vline(
        x=today, 
        line_width=2, 
        line_dash="dash", 
        line_color="rgba(0, 0, 0, 0.5)"
    )
    
    # Add today annotation separately instead of using annotation_text parameter
    fig.add_annotation(
        x=today,
        y=1.05,
        text="Today",
        showarrow=False,
        xref="x",
        yref="paper",
        font=dict(color="rgba(0, 0, 0, 0.5)", size=12)
    )
    
    # Update layout with improved styling
    fig.update_layout(
        title={
            'text': "Burndown Chart (Remaining Tasks)",
            'font': {'size': 24, 'color': '#333'},
            'y': 0.98,  # Move title even higher
            'x': 0.5,   # Center the title
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Date",
        yaxis_title="Number of Tasks",
        height=600,  # Increase height further to accommodate legend
        margin=dict(l=10, r=10, t=120, b=150),  # Increase bottom margin significantly
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.25,  # Move legend further down
            xanchor="center", 
            x=0.5,  # Center the legend
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            tickangle=-45,
            tickfont=dict(size=12),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all")
                ]),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='#e0e0e0',
                borderwidth=1
            )
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            zeroline=True,
            zerolinecolor='#e0e0e0',
            tickfont=dict(size=12)
        )
    )
    
    # Add annotations for key points
    if not burndown_df.empty:
        # Annotate start point
        fig.add_annotation(
            x=burndown_df['date'].iloc[0],
            y=burndown_df['remaining_tasks'].iloc[0],
            text="Start",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#1E88E5",
            ax=-40,
            ay=-40
        )
        
        # Annotate current point
        fig.add_annotation(
            x=burndown_df['date'].iloc[-1],
            y=burndown_df['remaining_tasks'].iloc[-1],
            text=f"Current: {burndown_df['remaining_tasks'].iloc[-1]} tasks",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#1E88E5",
            ax=40,
            ay=-40
        )
    
    return fig

def create_resource_allocation_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a resource allocation chart showing task distribution by assignee.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        Plotly figure object
    """
    # Convert dates to datetime and ensure timezone info
    if df['created_at'].dtype != 'datetime64[ns, UTC]':
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    
    # Filter to active tasks
    active_tasks = df[df['status'] != 'Completed'].copy()
    
    # Group by assignee and project
    resource_allocation = active_tasks.groupby(['assignee', 'project']).size().reset_index(name='task_count')
    
    # Sort by task count
    resource_allocation = resource_allocation.sort_values(['assignee', 'task_count'], ascending=[True, False])
    
    # Generate colors for projects
    projects = df['project'].unique()
    colors = generate_distinct_colors(len(projects))
    color_map = dict(zip(projects, colors))
    
    # Create figure
    fig = px.bar(
        resource_allocation,
        x='task_count',
        y='assignee',
        color='project',
        orientation='h',
        title="Resource Allocation (Active Tasks)",
        labels={'task_count': 'Number of Tasks', 'assignee': 'Team Member', 'project': 'Project'},
        color_discrete_map=color_map
    )
    
    # Update layout
    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode='stack',
        hovermode="y unified"
    )
    
    return fig

def create_task_status_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Create a pie chart showing task status distribution.
    
    Args:
        df: DataFrame of tasks
        
    Returns:
        Plotly figure object
    """
    # Count tasks by status
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    
    # Create figure
    fig = px.pie(
        status_counts,
        values='count',
        names='status',
        title="Task Status Distribution",
        color='status',
        color_discrete_map={'Completed': '#4CAF50', 'In Progress': '#FFC107'}
    )
    
    # Update layout
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    
    # Update traces
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    return fig

def create_project_progress_bars(project_details: List[Dict[str, Any]]) -> go.Figure:
    """
    Create progress bars for each project.
    
    Args:
        project_details: List of project details
        
    Returns:
        Plotly figure object
    """
    # Prepare data
    projects = []
    completion_percentages = []
    colors = []
    
    for project in project_details:
        total = project['total_tasks']
        completed = project['completed_tasks']
        
        if total > 0:
            percentage = (completed / total) * 100
        else:
            percentage = 0
            
        projects.append(project['name'])
        completion_percentages.append(percentage)
        
        # Determine color based on percentage
        if percentage < 33:
            colors.append('red')
        elif percentage < 66:
            colors.append('orange')
        else:
            colors.append('green')
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=completion_percentages,
        y=projects,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{p:.1f}%" for p in completion_percentages],
        textposition='auto',
        hovertemplate="<b>%{y}</b><br>Completion: %{x:.1f}%<extra></extra>"
    ))
    
    # Update layout
    fig.update_layout(
        title="Project Progress",
        xaxis=dict(
            title="Completion Percentage",
            range=[0, 100],
            tickvals=[0, 25, 50, 75, 100],
            ticktext=['0%', '25%', '50%', '75%', '100%']
        ),
        yaxis=dict(title="Project"),
        height=400,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    return fig 