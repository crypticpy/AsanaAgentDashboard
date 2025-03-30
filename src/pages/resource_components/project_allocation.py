"""
Project Allocation Component for Resource Allocation Page.

This module provides visualizations and metrics for project resource allocation,
including team allocation, task distribution, and resource utilization by project.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime, timedelta

def create_project_allocation_metrics(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create project allocation metrics and visualizations.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    st.markdown("### Project Resource Allocation")
    # Add a dashboard-style summary at the top - industry standard overview
    if not df.empty:
        create_resource_allocation_summary(df)
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Add explanation for the visualization options
    with st.expander("About Resource Allocation Visualizations"):
        st.markdown("""
        **Resource Allocation Visualization Options:**
        
        - **Stacked Bar Chart**: The most common industry-standard format for resource allocation reporting.
          Shows the distribution of team members across projects, with each color representing a different team member.
          This view makes it easy to see which projects have the most resources and how team members are distributed.
          
        - **Heatmap**: Provides a visual intensity map showing the concentration of resources.
          Darker colors indicate more tasks allocated to a particular team member-project combination.
          This view is excellent for quickly identifying hotspots and areas of high resource concentration.
          
        - **Detailed Table**: A comprehensive tabular view with color coding to show allocation intensity.
          Perfect for precise planning and resource balancing, as it shows the exact number of tasks
          assigned to each team member for each project.
        """)
    
    # Create project resource allocation visualization
    create_project_resource_allocation(df)
    
    # Create project health indicators
    create_project_health_indicators(df, project_details)

def create_project_resource_allocation(df: pd.DataFrame) -> None:
    """
    Create resource allocation visualization by project.
    
    Args:
        df: DataFrame with task data
    """
    # Get project filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_project = filters.get("project", "All Projects")
    
    # If a specific project is selected, show team allocation for that project
    if selected_project != "All Projects":
        # Filter for the selected project
        project_df = df[df["project"] == selected_project]
        
        # Get team member counts
        team_member_counts = project_df.groupby("assignee").size().reset_index(name="count")
        team_member_counts.columns = ["Team Member", "Task Count"]
        
        # Sort by task count
        team_member_counts = team_member_counts.sort_values("Task Count", ascending=False)
        
        # Create visualization
        if not team_member_counts.empty:
            fig = px.bar(
                team_member_counts,
                x="Team Member",
                y="Task Count",
                title=f"Team Allocation for {selected_project}",
                height=400,
                color="Task Count",
                color_continuous_scale="Viridis"
            )
            
            # Update layout
            fig.update_layout(
                xaxis_title="Team Member",
                yaxis_title="Number of Tasks"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No team allocation data available for {selected_project}.")
    else:
        # Show resource allocation across all projects
        # Group by project and assignee
        project_allocation = df.groupby(["project", "assignee"]).size().reset_index(name="count")
        
        # Create visualization
        if not project_allocation.empty:
            # Create visualization options (tabs)
            tab1, tab2, tab3, tab4 = st.tabs(["Stacked Bar Chart", "Heatmap", "Resource Timeline", "Detailed Table"])
            
            with tab1:
                # Create a stacked bar chart - industry standard for resource allocation
                # First, pivot the data to get projects as rows and assignees as columns
                pivot_df = project_allocation.pivot_table(
                    index="project",
                    columns="assignee",
                    values="count",
                    aggfunc="sum",
                    fill_value=0
                ).reset_index()
                
                # Melt the data for Plotly
                melted_df = pd.melt(
                    pivot_df,
                    id_vars=["project"],
                    var_name="assignee",
                    value_name="count"
                )
                
                # Sort projects by total task count
                project_totals = melted_df.groupby("project")["count"].sum().reset_index()
                project_totals = project_totals.sort_values("count", ascending=False)
                
                # Create stacked bar chart
                fig = px.bar(
                    melted_df,
                    x="project",
                    y="count",
                    color="assignee",
                    title="Resource Allocation by Project",
                    height=500,
                    labels={"project": "Project", "count": "Number of Tasks", "assignee": "Team Member"},
                    category_orders={"project": project_totals["project"].tolist()}
                )
                
                # Update layout for better readability
                fig.update_layout(
                    xaxis_title="Project",
                    yaxis_title="Number of Tasks",
                    legend_title="Team Member",
                    barmode="stack",
                    xaxis={'categoryorder': 'total descending'},
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                # Create a heatmap - great for showing allocation intensity
                # First, pivot the data to get projects as rows and assignees as columns
                heatmap_df = project_allocation.pivot_table(
                    index="project",
                    columns="assignee",
                    values="count",
                    aggfunc="sum",
                    fill_value=0
                )
                
                # Sort by total allocation
                heatmap_df = heatmap_df.loc[heatmap_df.sum(axis=1).sort_values(ascending=False).index]
                
                # Create heatmap
                fig = px.imshow(
                    heatmap_df,
                    labels=dict(x="Team Member", y="Project", color="Tasks Allocated"),
                    title="Resource Allocation Intensity",
                    height=500,
                    color_continuous_scale="Viridis"
                )
                
                # Update layout for better readability
                fig.update_layout(
                    xaxis_title="Team Member",
                    yaxis_title="Project"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                # Create a timeline view - industry standard for resource allocation over time
                # First, reorganize the data for timeline format
                timeline_data = []
                
                # Get unique team members and projects
                team_members = project_allocation["assignee"].unique()
                projects = project_allocation["project"].unique()
                
                # Create a color mapping for projects
                project_colors = {}
                color_scale = px.colors.qualitative.Bold
                for i, project in enumerate(projects):
                    project_colors[project] = color_scale[i % len(color_scale)]
                
                # For each team member, create a row with bars representing their project allocations
                for member in team_members:
                    member_projects = project_allocation[project_allocation["assignee"] == member]
                    
                    for _, row in member_projects.iterrows():
                        # Skip if count is 0
                        if row["count"] == 0:
                            continue
                            
                        # Add a timeline item
                        timeline_data.append({
                            "Team Member": row["assignee"],
                            "Project": row["project"],
                            "Start": 0,  # We don't have actual start dates, so use relative positions
                            "Duration": row["count"],  # Use task count as duration
                            "Count": row["count"],  # Store the actual count for the hover text
                            "Color": project_colors[row["project"]]
                        })
                
                # Convert to DataFrame
                timeline_df = pd.DataFrame(timeline_data)
                
                if not timeline_df.empty:
                    # Create figure
                    fig = go.Figure()
                    
                    # Sort team members by total allocation
                    member_totals = timeline_df.groupby("Team Member")["Duration"].sum().sort_values(ascending=False)
                    sorted_members = member_totals.index.tolist()
                    
                    # Calculate cumulative durations for each member to position bars
                    timeline_df["Cumulative"] = timeline_df.groupby("Team Member")["Duration"].cumsum() - timeline_df["Duration"]
                    
                    # Add bars for each project allocation
                    for idx, row in timeline_df.iterrows():
                        fig.add_trace(go.Bar(
                            x=[row["Duration"]],
                            y=[row["Team Member"]],
                            orientation='h',
                            name=row["Project"],
                            marker=dict(color=row["Color"]),
                            hoverinfo="text",
                            hovertext=f"<b>{row['Project']}</b><br>{row['Count']} tasks",
                            base=row["Cumulative"],  # Starting position for the bar
                            showlegend=True,
                            legendgroup=row["Project"]
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title="Resource Allocation Timeline",
                        barmode='stack',
                        height=max(500, len(sorted_members) * 30),  # Adjust height based on number of team members
                        yaxis=dict(
                            categoryorder='array',
                            categoryarray=sorted_members,
                            title="Team Member"
                        ),
                        xaxis=dict(
                            title="Task Allocation",
                            showgrid=True,
                            gridwidth=1,
                            gridcolor='rgba(211, 211, 211, 0.5)'
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5,
                            title="Projects"
                        ),
                        hovermode="closest"
                    )
                    
                    # De-duplicate legend items (show each project only once)
                    seen_projects = set()
                    for trace in fig.data:
                        if trace.name in seen_projects:
                            trace.showlegend = False
                        else:
                            seen_projects.add(trace.name)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add description
                    st.markdown("""
                    <div style="margin-top: -15px; margin-bottom: 15px; font-size: 0.9em; color: #666;">
                    This timeline visualization shows how team members are allocated across projects.
                    Each bar represents tasks assigned to a team member for a specific project.
                    Longer bars indicate more tasks assigned.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No timeline data available.")
            
            with tab4:
                # Create a detailed table view with conditional formatting
                # First, pivot the data to get projects as rows and assignees as columns
                table_df = project_allocation.pivot_table(
                    index="project",
                    columns="assignee",
                    values="count",
                    aggfunc="sum",
                    fill_value=0
                ).reset_index()
                
                # Add a Total column - exclude the 'project' column from the sum
                numeric_cols = table_df.columns.drop('project')
                table_df["Total"] = table_df[numeric_cols].sum(axis=1)
                
                # Sort by total
                table_df = table_df.sort_values("Total", ascending=False)
                
                # Create a custom formatted table
                fig = go.Figure(data=[go.Table(
                    header=dict(
                        values=["Project"] + table_df.columns.tolist()[1:],
                        fill_color='#2F4F4F',
                        font=dict(color='white', size=12),
                        align=['left'] + ['center'] * (len(table_df.columns) - 1)
                    ),
                    cells=dict(
                        values=[table_df["project"]] + [table_df[col] for col in table_df.columns[1:]],
                        fill_color=[
                            ['#F8F8F8'] * len(table_df)
                        ] + [
                            ['#E0F7FA' if v == 0 else
                             '#B2DFDB' if v <= 2 else
                             '#4DB6AC' if v <= 5 else
                             '#00796B' if v <= 10 else '#004D40'
                             for v in table_df[col]]
                            for col in table_df.columns[1:]
                        ],
                        font=dict(color='black', size=11),
                        align=['left'] + ['center'] * (len(table_df.columns) - 1),
                        format=[None] + [None] * (len(table_df.columns) - 1)
                    )
                )])
                
                # Update layout
                fig.update_layout(
                    title="Detailed Resource Allocation Table",
                    height=500,
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add legend for color coding
                st.markdown("""
                <div style="display: flex; align-items: center; margin-top: -15px;">
                    <div style="display: flex; align-items: center; margin-right: 15px;">
                        <div style="width: 15px; height: 15px; background-color: #E0F7FA; margin-right: 5px;"></div>
                        <span>0 tasks</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-right: 15px;">
                        <div style="width: 15px; height: 15px; background-color: #B2DFDB; margin-right: 5px;"></div>
                        <span>1-2 tasks</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-right: 15px;">
                        <div style="width: 15px; height: 15px; background-color: #4DB6AC; margin-right: 5px;"></div>
                        <span>3-5 tasks</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-right: 15px;">
                        <div style="width: 15px; height: 15px; background-color: #00796B; margin-right: 5px;"></div>
                        <span>6-10 tasks</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 15px; height: 15px; background-color: #004D40; margin-right: 5px;"></div>
                        <span>10+ tasks</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No resource allocation data available.")

def create_project_health_indicators(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create project health indicators based on resource allocation and task completion.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    # Calculate project health metrics
    project_health = calculate_project_health(df, project_details)
    
    # Create visualization
    if project_health:
        # Convert to DataFrame
        health_df = pd.DataFrame(project_health)
        
        # Add filter options for the health matrix
        st.markdown("#### Filter Project Health Matrix")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            health_filter = st.radio(
                "Filter by health status:",
                ["All Projects", "Critical Only", "At Risk Only", "Inefficient Only", "Healthy Only"],
                horizontal=True
            )
        
        with col2:
            min_tasks = st.slider("Minimum tasks", 0, int(health_df["total_tasks"].max()) if not health_df.empty else 10, 0)
        
        with col3:
            show_labels = st.checkbox("Show project labels", value=True)
        
        # Apply filters
        filtered_df = health_df.copy()
        if health_filter == "Critical Only":
            filtered_df = filtered_df[(filtered_df['resource_allocation'] < 50) & (filtered_df['completion_rate'] < 50)]
        elif health_filter == "At Risk Only":
            filtered_df = filtered_df[(filtered_df['resource_allocation'] < 50) & (filtered_df['completion_rate'] >= 50)]
        elif health_filter == "Inefficient Only":
            filtered_df = filtered_df[(filtered_df['resource_allocation'] >= 50) & (filtered_df['completion_rate'] < 50)]
        elif health_filter == "Healthy Only":
            filtered_df = filtered_df[(filtered_df['resource_allocation'] >= 50) & (filtered_df['completion_rate'] >= 50)]
        
        # Filter by minimum tasks
        if min_tasks > 0:
            filtered_df = filtered_df[filtered_df["total_tasks"] >= min_tasks]
        
        # Show a message if no projects match the filters
        if filtered_df.empty:
            st.warning("No projects match the selected filters. Try adjusting your criteria.")
            return
            
        # Create visualization options with tabs
        tabs = st.tabs(["Matrix View", "Bubble Chart View", "Edge Projects Focus"])
        
        with tabs[0]:
            # Create a more readable visualization (Matrix)
            fig = go.Figure()
        
            # Add quadrant backgrounds for better visual interpretation
            fig.add_shape(
                type="rect",
                x0=0, y0=50,
                x1=50, y1=100,
                line=dict(width=0),
                fillcolor="rgba(255, 230, 230, 0.3)",  # Light red
                layer="below"
            )
            fig.add_shape(
                type="rect",
                x0=50, y0=50,
                x1=100, y1=100,
                line=dict(width=0),
                fillcolor="rgba(230, 255, 230, 0.3)",  # Light green
                layer="below"
            )
            fig.add_shape(
                type="rect",
                x0=0, y0=0,
                x1=50, y1=50,
                line=dict(width=0),
                fillcolor="rgba(255, 200, 200, 0.3)",  # Darker red
                layer="below"
            )
            fig.add_shape(
                type="rect",
                x0=50, y0=0,
                x1=100, y1=50,
                line=dict(width=0),
                fillcolor="rgba(255, 230, 180, 0.3)",  # Light orange
                layer="below"
            )
            
            # Add quadrant labels
            fig.add_annotation(
                x=25, y=75,
                text="AT RISK<br>Efficient but<br>under-resourced",
                showarrow=False,
                font=dict(size=10, color="rgba(0,0,0,0.5)"),
                align="center"
            )
            fig.add_annotation(
                x=75, y=75,
                text="HEALTHY<br>Well resourced<br>and productive",
                showarrow=False,
                font=dict(size=10, color="rgba(0,0,0,0.5)"),
                align="center"
            )
            fig.add_annotation(
                x=25, y=25,
                text="CRITICAL<br>Under-resourced<br>and struggling",
                showarrow=False,
                font=dict(size=10, color="rgba(0,0,0,0.5)"),
                align="center"
            )
            fig.add_annotation(
                x=75, y=25,
                text="INEFFICIENT<br>Well resourced<br>but low productivity",
                showarrow=False,
                font=dict(size=10, color="rgba(0,0,0,0.5)"),
                align="center"
            )
            
            # Add grid
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(211, 211, 211, 0.5)',
                zeroline=False
            )
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(211, 211, 211, 0.5)',
                zeroline=False
            )
            
            # Group projects by proximity to handle overlapping
            # First sort by health score to prioritize showing critical projects
            sorted_df = filtered_df.sort_values(['health_score'])
            
            # Create bins for resource allocation and completion rate to identify nearby projects
            sorted_df['ra_bin'] = pd.cut(sorted_df['resource_allocation'], bins=10)
            sorted_df['cr_bin'] = pd.cut(sorted_df['completion_rate'], bins=10)
            
            # Group projects that are in the same "bin" area
            bin_groups = sorted_df.groupby(['ra_bin', 'cr_bin'])
            
            # Dictionary to track used positions
            used_positions = {}
            
            # Add scatter points
            for name, group in bin_groups:
                # For groups with multiple projects in same area, apply jitter and different text positions
                group_size = len(group)
                
                for i, (idx, row) in enumerate(group.iterrows()):
                    # Determine color based on health score
                    if row['health_score'] >= 67:
                        color = 'rgb(0, 128, 0)'  # Green
                    elif row['health_score'] >= 34:
                        color = 'rgb(255, 165, 0)'  # Orange
                    else:
                        color = 'rgb(255, 0, 0)'  # Red
                    
                    # Calculate marker size based on total_tasks (normalized)
                    # Use filtered_df for normalization to ensure proper scaling with filters
                    max_tasks = filtered_df['total_tasks'].max()
                    # Ensure minimum size of 12 and max of 35 for better visibility in expanded chart
                    size = min(35, max(12, 8 + (row['total_tasks'] / max(max_tasks, 1) * 27)))
                    
                    # Apply jitter for overlapping points
                    jitter_x = 0
                    jitter_y = 0
                    
                    if group_size > 1:
                        # Apply jitter (more for larger groups)
                        jitter_x = (i % 3 - 1) * 2  # -2, 0, or 2
                        jitter_y = ((i // 3) % 3 - 1) * 2  # -2, 0, or 2
                    
                    # Cycle through different text positions for groups
                    positions = ["top center", "top right", "top left", "bottom center", "bottom right", "bottom left"]
                    text_pos = positions[i % len(positions)] if group_size > 1 else "top center"
                    
                    # Adjust opacity for better visibility
                    if row['health_score'] < 34:  # Critical projects
                        opacity = 0.9
                        line_width = 2
                    else:
                        opacity = 0.8
                        line_width = 1
                    
                    # Add project node
                    fig.add_trace(go.Scatter(
                        x=[row['resource_allocation'] + jitter_x],
                        y=[row['completion_rate'] + jitter_y],
                        mode='markers+text' if show_labels else 'markers',
                        marker=dict(
                            size=size,
                            color=color,
                            opacity=opacity,
                            line=dict(width=line_width, color='white'),
                            symbol='circle'
                        ),
                        name=row['project'],
                        text=row['project'],
                        textposition=text_pos,
                        textfont=dict(size=10, color='rgba(0,0,0,0.7)'),
                        hoverinfo='text',
                        hovertext=(f"<b>{row['project']}</b><br>"
                                  f"Resource Allocation: {row['resource_allocation']:.1f}<br>"
                                  f"Completion Rate: {row['completion_rate']:.1f}%<br>"
                                  f"Health Score: {row['health_score']:.1f}<br>"
                                  f"Total Tasks: {row['total_tasks']}<br>"
                                  f"Team Members: {row['team_members']}")
                    ))
            
            # Add reference lines
            fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
            
            # Update layout
            fig.update_layout(
                title={
                    'text': "Project Health Matrix",
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': dict(size=20)
                },
                xaxis_title="Resource Allocation Score (higher = better allocated)",
                yaxis_title="Task Completion Rate (%)",
                xaxis=dict(range=[0, 105], dtick=10),  # Expanded range to show edge case projects
                yaxis=dict(range=[0, 105], dtick=10),  # Expanded range for y-axis as well
                height=600,
                hovermode="closest",
                showlegend=False,
                margin=dict(t=80, b=80, l=80, r=80)
            )
            
            # Show health matrix with download option
            st.plotly_chart(fig, use_container_width=True)
            
            # Create a summary of projects by quadrant - using filtered data
            q1_count = len(filtered_df[(filtered_df['resource_allocation'] < 50) & (filtered_df['completion_rate'] >= 50)])  # AT RISK
            q2_count = len(filtered_df[(filtered_df['resource_allocation'] >= 50) & (filtered_df['completion_rate'] >= 50)])  # HEALTHY
            q3_count = len(filtered_df[(filtered_df['resource_allocation'] < 50) & (filtered_df['completion_rate'] < 50)])   # CRITICAL
            q4_count = len(filtered_df[(filtered_df['resource_allocation'] >= 50) & (filtered_df['completion_rate'] < 50)])  # INEFFICIENT
            
            # Create UI columns for the summary and legend
            col1, col2 = st.columns([3, 2])
            
            with col1:
                # Add legend for health score colors
                st.markdown("""
                <div style="display: flex; justify-content: flex-start; margin-top: -20px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; margin-right: 20px;">
                        <div style="width: 15px; height: 15px; background-color: rgb(255, 0, 0); margin-right: 5px; border-radius: 50%;"></div>
                        <span>Poor Health (0-33)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-right: 20px;">
                        <div style="width: 15px; height: 15px; background-color: rgb(255, 165, 0); margin-right: 5px; border-radius: 50%;"></div>
                        <span>Moderate Health (34-66)</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 15px; height: 15px; background-color: rgb(0, 128, 0); margin-right: 5px; border-radius: 50%;"></div>
                        <span>Good Health (67-100)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Display quadrant summary
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: -20px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Project Summary:</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr;">
                        <div style="padding: 5px; border-right: 1px solid #eee; border-bottom: 1px solid #eee; color: #ff9999;">CRITICAL: {q3_count}</div>
                        <div style="padding: 5px; border-bottom: 1px solid #eee; color: #ffcc99;">INEFFICIENT: {q4_count}</div>
                        <div style="padding: 5px; border-right: 1px solid #eee; color: #ffaa99;">AT RISK: {q1_count}</div>
                        <div style="padding: 5px; color: #99cc99;">HEALTHY: {q2_count}</div>
                    </div>
                    <div style="font-size: 0.8em; margin-top: 5px;">Total Projects: {len(filtered_df)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Add download button for the data
            csv = health_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download Project Health Data",
                data=csv,
                file_name="project_health_matrix.csv",
                mime="text/csv",
                help="Download the project health data as a CSV file for further analysis"
            )
            
        with tabs[1]:
            # Create a bubble chart visualization - industry standard for resource allocation
            bubble_fig = go.Figure()
            
            # Add data points for each project
            for index, row in filtered_df.iterrows():
                project_name = row['project']
                resource_allocation = row['resource_allocation']
                completion_rate = row['completion_rate']
                total_tasks = row['total_tasks']
                health_score = row['health_score']
                team_count = row['team_members']
                
                # Determine color based on health score
                if health_score < 33:
                    marker_color = 'rgb(255, 0, 0)'  # Red
                elif health_score < 67:
                    marker_color = 'rgb(255, 165, 0)'  # Orange
                else:
                    marker_color = 'rgb(0, 128, 0)'  # Green
                
                # Calculate size based on total tasks
                size = min(50, max(20, 15 + (total_tasks / max(filtered_df['total_tasks'].max(), 1) * 35)))
                
                # Add bubble for this project
                bubble_fig.add_trace(go.Scatter(
                    x=[resource_allocation],
                    y=[completion_rate],
                    mode='markers+text' if show_labels else 'markers',
                    name=project_name,
                    text=[project_name] if show_labels else None,
                    textposition="top center",
                    textfont=dict(size=10),
                    marker=dict(
                        size=size,
                        color=marker_color,
                        opacity=0.7,
                        line=dict(width=1, color='DarkSlateGrey')
                    ),
                    hoverinfo='text',
                    hovertext=(f"<b>{project_name}</b><br>"
                              f"Resource Allocation: {resource_allocation:.1f}<br>"
                              f"Completion Rate: {completion_rate:.1f}%<br>"
                              f"Total Tasks: {total_tasks}<br>"
                              f"Team Members: {team_count}<br>"
                              f"Health Score: {health_score:.1f}")
                ))
            
            # Configure the layout for the bubble chart
            bubble_fig.update_layout(
                title="Project Resource Allocation vs. Completion Rate",
                xaxis=dict(
                    title="Resource Allocation Score",
                    range=[0, 105],
                    dtick=10,
                    gridcolor='LightGrey'
                ),
                yaxis=dict(
                    title="Task Completion Rate (%)",
                    range=[0, 105],
                    dtick=10,
                    gridcolor='LightGrey'
                ),
                # Add quadrant lines
                shapes=[
                    # Vertical line at x=50
                    dict(
                        type="line",
                        x0=50, y0=0, x1=50, y1=105,
                        line=dict(color="grey", width=1, dash="dash")
                    ),
                    # Horizontal line at y=50
                    dict(
                        type="line",
                        x0=0, y0=50, x1=105, y1=50,
                        line=dict(color="grey", width=1, dash="dash")
                    ),
                ],
                # Add quadrant annotations
                annotations=[
                    dict(x=25, y=75, text="AT RISK<br>Efficient but<br>under-resourced", 
                         showarrow=False, font=dict(size=12)),
                    dict(x=75, y=75, text="HEALTHY<br>Well resourced<br>and productive", 
                         showarrow=False, font=dict(size=12)),
                    dict(x=25, y=25, text="CRITICAL<br>Under-resourced<br>and struggling", 
                         showarrow=False, font=dict(size=12)),
                    dict(x=75, y=25, text="INEFFICIENT<br>Well resourced<br>but low productivity", 
                         showarrow=False, font=dict(size=12)),
                ],
                showlegend=False,
                height=600,
                hovermode='closest',
                margin=dict(l=50, r=50, t=80, b=50),
            )
            
            # Add health regions as colored backgrounds
            bubble_fig.add_shape(
                type="rect",
                x0=0, y0=50, x1=50, y1=105,
                line=dict(width=0),
                fillcolor="rgba(255, 230, 230, 0.3)",  # Light red
                layer="below"
            )
            bubble_fig.add_shape(
                type="rect",
                x0=50, y0=50, x1=105, y1=105,
                line=dict(width=0),
                fillcolor="rgba(230, 255, 230, 0.3)",  # Light green
                layer="below"
            )
            bubble_fig.add_shape(
                type="rect",
                x0=0, y0=0, x1=50, y1=50,
                line=dict(width=0),
                fillcolor="rgba(255, 200, 200, 0.3)",  # Darker red
                layer="below"
            )
            bubble_fig.add_shape(
                type="rect",
                x0=50, y0=0, x1=105, y1=50,
                line=dict(width=0),
                fillcolor="rgba(255, 230, 180, 0.3)",  # Light orange
                layer="below"
            )
            
            st.plotly_chart(bubble_fig, use_container_width=True)
            
            # Add explanation for the bubble chart
            st.markdown("""
            <div style="margin-top: -15px; font-size: 0.9em; color: #666;">
            <b>Reading the Bubble Chart:</b>
            <ul style="margin-top: 5px; margin-bottom: 5px;">
              <li>Bubble size represents the number of tasks in each project</li>
              <li>Color indicates health score (red = poor, orange = moderate, green = good)</li>
              <li>Position shows both resource allocation (x-axis) and completion rate (y-axis)</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with tabs[2]:
            # Create a specialized view for edge case projects (high values near 100)
            # Filter for projects with high resource allocation (>= 90)
            edge_projects = filtered_df[filtered_df['resource_allocation'] >= 90].copy()
            
            if not edge_projects.empty:
                st.markdown("### Edge Case Projects (High Resource Allocation)")  
                st.markdown("This view focuses on projects with very high resource allocation scores (≥90) that might "+ 
                          "appear at the edge of the standard chart.")
                
                # Create a specialized horizontal bar chart for edge projects
                # Sort by resource allocation descending
                edge_projects = edge_projects.sort_values('resource_allocation', ascending=True)
                
                # Create figure
                edge_fig = go.Figure()
                
                # Add bars for resource allocation
                edge_fig.add_trace(go.Bar(
                    y=edge_projects['project'],
                    x=edge_projects['resource_allocation'],
                    orientation='h',
                    name='Resource Allocation',
                    marker=dict(color='royalblue'),
                    text=edge_projects['resource_allocation'].round(1),
                    textposition='outside',
                    width=0.5
                ))
                
                # Update layout
                edge_fig.update_layout(
                    title='Projects with High Resource Allocation',
                    xaxis=dict(
                        title='Resource Allocation Score',
                        range=[85, 105],  # Focus on the high end
                        dtick=5
                    ),
                    yaxis=dict(
                        title='Project',
                    ),
                    height=max(400, len(edge_projects) * 30),  # Adjust height based on number of projects
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                
                st.plotly_chart(edge_fig, use_container_width=True)
                
                # Add detailed information in a table for these edge projects
                st.markdown("### Detailed Information for Edge Case Projects")
                
                # Prepare data for the table
                table_data = edge_projects[['project', 'resource_allocation', 'completion_rate', 
                                          'total_tasks', 'team_members', 'health_score']].copy()
                
                # Rename columns for better readability
                table_data.columns = ['Project', 'Resource Allocation', 'Completion Rate (%)', 
                                     'Total Tasks', 'Team Members', 'Health Score']
                
                # Format numeric columns
                table_data['Resource Allocation'] = table_data['Resource Allocation'].round(1)
                table_data['Completion Rate (%)'] = table_data['Completion Rate (%)'].round(1)
                table_data['Health Score'] = table_data['Health Score'].round(1)
                
                # Display as a formatted table
                st.dataframe(
                    table_data,
                    use_container_width=True,
                    column_config={
                        'Resource Allocation': st.column_config.ProgressColumn(
                            'Resource Allocation', 
                            format="%.1f", 
                            min_value=0, 
                            max_value=100,
                            help="Higher is better - indicates balanced resource allocation"
                        ),
                        'Completion Rate (%)': st.column_config.ProgressColumn(
                            'Completion Rate (%)', 
                            format="%.1f%%", 
                            min_value=0, 
                            max_value=100,
                            help="Percentage of tasks completed"
                        ),
                        'Health Score': st.column_config.ProgressColumn(
                            'Health Score', 
                            format="%.1f", 
                            min_value=0, 
                            max_value=100,
                            help="Overall health (average of resource allocation and completion rate)"
                        )
                    }
                )
                
                # Add recommendations for edge case projects
                st.markdown("### Recommendations for High Allocation Projects")
                st.markdown("""
                Projects with very high resource allocation scores (near 100) indicate excellent balance in how 
                resources are distributed. For these projects:
                
                - **If completion rate is also high**: These are exemplary projects that can serve as models for 
                  resource allocation practices across the organization.
                  
                - **If completion rate is low**: Despite excellent resource distribution, productivity may be 
                  affected by other factors such as skill mismatches, external dependencies, or scope issues. 
                  Consider conducting deeper analysis of these projects.
                  
                - **Consider stability**: Projects with perfect or near-perfect resource allocation may be 
                  sensitive to team changes. Have contingency plans in place for potential team member transitions.
                """)
            else:
                st.info("No projects with resource allocation scores ≥90 found in the current filtered dataset.")
        
        # Add explanation
        with st.expander("Understanding the Project Health Matrix"):
            st.markdown("""
            ### Understanding the Project Health Matrix
            
            This matrix provides a comprehensive view of project health by evaluating two key dimensions:
            
            #### Dimensions:
            
            - **Resource Allocation Score (X-axis)**: Measures how effectively resources are distributed across the project.
              - Higher scores (>50) indicate balanced workload distribution among team members
              - Lower scores (<50) suggest uneven resource allocation that may need attention
            
            - **Task Completion Rate (Y-axis)**: Shows the percentage of tasks completed in the project.
              - Higher rates (>50%) indicate good progress toward completion
              - Lower rates (<50%) suggest the project may be falling behind schedule
            
            #### Quadrant Interpretation:
            
            1. **HEALTHY (Top-Right)**: Well-resourced with high completion rates - these projects are performing well
               - Action: Maintain current approach, consider as exemplars for other projects
            
            2. **AT RISK (Top-Left)**: Achieving good completion despite poor resource allocation
               - Action: Review resource allocation to ensure sustainability; team may be overworked
            
            3. **INEFFICIENT (Bottom-Right)**: Well-resourced but with low completion rates
               - Action: Investigate productivity blockers, possible skill mismatches, or scope issues
            
            4. **CRITICAL (Bottom-Left)**: Poor resource allocation and low completion rates
               - Action: Immediate intervention required - consider re-planning and resource reallocation
            
            #### Marker Size and Color:
            
            - **Size**: Represents the total number of tasks in the project (larger = more tasks)
            - **Color**: Indicates overall health score (green = good, orange = moderate, red = needs attention)
            """)
            
            # Add more detailed breakdown for project managers
            st.markdown("""
            ### Action Items by Quadrant
            
            #### For Projects in the CRITICAL Quadrant:
            - Conduct immediate project review meetings
            - Consider adding more resources or reducing project scope
            - Establish more frequent progress check-ins
            - Review skills and training needs
            
            #### For Projects in the AT RISK Quadrant:
            - Conduct resource capacity planning
            - Evaluate for potential burnout risks
            - Document efficient processes for knowledge sharing
            - Consider strategic resource additions
            
            #### For Projects in the INEFFICIENT Quadrant:
            - Identify and remove productivity blockers
            - Review team composition and skills alignment
            - Evaluate communication patterns
            - Check for scope creep or unclear requirements
            
            #### For Projects in the HEALTHY Quadrant:
            - Document success factors
            - Consider if resources could be shared with struggling projects
            - Implement knowledge sharing sessions
            - Recognize team achievements
            """)
    else:
        st.info("No project health data available.")

def create_resource_allocation_summary(df: pd.DataFrame) -> None:
    """
    Create a dashboard-style summary of resource allocation metrics.
    
    Args:
        df: DataFrame with task data
    """
    # Calculate key metrics
    total_projects = df['project'].nunique()
    total_team_members = df['assignee'].nunique()
    total_tasks = len(df)
    avg_tasks_per_project = round(total_tasks / total_projects, 1) if total_projects > 0 else 0
    avg_tasks_per_team_member = round(total_tasks / total_team_members, 1) if total_team_members > 0 else 0
    completion_rate = round((df[df['status'] == 'Completed'].shape[0] / total_tasks * 100), 1) if total_tasks > 0 else 0
    
    # Calculate resource distribution (coefficient of variation)
    tasks_per_member = df.groupby('assignee').size()
    resource_balance = round(100 - (tasks_per_member.std() / tasks_per_member.mean() * 100), 1) if not tasks_per_member.empty and tasks_per_member.mean() > 0 else 0
    resource_balance = max(0, min(100, resource_balance))  # Clamp between 0-100
    
    # Create a dashboard-style summary
    st.markdown("#### Resource Allocation Dashboard")
    
    # Add CSS for tooltips
    st.markdown("""
    <style>
    .metric-container {
        position: relative;
        cursor: pointer;
    }
    .tooltip-icon {
        font-size: 12px;
        color: #999;
        margin-left: 4px;
    }
    .tooltip-text {
        visibility: hidden;
        background-color: rgba(60, 60, 60, 0.95);
        color: white;
        text-align: left;
        border-radius: 6px;
        padding: 8px 12px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -120px;
        width: 240px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 12px;
        line-height: 1.4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .metric-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create columns for the metrics
    cols = st.columns(5)
    
    # Define the metrics with icons, colors and tooltips
    metrics = [
        {
            "icon": "📋",
            "label": "Projects",
            "value": total_projects,
            "color": "#3366cc",
            "tooltip": "Total number of active projects in the current view."
        },
        {
            "icon": "👥",
            "label": "Team Members",
            "value": total_team_members,
            "color": "#dc3912",
            "tooltip": "Total number of team members assigned to tasks."
        },
        {
            "icon": "✓",
            "label": "Completion Rate",
            "value": f"{completion_rate}%",
            "color": "#109618",
            "tooltip": "Percentage of tasks marked as completed across all projects."
        },
        {
            "icon": "⚖️",
            "label": "Resource Balance",
            "value": f"{resource_balance}%",
            "color": "#ff9900",
            "tooltip": "Indicator of how evenly tasks are distributed among team members. Higher percentages indicate more balanced allocation."
        },
        {
            "icon": "📝",
            "label": "Tasks",
            "value": total_tasks,
            "color": "#990099",
            "tooltip": "Total number of tasks across all projects."
        }
    ]
    
    # Display each metric in its own column
    for i, metric in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div class="metric-container" style="background-color: {metric['color']}15; padding: 10px; border-radius: 5px; border-left: 5px solid {metric['color']}; margin-bottom: 12px;">
                <div style="color: {metric['color']}; font-size: 24px; margin-bottom: 0px;">{metric['icon']} {metric['value']}</div>
                <div style="font-size: 14px; color: #666; display: flex; align-items: center;">
                    {metric['label']}
                    <span class="tooltip-icon">ⓘ</span>
                </div>
                <div class="tooltip-text">{metric['tooltip']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Second row with additional metrics
    cols2 = st.columns(5)
    
    # Calculate additional metrics and track the actual members
    overallocated_members_count = 0
    underallocated_members_count = 0
    overallocated_members_names = []
    underallocated_members_names = []
    
    # Get task counts per member with names
    tasks_per_member_with_names = tasks_per_member.reset_index()
    tasks_per_member_with_names.columns = ['assignee', 'task_count']
    
    # Identify over and under allocated members
    for _, row in tasks_per_member_with_names.iterrows():
        if row['task_count'] > avg_tasks_per_team_member * 1.5:
            overallocated_members_count += 1
            overallocated_members_names.append(row['assignee'])
        elif row['task_count'] < avg_tasks_per_team_member * 0.5:
            underallocated_members_count += 1
            underallocated_members_names.append(row['assignee'])
    
    # Format the names lists for display
    overallocated_str = ", ".join(overallocated_members_names) if overallocated_members_names else "None"
    underallocated_str = ", ".join(underallocated_members_names) if underallocated_members_names else "None"
    
    resource_utilization = round((df.groupby('assignee').size().sum() / (total_team_members * avg_tasks_per_team_member * 1.2) * 100), 1) if total_team_members > 0 and avg_tasks_per_team_member > 0 else 0
    resource_utilization = min(100, resource_utilization)  # Cap at 100%
    
    # Additional metrics with tooltips
    metrics2 = [
        {
            "icon": "📊",
            "label": "Avg Tasks/Project",
            "value": avg_tasks_per_project,
            "color": "#3366cc",
            "tooltip": "Average number of tasks assigned per project. Helps gauge typical project scope."
        },
        {
            "icon": "👤",
            "label": "Avg Tasks/Member",
            "value": avg_tasks_per_team_member,
            "color": "#dc3912",
            "tooltip": "Average number of tasks assigned per team member. Helps identify balanced workload targets."
        },
        {
            "icon": "⚠️",
            "label": "Overallocated Members",
            "value": overallocated_members_count,
            "color": "#ee8800",
            "tooltip": f"Members with 50%+ more tasks than average.<br><b>Who:</b> {overallocated_str}"
        },
        {
            "icon": "⚡",
            "label": "Underallocated Members",
            "value": underallocated_members_count,
            "color": "#5574a6",
            "tooltip": f"Members with 50%+ fewer tasks than average.<br><b>Who:</b> {underallocated_str}"
        },
        {
            "icon": "📈",
            "label": "Resource Utilization",
            "value": f"{resource_utilization}%",
            "color": "#109618",
            "tooltip": "Overall resource utilization across team. Higher percentages indicate efficient use of available capacity."
        }
    ]
    
    # Display each metric in its own column
    for i, metric in enumerate(metrics2):
        with cols2[i]:
            st.markdown(f"""
            <div class="metric-container" style="background-color: {metric['color']}15; padding: 10px; border-radius: 5px; border-left: 5px solid {metric['color']}; margin-bottom: 15px;">
                <div style="color: {metric['color']}; font-size: 24px; margin-bottom: 0px;">{metric['icon']} {metric['value']}</div>
                <div style="font-size: 14px; color: #666; display: flex; align-items: center;">
                    {metric['label']}
                    <span class="tooltip-icon">ⓘ</span>
                </div>
                <div class="tooltip-text">{metric['tooltip']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Add a divider
    st.markdown("<hr style='margin-top: 0; margin-bottom: 15px;'>", unsafe_allow_html=True)

def calculate_project_health(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate project health metrics based on resource allocation and task completion.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
        
    Returns:
        List of project health metrics
    """
    project_health = []
    
    for project in project_details:
        project_name = project.get("name")
        
        # Filter for this project
        project_df = df[df["project"] == project_name]
        
        if not project_df.empty:
            # Calculate metrics
            total_tasks = len(project_df)
            completed_tasks = project_df[project_df["status"] == "Completed"].shape[0]
            completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            
            # Only skip projects that are explicitly marked as completed in the API
            # Check if project has a "status" field and if it equals "completed"
            project_status = project.get("status", "").lower()
            if project_status == "completed":
                continue
            
            # Do not skip projects based on task completion rate - they may still be active
            
            # Calculate resource allocation score
            team_members = project_df["assignee"].nunique()
            tasks_per_member = total_tasks / team_members if team_members > 0 else 0
            
            # Calculate standard deviation of tasks per member (lower is better)
            tasks_per_member_std = project_df.groupby("assignee").size().std()
            tasks_per_member_std = tasks_per_member_std if not pd.isna(tasks_per_member_std) else 0
            
            # Calculate resource allocation score (0-100)
            # Lower standard deviation means more balanced allocation
            max_std = 10  # Maximum expected standard deviation
            resource_allocation = max(0, min(100, 100 - (tasks_per_member_std / max_std * 100)))
            
            # Calculate health score (0-100)
            health_score = (completion_rate + resource_allocation) / 2
            
            project_health.append({
                "project": project_name,
                "total_tasks": total_tasks,
                "completion_rate": min(98, completion_rate),  # Cap at 98% to avoid edge cases
                "resource_allocation": resource_allocation,
                "health_score": health_score,
                "team_members": team_members,
                "tasks_per_member": tasks_per_member
            })
    
    return project_health