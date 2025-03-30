"""
Fiscal year visualization utilities for the Asana Portfolio Dashboard.

These utilities create visualizations for the fiscal year overview dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List, Optional
import streamlit as st
from src.utils.fiscal_year import get_fiscal_year_quarters, get_projects_by_status, calculate_portfolio_health

def create_quarterly_performance_chart(quarterly_metrics: Dict[str, Any]) -> go.Figure:
    """
    Create a chart showing quarterly performance with actual vs. projected data.
    Optimized for Kanban/Scrum methodologies.
    
    Args:
        quarterly_metrics: Dictionary with quarterly metrics
        
    Returns:
        Plotly figure object
    """
    # Extract quarters data
    quarters = quarterly_metrics.get('quarters', [])
    
    if not quarters:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="Quarterly Performance (No Data Available)",
            height=400
        )
        return fig
    
    # Prepare data for the chart
    quarter_names = []
    for q in quarters:
        quarter_num = q.get('quarter')
        quarter_name = q.get('name', f"Q{quarter_num}")
        quarter_names.append(quarter_name)
        
    # Get key agile metrics
    tasks_completed = [q.get('tasks_completed', 0) for q in quarters]
    tasks_in_progress = [q.get('tasks_in_progress', 0) for q in quarters]
    is_projected = [q.get('is_projected', False) for q in quarters]
    
    # Create figure
    fig = go.Figure()
    
    # Add bar for completed tasks (throughput) - primary agile metric
    fig.add_trace(go.Bar(
        x=quarter_names,
        y=tasks_completed,
        name='Throughput (Completed)',
        marker_color=['rgba(55, 126, 184, 0.7)' if not proj else 'rgba(55, 126, 184, 0.3)' for proj in is_projected],
        marker_line_color=['rgba(55, 126, 184, 1)' if not proj else 'rgba(55, 126, 184, 0.5)' for proj in is_projected],
        marker_line_width=1.5,
        opacity=0.8
    ))
    
    # Add bar for WIP (work in progress) - important Kanban metric
    fig.add_trace(go.Bar(
        x=quarter_names,
        y=tasks_in_progress,
        name='WIP (In Progress)',
        marker_color=['rgba(228, 26, 28, 0.7)' if not proj else 'rgba(228, 26, 28, 0.3)' for proj in is_projected],
        marker_line_color=['rgba(228, 26, 28, 1)' if not proj else 'rgba(228, 26, 28, 0.5)' for proj in is_projected],
        marker_line_width=1.5,
        opacity=0.8
    ))
    
    # Add line for completion rate (capped at 100%)
    completion_rates = [min(q.get('completion_rate', 0), 100) for q in quarters]
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=completion_rates,
        name='Completion Rate (%)',
        yaxis='y2',
        line=dict(color='rgb(77, 175, 74)', width=3),
        marker=dict(
            size=10,
            color=['rgb(77, 175, 74)' if not proj else 'rgba(77, 175, 74, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    # Calculate flow ratio (completed/created) for each quarter - key metric for Kanban teams
    flow_ratios = []
    for q in quarters:
        tasks_created = q.get('tasks_created', 0)
        tasks_completed = q.get('tasks_completed', 0)
        ratio = tasks_completed / tasks_created if tasks_created > 0 else 1
        # Cap at 2.0 for display purposes
        flow_ratios.append(min(ratio, 2.0))
    
    # Add line for flow ratio
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=flow_ratios,
        name='Flow Ratio',
        yaxis='y3',
        line=dict(color='rgb(255, 127, 14)', width=3, dash='dot'),
        marker=dict(
            size=10,
            color=['rgb(255, 127, 14)' if not proj else 'rgba(255, 127, 14, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    # Update layout with further improved legend positioning to prevent any overlaps
    fig.update_layout(
        title="Quarterly Performance (Agile Metrics)",
        xaxis_title="Quarter",
        yaxis_title="Number of Tasks",
        barmode='group',
        height=650,  # Significantly increased height
        margin=dict(l=10, r=40, t=180, b=150),  # Much larger margins
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",    # Anchor to top
            y=1.22,           # Positioned much higher above the chart
            xanchor="center", # Center-align the legend
            x=0.5,            # Center position
            itemsizing="constant",
            itemwidth=100,    # Much wider items to prevent overlap
            font=dict(size=10),
            traceorder="normal",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        ),
        yaxis2=dict(
            title="Completion Rate (%)",
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False  # Remove grid for secondary axis
        ),
        yaxis3=dict(
            title="Flow Ratio",
            overlaying="y",
            side="right",
            position=0.85,
            range=[0, 2],
            showgrid=False,
            tickvals=[0, 0.5, 1, 1.5, 2.0],
            ticktext=["0", "0.5", "1.0", "1.5", "2.0+"],
            tickmode="array"
        ),
        plot_bgcolor='white',
        yaxis=dict(
            gridcolor='lightgray',
            zerolinecolor='lightgray',
        )
    )
    
    # Add 'Projected' annotation to distinguish projected quarters
    if any(is_projected):
        fig.add_annotation(
            x=0.5,
            y=1.05,  # Position above legend
            xref="paper",
            yref="paper",
            text="Quarters with lighter colors are projections",
            showarrow=False,
            font=dict(size=10, color="gray"),
            align="center"
        )
    
    # Add annotation for Flow Ratio interpretation
    fig.add_annotation(
        x=1.0,
        y=0.5,
        xref="paper",
        yref="paper",
        text="Flow Ratio: >1.0 means completing more tasks than adding (good)",
        showarrow=False,
        font=dict(size=9, color="gray"),
        align="right",
        xshift=5
    )
    
    # Add comprehensive metrics explanation - positioned much lower to avoid overlap
    fig.add_annotation(
        x=0.5,
        y=-0.35,
        xref="paper",
        yref="paper",
        text="<b>Chart Guide:</b> Blue bars show completed work (Throughput). Red bars show in-progress work (WIP).<br>Green line shows Completion Rate (%). Orange dotted line shows Flow Ratio (lower is better).",
        showarrow=False,
        font=dict(size=10, color="#444"),
        align="center",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="rgba(0,0,0,0.1)",
        borderwidth=1,
        borderpad=6
    )
    
    return fig

def create_fiscal_year_progress_chart(quarterly_metrics: Dict[str, Any]) -> go.Figure:
    """
    Create a chart showing overall fiscal year progress.
    
    Args:
        quarterly_metrics: Dictionary with quarterly metrics
        
    Returns:
        Plotly figure object
    """
    # Extract fiscal year metrics
    fy_metrics = quarterly_metrics.get('fiscal_year_metrics', {})
    
    # Prepare data
    tasks_completed = fy_metrics.get('tasks_completed', 0)
    tasks_due = fy_metrics.get('tasks_due', 0)
    tasks_in_progress = fy_metrics.get('tasks_in_progress', 0)
    completion_rate = min(fy_metrics.get('completion_rate', 0), 100)  # Cap at 100%
    
    # Create figure
    fig = go.Figure()
    
    # Add gauge chart for completion rate
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=completion_rate,
        title={
            "text": "Fiscal Year Completion",
            "font": {"size": 14}
        },
        number={"suffix": "%", "font": {"size": 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': 'red'},
                {'range': [30, 70], 'color': 'orange'},
                {'range': [70, 100], 'color': 'green'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    
    # Update layout
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        font=dict(size=12, color="darkblue")
    )
    
    # Add a more descriptive caption for agile metrics
    fig.add_annotation(
        x=0.5,
        y=0,
        xref="paper",
        yref="paper",
        text=f"Throughput: {tasks_completed} completed / {tasks_due} total tasks",
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="center",
        yshift=-20
    )
    
    # Add WIP annotation
    fig.add_annotation(
        x=0.5,
        y=0,
        xref="paper",
        yref="paper",
        text=f"Current WIP: {tasks_in_progress} tasks in progress",
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="center",
        yshift=-40
    )
    
    return fig

def create_quarter_over_quarter_comparison(quarterly_metrics: Dict[str, Any]) -> go.Figure:
    """
    Create a chart comparing the performance of quarters using agile metrics.
    
    Args:
        quarterly_metrics: Dictionary with quarterly metrics
        
    Returns:
        Plotly figure object
    """
    # Extract quarters data
    quarters = quarterly_metrics.get('quarters', [])
    
    if not quarters:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="Quarter-over-Quarter Comparison (No Data Available)",
            height=400
        )
        return fig
    
    # Prepare data for the chart
    quarter_names = []
    for q in quarters:
        quarter_num = q.get('quarter')
        quarter_name = q.get('name', f"Q{quarter_num}")
        quarter_names.append(quarter_name)
    
    # For Kanban/Scrum metrics, focus on:
    # 1. Tasks Created (Incoming work)
    # 2. Tasks Completed (Throughput)
    # 3. Active Resources (Team capacity)
    # 4. Work in Progress (WIP)
    tasks_created = [q.get('tasks_created', 0) for q in quarters]
    tasks_completed = [q.get('tasks_completed', 0) for q in quarters]
    active_resources = [q.get('active_resources', 0) for q in quarters]
    tasks_in_progress = [q.get('tasks_in_progress', 0) for q in quarters]
    is_projected = [q.get('is_projected', False) for q in quarters]
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for each metric
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=tasks_created,
        name='Incoming (Created)',
        line=dict(color='rgb(31, 119, 180)', width=3),
        marker=dict(
            size=10,
            color=['rgb(31, 119, 180)' if not proj else 'rgba(31, 119, 180, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=tasks_completed,
        name='Throughput (Completed)',
        line=dict(color='rgb(255, 127, 14)', width=3),
        marker=dict(
            size=10,
            color=['rgb(255, 127, 14)' if not proj else 'rgba(255, 127, 14, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=tasks_in_progress,
        name='WIP (In Progress)',
        line=dict(color='rgb(214, 39, 40)', width=3),
        marker=dict(
            size=10,
            color=['rgb(214, 39, 40)' if not proj else 'rgba(214, 39, 40, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=quarter_names,
        y=active_resources,
        name='Team Members',
        line=dict(color='rgb(44, 160, 44)', width=3),
        marker=dict(
            size=10, 
            color=['rgb(44, 160, 44)' if not proj else 'rgba(44, 160, 44, 0.5)' for proj in is_projected],
            line=dict(width=2, color='white')
        )
    ))
    
    # Update layout with further improved legend positioning to prevent any overlaps
    fig.update_layout(
        title="Quarter-over-Quarter Agile Metrics",
        xaxis_title="Quarter",
        yaxis_title="Count",
        height=650,  # Significantly increased height
        margin=dict(l=10, r=40, t=180, b=150),  # Much larger margins
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",    # Anchor to top
            y=1.22,           # Positioned much higher above the chart
            xanchor="center", # Center-align the legend
            x=0.5,            # Center position
            itemsizing="constant",
            itemwidth=100,    # Much wider items to prevent overlap
            font=dict(size=10),
            traceorder="normal",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        ),
        plot_bgcolor='white',
        yaxis=dict(
            gridcolor='lightgray',
            zerolinecolor='lightgray',
        )
    )
    
    # Add 'Projected' annotation to distinguish projected quarters
    if any(is_projected):
        fig.add_annotation(
            x=0.5,
            y=1.05,  # Position above legend
            xref="paper",
            yref="paper",
            text="Quarters with lighter colors are projections",
            showarrow=False,
            font=dict(size=10, color="gray"),
            align="center"
        )
    
    # Move the ideal metrics text further up to eliminate any possible overlap
    fig.add_annotation(
        x=0.5,
        y=-0.20,
        xref="paper",
        yref="paper",
        text="Ideal: Throughput (orange) >= Incoming (blue), WIP (red) trending down",
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="center",
        bgcolor="rgba(255,255,255,0.7)",  # Add background to separate from other annotations
        borderpad=4
    )
    
    # Add comprehensive metrics explanation - positioned much lower to avoid overlap
    fig.add_annotation(
        x=0.5,
        y=-0.35,
        xref="paper",
        yref="paper",
        text="<b>Chart Guide:</b> Blue line shows incoming tasks. Orange line shows completed tasks.<br>Red line shows in-progress tasks. Green line shows team size.",
        showarrow=False,
        font=dict(size=10, color="#444"),
        align="center",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="rgba(0,0,0,0.1)",
        borderwidth=1,
        borderpad=6
    )
    
    return fig

def create_portfolio_health_chart(portfolio_metrics: Dict[str, Any] = None, project_estimates: pd.DataFrame = None) -> go.Figure:
    """
    Create a chart showing portfolio health indicators.
    
    Args:
        portfolio_metrics: Dictionary with portfolio health metrics (precomputed)
        project_estimates: DataFrame with project completion estimates (used if portfolio_metrics is None)
        
    Returns:
        Plotly figure object
    """
    # Check if we have portfolio_metrics
    if portfolio_metrics:
        health_score = portfolio_metrics['health_score']
        status_counts = portfolio_metrics['status_counts']
        description = portfolio_metrics['description']
    else:
        # Create a placeholder with default values
        health_score = 0
        status_counts = {
            "On Track": 0, 
            "At Risk": 0, 
            "Off Track": 0, 
            "Completed On Time": 0, 
            "Completed Late": 0
        }
        description = "No data"
    
    # Create figure
    fig = go.Figure()
    
    # Add gauge chart for health score
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=health_score,
        title={
            "text": "Portfolio Health Score",
            "font": {"size": 14}
        },
        number={"suffix": "%", "font": {"size": 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': 'red'},
                {'range': [30, 70], 'color': 'orange'},
                {'range': [70, 100], 'color': 'green'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    
    # Update layout
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        font=dict(size=12, color="darkblue")
    )
    
    # Get counts for status breakdown
    on_track_count = status_counts.get("On Track", 0)
    at_risk_count = status_counts.get("At Risk", 0)
    off_track_count = status_counts.get("Off Track", 0)
    completed_on_time = status_counts.get("Completed On Time", 0)
    completed_late = status_counts.get("Completed Late", 0)
    
    # Add caption with status breakdown
    status_text = f"On Track: {on_track_count} | At Risk: {at_risk_count} | Off Track: {off_track_count}"
    if completed_on_time > 0 or completed_late > 0:
        status_text += f"<br>Completed On Time: {completed_on_time} | Completed Late: {completed_late}"
    
    fig.add_annotation(
        x=0.5,
        y=0,
        xref="paper",
        yref="paper",
        text=status_text,
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="center",
        yshift=-20
    )
    
    # Add health status description
    fig.add_annotation(
        x=0.5,
        y=0.8,
        xref="paper",
        yref="paper",
        text=f"Status: {description}",
        showarrow=False,
        font=dict(size=12, color="black", family="Arial"),
        bgcolor="rgba(255, 255, 255, 0.7)",
        bordercolor="rgba(0, 0, 0, 0.2)",
        borderwidth=1,
        borderpad=4,
        align="center"
    )
    
    return fig

def create_resource_utilization_heatmap(df: pd.DataFrame, fiscal_year: int) -> go.Figure:
    """
    Create a heatmap showing resource utilization by quarter.
    
    Args:
        df: DataFrame of tasks
        fiscal_year: The fiscal year to show
        
    Returns:
        Plotly figure object
    """
    # Get quarters for the fiscal year
    quarters = get_fiscal_year_quarters(fiscal_year)
    
    # Ensure date columns are properly formatted
    if 'created_at' in df.columns and df['created_at'].dtype != 'datetime64[ns, UTC]':
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    
    # Initialize data
    resources = df['assignee'].unique()
    utilization_data = []
    
    # Calculate utilization for each resource in each quarter
    for quarter in quarters:
        start_date = quarter['start_date']
        end_date = quarter['end_date']
        quarter_name = quarter['name']
        
        # Get tasks in this quarter
        quarter_tasks = df[(df['created_at'] >= start_date) & (df['created_at'] <= end_date)]
        
        # Get task counts by assignee
        if not quarter_tasks.empty:
            resource_counts = quarter_tasks['assignee'].value_counts()
            
            for resource in resources:
                # Get task count for this resource (default to 0 if no tasks)
                task_count = resource_counts.get(resource, 0)
                
                # Calculate utilization percentage (assume 10 tasks = 100% utilization)
                utilization_pct = min(task_count / 10 * 100, 100)
                
                # Add to data
                utilization_data.append({
                    'Resource': resource,
                    'Quarter': quarter_name,
                    'Tasks': task_count,
                    'Utilization': utilization_pct
                })
    
    # Convert to DataFrame
    utilization_df = pd.DataFrame(utilization_data)
    
    # If no data, return empty figure
    if utilization_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Resource Utilization by Quarter (No Data Available)",
            height=400
        )
        return fig
    
    # Create pivot table for heatmap
    heatmap_data = utilization_df.pivot_table(
        values='Utilization', 
        index='Resource', 
        columns='Quarter', 
        aggfunc='mean'
    ).fillna(0)
    
    # Create improved heatmap with better readability
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Quarter", y="Team Member", color="Utilization (%)"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        color_continuous_scale='RdYlGn_r',  # Red for high utilization, green for low
        aspect="auto",
        title="Team Member Utilization by Quarter"
    )
    
    # Add annotations with the task count - improved readability
    for i, resource in enumerate(heatmap_data.index):
        for j, quarter in enumerate(heatmap_data.columns):
            task_count = utilization_df[
                (utilization_df['Resource'] == resource) &
                (utilization_df['Quarter'] == quarter)
            ]['Tasks'].values[0]
            
            # Make text more readable with background
            fig.add_annotation(
                x=j,
                y=i,
                text=f"{task_count}",  # Simplified text
                showarrow=False,
                font=dict(
                    color="white" if heatmap_data.iloc[i, j] > 50 else "black",
                    size=11,  # Larger font
                    family="Arial",
                    weight="bold"
                ),
                bgcolor="rgba(0,0,0,0.2)" if heatmap_data.iloc[i, j] <= 50 else "rgba(255,255,255,0.2)",  # Subtle background
                borderpad=2
            )
    
    # Update layout with improved readability and spacing
    fig.update_layout(
        height=max(450, len(heatmap_data.index) * 40),  # More space for each row
        margin=dict(l=20, r=80, t=60, b=50),  # More right margin for colorbar
        coloraxis_colorbar=dict(
            title=dict(
                text="Utilization (%)",
                side="right"
            ),
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            ticks="outside",
            ticklen=5,
            tickwidth=1,
            tickcolor="gray",
            x=1.02,  # Position colorbar further right
            len=0.8,  # Shorter colorbar
            y=0.5   # Center vertically
        )
    )
    
    # Add annotation explaining the scale - simpler version
    fig.add_annotation(
        x=0.5,
        y=-0.15,
        xref="paper",
        yref="paper",
        text="Numbers in cells = task count per quarter | 100% utilization = 10 tasks per quarter",
        showarrow=False,
        font=dict(size=11, color="gray"),
        align="center"
    )
    
    return fig