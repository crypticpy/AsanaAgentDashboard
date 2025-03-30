"""
Fiscal year overview component for the Asana Portfolio Dashboard.
"""
import streamlit as st
from typing import Dict, Any, List, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.utils.fiscal_year import (
    get_fiscal_year, get_current_and_surrounding_fiscal_years,
    get_fiscal_year_quarters, calculate_quarterly_metrics,
    project_future_quarters, get_projects_by_status, calculate_velocity,
    get_fiscal_quarter, calculate_portfolio_health, calculate_project_health
)
from src.utils.fiscal_visualizations import (
    create_quarterly_performance_chart, create_fiscal_year_progress_chart,
    create_quarter_over_quarter_comparison, create_portfolio_health_chart,
    create_resource_utilization_heatmap
)
from streamlit_extras.metric_cards import style_metric_cards

def create_fiscal_year_selector() -> int:
    """
    Create a fiscal year selector.
    
    Returns:
        Selected fiscal year
    """
    # Get current fiscal year and surrounding years
    fiscal_years = get_current_and_surrounding_fiscal_years(5)  # Current year + 2 years before and after
    current_fy, _, _ = get_fiscal_year()
    
    # Format fiscal years for display
    fy_options = [f"FY{year}" for year in fiscal_years]
    
    # Find index of current fiscal year in options
    current_fy_index = fiscal_years.index(current_fy) if current_fy in fiscal_years else 0
    
    # Create selector
    st.write("### Fiscal Year")
    selected_fy_index = st.select_slider(
        "Select fiscal year",
        options=range(len(fy_options)),
        format_func=lambda i: fy_options[i],
        value=current_fy_index,
        key="fiscal_year_selector",
        label_visibility="collapsed"
    )
    
    # Get the actual fiscal year value
    selected_fiscal_year = fiscal_years[selected_fy_index]
    
    # Show fiscal year date range
    _, fy_start, fy_end = get_fiscal_year(pd.Timestamp(year=selected_fiscal_year-1, month=10, day=1, tz='UTC'))
    st.caption(f"October 1, {fy_start.year} - September 30, {fy_end.year}")
    
    return selected_fiscal_year

def create_fiscal_metrics(df: pd.DataFrame, project_estimates: pd.DataFrame, quarterly_metrics: Dict[str, Any], fiscal_year: int) -> None:
    """
    Create high-level fiscal year metrics.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
        quarterly_metrics: Dictionary with quarterly metrics
        fiscal_year: The selected fiscal year
    """
    # Get projects by status for this fiscal year
    projects_by_status = get_projects_by_status(df, project_estimates, fiscal_year)
    completed_projects = projects_by_status['completed']
    active_projects = projects_by_status['active']
    
    # Calculate portfolio health using new algorithm
    projects_list = []
    for _, project in project_estimates.iterrows():
        projects_list.append(project.to_dict())
    
    portfolio_health = calculate_portfolio_health(projects_list, df, fiscal_year)
    health_score = portfolio_health['health_score']
    health_description = portfolio_health['description']
    
    # Project metrics with clearer breakdown
    completed_count = len(completed_projects)
    active_count = len(active_projects)
    total_projects = completed_count + active_count
    
    # Task metrics with clearer breakdown
    completed_tasks = df[df['status'] == 'Completed'].shape[0]
    active_tasks = df[df['status'] != 'Completed'].shape[0]
    total_tasks = len(df)
    
    # Count unique team members (resources)
    total_resources = df['assignee'].nunique()
    
    # Create metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Projects",
            value=total_projects,
            delta=f"{completed_count} completed, {active_count} active",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="Tasks",
            value=total_tasks,
            delta=f"{completed_tasks} completed, {active_tasks} in progress",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="Team Members",
            value=total_resources,
            delta=None
        )
    
    with col4:
        st.metric(
            label="Portfolio Health",
            value=f"{health_score:.1f}%",
            delta=health_description,
            delta_color="normal" if health_score >= 70 else "inverse"
        )
    
    # Apply styling
    style_metric_cards()
    
    # Add velocity metric with timeframe context
    velocity = portfolio_health['team_velocity']
    st.caption(f"Team Velocity: {velocity:.2f} tasks per day (based on last 90 days)")

def create_quarterly_dashboard(df: pd.DataFrame, project_estimates: pd.DataFrame, quarterly_metrics: Dict[str, Any]) -> None:
    """
    Create the quarterly dashboard with improved metrics for Kanban/Scrum teams.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
        quarterly_metrics: Dictionary with quarterly metrics
    """
    # Show quarter performance metrics with more Kanban/Scrum-friendly title
    st.write("### Quarterly Performance Scorecard")
    
    # Get current date and fiscal quarter
    current_date = pd.Timestamp.now(tz='UTC')
    current_fy, current_quarter, _, _ = get_fiscal_quarter(current_date)
    
    # Calculate team velocity from recent history (last 90 days)
    velocity = calculate_velocity(df, window_days=90)
    
    # Add a comprehensive explanation about the quarterly performance view optimized for Kanban/Scrum
    st.caption("""
    This scorecard displays key agile metrics for each quarter. For past quarters, it shows actual completed work (throughput).
    For future quarters, projections are based on team velocity and current work in progress. The completion percentage represents 
    completed work relative to all work that flowed through the system during the quarter.
    """)
    
    # Extract quarters data
    quarters = quarterly_metrics.get('quarters', [])
    
    if quarters:
        # Create metrics for each quarter
        cols = st.columns(len(quarters))
        
        for i, quarter in enumerate(quarters):
            with cols[i]:
                # Check if this is projected data
                is_projected = quarter.get('is_projected', False)
                
                # Determine if this is the current quarter
                quarter_num = quarter.get('quarter')
                is_current_quarter = (current_fy == quarterly_metrics.get('fiscal_year', 0) and 
                                     current_quarter == quarter_num)
                
                # Set title with appropriate markers
                quarter_name = quarter.get('name', f"Q{quarter_num}")
                if is_projected and is_current_quarter:
                    title = f"**{quarter_name}** 📍 (Current)"
                elif is_projected:
                    title = f"**{quarter_name}** (Proj.)"
                else:
                    title = f"**{quarter_name}**"
                st.write(title)
                
                # Show completion rate (capped at 100%)
                completion_rate = min(quarter.get('completion_rate', 0), 100)
                
                # Use a progress bar with different styling based on quarter status
                if is_projected:
                    # Use a lighter color for projected data
                    status_color = "rgba(76, 175, 80, 0.5)"  # Light green for projections
                    text_color = "black"
                elif is_current_quarter:
                    # Use a distinctive color for current quarter
                    status_color = "#2196F3"  # Blue for current quarter
                    text_color = "white"
                else:
                    # Use a solid color for past quarters
                    status_color = "#4CAF50"  # Green for historical data
                    text_color = "white"
                
                # Create the progress bar with improved labeling
                if completion_rate >= 100:
                    # For 100% completion, show a special indicator
                    st.markdown(
                        f"""
                        <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 20px; margin-bottom: 10px;">
                            <div style="width: 100%; background-color: {status_color};
                                height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: {text_color}; font-weight: bold;">
                                {completion_rate:.1f}% ✓
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                elif is_projected and completion_rate > 95:
                    # For projected quarters with very high completion, add a note
                    st.markdown(
                        f"""
                        <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 20px; margin-bottom: 10px;">
                            <div style="width: {completion_rate}%; background-color: {status_color};
                                height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: {text_color}; font-weight: bold;">
                                {completion_rate:.1f}% (Projected)
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    # Add explanation for future quarter projections
                    if is_current_quarter:
                        st.caption("Completion for current quarter based on progress so far")
                    else:
                        st.caption("Projection based on team velocity and backlog")
                else:
                    # Normal progress bar
                    st.markdown(
                        f"""
                        <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 20px; margin-bottom: 10px;">
                            <div style="width: {completion_rate}%; background-color: {status_color};
                                height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: {text_color}; font-weight: bold;">
                                {completion_rate:.1f}%
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Get key metrics with meaningful names for Kanban/Scrum
                throughput = quarter.get('tasks_completed', 0)
                total_work = quarter.get('tasks_due', 0)
                incoming = quarter.get('tasks_created', 0)
                wip = quarter.get('tasks_in_progress', 0)
                
                # Show throughput/total with clearer explanation
                # For Kanban/Scrum, this represents completed tasks vs. total work that flowed through the system
                if is_projected:
                    st.markdown(f"**Throughput:** {throughput}/{total_work} (projected)")
                    # Add explanation about projections if the numbers look unusual
                    if throughput == total_work and is_current_quarter:
                        st.caption("These values match because projection is based on current progress")
                    elif throughput == total_work and not is_current_quarter:
                        st.caption("Projections are based on team velocity and estimated capacity")
                else:
                    # For past quarters show actual throughput data
                    completed_percentage = (throughput / total_work * 100) if total_work > 0 else 0
                    st.markdown(f"**Throughput:** {throughput}/{total_work} ({completed_percentage:.1f}%)")
                
                # Calculate and display daily throughput rate
                days_in_quarter = 91  # ~91 days per quarter
                if is_projected:
                    # For projected quarters, display as a range
                    daily_throughput = throughput / days_in_quarter if days_in_quarter > 0 else 0
                    st.markdown(f"**Daily Rate:** ~{daily_throughput:.2f} tasks/day")
                else:
                    # For past quarters, use actual data
                    actual_throughput = throughput / days_in_quarter if days_in_quarter > 0 else 0
                    st.markdown(f"**Daily Rate:** {actual_throughput:.2f} tasks/day")
                
                # Show WIP (work in progress) - key metric for Kanban
                # Add a visual indicator when WIP is non-zero
                if wip > 0:
                    st.markdown(f"**WIP:** {wip} tasks")
                else:
                    # For projected quarters with zero WIP, add explanation
                    if is_projected and quarter_num > 1:  # Not first quarter
                        st.markdown(f"**WIP:** {wip} tasks ⚠️")
                        st.caption("WIP should carry over from previous quarters")
                    else:
                        st.markdown(f"**WIP:** {wip} tasks")
                
                # Show WIP ratio - important for flow efficiency
                if throughput > 0:
                    wip_ratio = wip / throughput
                    if wip_ratio <= 1.5:
                        wip_status = "Good"
                        st.markdown(f"**WIP Ratio:** {wip_ratio:.1f} ({wip_status})")
                    else:
                        wip_status = "High"
                        st.markdown(f"**WIP Ratio:** {wip_ratio:.1f} ({wip_status}) ⚠️")
                
                # Show flow ratio (completed/incoming) - another key Kanban metric
                if incoming > 0:
                    flow_ratio = throughput / incoming
                    flow_status = "✅" if flow_ratio >= 1.0 else "⚠️"
                    st.markdown(f"**Flow Ratio:** {flow_ratio:.2f} {flow_status}")
                
                # Display team size
                team_size = quarter.get('active_resources', 0)
                st.markdown(f"**Team Size:** {team_size}")
                
                # Show project count
                projects_count = quarter.get('projects', 0)
                st.markdown(f"**Projects:** {projects_count}")
    else:
        st.info("No quarterly data available")
        
    # Add contextual information about Kanban/Scrum metrics
    with st.expander("⚙️ Understanding Agile Metrics"):
        st.markdown("""
        - **Throughput**: Number of completed tasks / Total work that flowed through the system
        - **Daily Rate**: Average tasks completed per day (velocity)
        - **WIP**: Work In Progress - tasks that are started but not completed
        - **WIP Ratio**: WIP divided by throughput (lower is better, <1.5 is good)
        - **Flow Ratio**: Throughput divided by incoming work (>1.0 means completing more than adding)
        
        For past quarters, metrics show actual performance. For future quarters (marked as "Proj."), 
        metrics are projections based on current velocity, WIP limits, and known work.
        """)

def create_project_status_overview(df: pd.DataFrame, project_estimates: pd.DataFrame, fiscal_year: int) -> None:
    """
    Create an aggregated view of project status.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
        fiscal_year: The fiscal year to filter by
    """
    # Calculate portfolio health
    projects_list = []
    for _, project in project_estimates.iterrows():
        projects_list.append(project.to_dict())
    
    portfolio_health = calculate_portfolio_health(projects_list, df, fiscal_year)
    status_counts = portfolio_health['status_counts']
    status_details = portfolio_health['status_details']
    
    st.write("### Project Status Overview")
    
    # Create two columns for the status overview
    col1, col2 = st.columns(2)
    
    with col1:
        # Create status distribution chart
        status_data = []
        
        # Format status counts for the pie chart
        for status, count in status_counts.items():
            if count > 0:
                status_data.append({"Status": status, "Count": count})
        
        # Create DataFrame
        status_df = pd.DataFrame(status_data)
        
        if not status_df.empty:
            # Create donut chart
            fig = px.pie(
                status_df, 
                values='Count', 
                names='Status',
                color='Status',
                hole=0.4,
                color_discrete_map={
                    'On Track': '#4CAF50',        # Green
                    'At Risk': '#FF9800',         # Orange
                    'Off Track': '#F44336',       # Red
                    'Completed On Time': '#2196F3',  # Blue
                    'Completed Late': '#9C27B0'   # Purple
                }
            )
            
            # Add total count in the center
            total_projects = sum(status_counts.values())
            fig.add_annotation(
                x=0.5, y=0.5,
                text=f"{total_projects}<br>Projects",
                font=dict(size=16, family="Arial", color="black"),
                showarrow=False
            )
            
            fig.update_layout(
                title="Project Status Distribution",
                height=300,
                margin=dict(l=10, r=10, t=50, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No project data available")
    
    with col2:
        # Create project health bar chart by velocity
        if status_details:
            # Group projects by velocity ranges for active projects
            velocity_data = []
            
            # Only include active projects (not completed)
            active_projects = [p for p in status_details if p['status'] not in ['Completed On Time', 'Completed Late']]
            
            if active_projects:
                # Define velocity ranges
                velocity_ranges = [
                    {"range": "Very Low (<0.1)", "min": 0, "max": 0.1, "color": "#F44336"},
                    {"range": "Low (0.1-0.25)", "min": 0.1, "max": 0.25, "color": "#FF9800"},
                    {"range": "Medium (0.25-0.5)", "min": 0.25, "max": 0.5, "color": "#FFEB3B"},
                    {"range": "High (0.5+)", "min": 0.5, "max": float('inf'), "color": "#4CAF50"}
                ]
                
                # Count projects in each velocity range
                for velocity_range in velocity_ranges:
                    count = sum(
                        velocity_range["min"] <= p['velocity'] < velocity_range["max"]
                        for p in active_projects
                    )
                    
                    if count > 0:
                        velocity_data.append({
                            "Velocity": velocity_range["range"],
                            "Count": count,
                            "Color": velocity_range["color"]
                        })
                
                # Create DataFrame
                velocity_df = pd.DataFrame(velocity_data)
                
                if not velocity_df.empty:
                    # Create horizontal bar chart
                    fig = go.Figure()
                    
                    # Sort by velocity (highest to lowest)
                    velocity_df = velocity_df.sort_values(by="Velocity", ascending=False)
                    
                    fig.add_trace(go.Bar(
                        x=velocity_df['Count'],
                        y=velocity_df['Velocity'],
                        orientation='h',
                        marker_color=velocity_df['Color'],
                        text=velocity_df['Count'],
                        textposition='auto'
                    ))
                    
                    # Add total active projects annotation
                    total_active = len(active_projects)
                    fig.add_annotation(
                        x=max(velocity_df['Count'].max() * 0.9, 1),
                        y=velocity_df['Velocity'].iloc[-1],
                        yshift=-40,
                        text=f"Total: {total_active} active projects",
                        showarrow=False,
                        font=dict(size=14, color="black"),
                        align="center"
                    )
                    
                    fig.update_layout(
                        title="Active Projects by Velocity",
                        height=300,
                        margin=dict(l=10, r=10, t=50, b=10),
                        xaxis_title="Number of Projects"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No velocity data available")
            else:
                st.info("No active projects")
        else:
            st.info("No project data available")
    
    # Add summarized statistics below the charts - focus on velocity and risk
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Count of projects at risk
        at_risk_count = status_counts.get('At Risk', 0)
        off_track_count = status_counts.get('Off Track', 0)
        total_active = sum(1 for p in status_details if p['status'] not in ['Completed On Time', 'Completed Late'])
        
        if total_active > 0:
            risk_percentage = ((at_risk_count + off_track_count) / total_active) * 100
            st.metric(
                label="Projects Needing Attention",
                value=f"{at_risk_count + off_track_count} of {total_active}",
                delta=f"{risk_percentage:.1f}% of active projects",
                delta_color="inverse"
            )
        else:
            st.metric(
                label="Projects Needing Attention",
                value="0 of 0",
                delta="No active projects",
                delta_color="normal"
            )
    
    with col2:
        # Average velocity among active projects
        active_projects = [p for p in status_details if p['status'] not in ['Completed On Time', 'Completed Late']]
        if active_projects:
            avg_velocity = sum(p['velocity'] for p in active_projects) / len(active_projects)
            
            # Calculate tasks per week for easier understanding
            tasks_per_week = avg_velocity * 7
            
            st.metric(
                label="Avg. Project Velocity",
                value=f"{avg_velocity:.2f} tasks/day",
                delta=f"{tasks_per_week:.1f} tasks/week",
                delta_color="normal"
            )
        else:
            st.metric(
                label="Avg. Project Velocity",
                value="N/A",
                delta="No active projects",
                delta_color="normal"
            )
    
    with col3:
        # Top risk reason
        if status_details:
            risk_reasons = {}
            for p in status_details:
                if p['status'] in ['At Risk', 'Off Track']:
                    reason = p['reason']
                    if "days behind" in reason:
                        reason = "Behind schedule"
                    elif "velocity" in reason:
                        reason = "Low velocity"
                    elif "overdue" in reason:
                        reason = "Overdue tasks"
                    elif "tasks" in reason and "defined" in reason:
                        reason = "No tasks defined"
                    
                    risk_reasons[reason] = risk_reasons.get(reason, 0) + 1
            
            if risk_reasons:
                top_reason = max(risk_reasons.items(), key=lambda x: x[1])
                st.metric(
                    label="Top Risk Factor",
                    value=top_reason[0],
                    delta=f"Affects {top_reason[1]} projects",
                    delta_color="inverse"
                )
            else:
                st.metric(
                    label="Top Risk Factor",
                    value="None",
                    delta="All projects on track",
                    delta_color="normal"
                )
        else:
            st.metric(
                label="Top Risk Factor",
                value="N/A",
                delta="No project data",
                delta_color="normal"
            )
    
    # Apply styling to metrics
    style_metric_cards()
    
    # Add a compact data table with high-level stats and improved health status
    if status_details:
        # Format for table display
        project_summary = []
        
        for project in status_details:
            # Format velocity for display
            velocity_str = f"{project['velocity']:.2f} tasks/day"
            
            # Add to summary
            project_summary.append({
                "Project": project['project'],
                "Status": project['status'],
                "Health Reason": project['reason'],
                "Velocity": velocity_str,
                "Remaining": project['remaining_tasks']
            })
        
        # Create DataFrame and sort by status (most critical first)
        summary_df = pd.DataFrame(project_summary)
        
        # Define status priority for sorting
        status_priority = {
            "Off Track": 0,
            "At Risk": 1,
            "On Track": 2,
            "Completed Late": 3,
            "Completed On Time": 4
        }
        
        # Sort by status priority
        if not summary_df.empty:
            summary_df['status_sort'] = summary_df['Status'].map(status_priority)
            summary_df = summary_df.sort_values('status_sort').drop('status_sort', axis=1)
            
            # Display the table with a height limit and horizontal scrolling
            st.caption("Projects Status Summary (sorted by risk level)")
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
                height=150  # Limited height to keep it compact
            )

def create_quarterly_charts(df: pd.DataFrame, project_estimates: pd.DataFrame,
                           quarterly_metrics: Dict[str, Any], fiscal_year: int) -> None:
    """
    Create charts for the quarterly dashboard.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
        quarterly_metrics: Dictionary with quarterly metrics
        fiscal_year: The fiscal year to show
    """
    # Create two columns for the main charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Create quarterly performance chart
        perf_fig = create_quarterly_performance_chart(quarterly_metrics)
        st.plotly_chart(perf_fig, use_container_width=True)
        
        # Add explainer for the quarterly performance chart
        with st.expander("📊 Understanding Quarterly Performance Metrics"):
            st.markdown("""
            This chart displays key metrics for each quarter:
            
            - **Throughput (Blue bars)**: Number of tasks completed in the quarter. Higher is better.
            - **WIP (Red bars)**: Work in Progress - tasks that were being worked on but not completed during the quarter. Lower is better.
            - **Completion Rate (Green line)**: Percentage of work that was completed vs. total work that flowed through the system.
            - **Flow Ratio (Orange dotted line)**: Ratio of completed tasks to incoming tasks. Values above 1.0 indicate the team is completing more than they're taking on, which is healthy.
            
            **Quarters with lighter colors are projections** based on current velocity and known future work.
            """)
    
    with col2:
        # Create quarter-over-quarter comparison
        comp_fig = create_quarter_over_quarter_comparison(quarterly_metrics)
        st.plotly_chart(comp_fig, use_container_width=True)
        
        # Add explainer for the quarter-over-quarter comparison
        with st.expander("📈 Understanding Quarter-over-Quarter Trends"):
            st.markdown("""
            This chart tracks key agile metrics across quarters:
            
            - **Incoming (Blue line)**: New tasks created during each quarter.
            - **Throughput (Orange line)**: Tasks completed each quarter.
            - **WIP (Red line)**: Work in Progress at each quarter end.
            - **Team Members (Green line)**: Number of active team members per quarter.
            
            **Ideal trends:**
            - Throughput (orange) should be equal to or greater than Incoming (blue), showing the team is keeping up with new work.
            - WIP (red) should trend downward or remain stable, indicating controlled work in progress.
            - Team size (green) should align with workload needs.
            
            **Quarters with lighter colors are projections** based on current velocity and known future work.
            """)
    
    # Create two columns for the health indicators
    col1, col2 = st.columns(2)
    
    with col1:
        # Create portfolio health chart
        health_fig = create_portfolio_health_chart(portfolio_metrics=portfolio_health,
                                                  project_estimates=project_estimates)
        st.plotly_chart(health_fig, use_container_width=True)
        
        # Add explainer for the portfolio health chart
        with st.expander("🔍 Understanding Portfolio Health Score"):
            st.markdown("""
            The Portfolio Health Score represents the overall health of your portfolio, calculated using:
            
            - **Project Status Distribution**: Proportion of projects that are On Track, At Risk, or Off Track
            - **Completion Rates**: How many projects are completing on time vs. late
            - **Team Velocity**: Average rate of task completion across the portfolio
            
            **Score Interpretation:**
            - **70-100%**: Healthy - Most projects on track, good velocity
            - **30-70%**: Caution - Some projects at risk, may need attention
            - **0-30%**: Critical - Significant issues, immediate action required
            """)
    
    with col2:
        # Create fiscal year progress chart
        progress_fig = create_fiscal_year_progress_chart(quarterly_metrics)
        st.plotly_chart(progress_fig, use_container_width=True)
        
        # Add explainer for the fiscal year progress chart
        with st.expander("📅 Understanding Fiscal Year Progress"):
            st.markdown("""
            This gauge shows your fiscal year completion progress:
            
            - **Completion Percentage**: How much of the planned work has been completed for the fiscal year
            - **Color Zones**: Red (0-30%), Orange (30-70%), and Green (70-100%) indicate health of progress
            - **Threshold Line**: The black line at 80% represents the target completion rate
            
            The annotations below the gauge show your total throughput (completed tasks) and current WIP (work in progress).
            """)
    
    # Create resource utilization heatmap
    st.write("### Team Member Utilization by Quarter")
    util_fig = create_resource_utilization_heatmap(df, fiscal_year)
    st.plotly_chart(util_fig, use_container_width=True)
    
    # Add explainer for the resource utilization heatmap
    with st.expander("👥 Understanding Team Utilization Heatmap"):
        st.markdown("""
        This heatmap shows how team members are utilized across quarters:
        
        - **Color Intensity**: Darker red indicates higher utilization (more tasks assigned)
        - **Task Count**: The number in each cell shows how many tasks were assigned to that person in that quarter
        - **Scale**: 100% utilization is defined as 10 tasks per quarter
        
        **Key insights to look for:**
        - **Uneven distribution**: Some team members may be overloaded while others are underutilized
        - **Capacity planning**: Identify quarters where overall utilization is too high or too low
        - **Resource allocation**: Use this data to better distribute work across the team
        
        For projected quarters, utilization is estimated based on current assignments and team velocity.
        """)

def create_fiscal_overview(df: pd.DataFrame, project_estimates: pd.DataFrame) -> None:
    """
    Create the fiscal year overview dashboard.
    
    Args:
        df: DataFrame of tasks
        project_estimates: DataFrame of project completion estimates
    """
    # Create fiscal year selector
    selected_fiscal_year = create_fiscal_year_selector()
    
    # Get quarterly metrics
    quarterly_metrics = project_future_quarters(df, project_estimates, selected_fiscal_year)
    
    # Calculate portfolio health
    projects_list = []
    for _, project in project_estimates.iterrows():
        projects_list.append(project.to_dict())
    
    # Calculate portfolio health once and store for all components
    global portfolio_health
    portfolio_health = calculate_portfolio_health(projects_list, df, selected_fiscal_year)
    
    # Create high-level metrics
    create_fiscal_metrics(df, project_estimates, quarterly_metrics, selected_fiscal_year)
    
    # Create quarterly dashboard
    create_quarterly_dashboard(df, project_estimates, quarterly_metrics)
    
    # Add project status overview (replacing individual cards with aggregate view)
    create_project_status_overview(df, project_estimates, selected_fiscal_year)
    
    # Create quarterly charts
    create_quarterly_charts(df, project_estimates, quarterly_metrics, selected_fiscal_year)
    
    # Add option to drill down to other tabs
    st.write("### Drill Down for More Details")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("View Projects Detail", use_container_width=True):
            st.session_state.current_tab = 1  # Set to Projects tab
            st.rerun()
    
    with col2:
        if st.button("View Tasks Detail", use_container_width=True):
            st.session_state.current_tab = 2  # Set to Tasks tab
            st.rerun()
    
    with col3:
        if st.button("View Resource Allocation", use_container_width=True):
            st.session_state.current_tab = 3  # Set to Resource Allocation tab
            st.rerun()