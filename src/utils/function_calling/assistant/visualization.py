"""
Visualization module for function calling assistant.

This module provides functionality for creating and rendering visualizations
from Asana data, including charts, timelines, and other visual representations.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.utils.function_calling.tools.helpers import (
    # create_chart, # Deprecated: Specific helpers are called directly now
    convert_to_chart_data,
    # fig_to_json # Deprecated: Use plotly.io.to_json directly where needed
)
from src.utils.function_calling.schemas import ChartType


class VisualizationManager:
    """
    Visualization manager for function calling assistant.

    This class provides methods for creating and rendering visualizations,
    including charts, timelines, and other visual representations.
    NOTE: Parts of this may be deprecated due to direct chart creation refactoring.
    """

    def __init__(self):
        """Initialize the visualization manager."""
        self.logger = logging.getLogger(self.__class__.__name__)

        # Track created visualizations
        self.visualizations = []

    def render_chart_from_json(self, chart_json: Dict[str, Any]) -> go.Figure:
        """
        Render a chart from a JSON representation.

        Args:
            chart_json: JSON representation of a Plotly figure

        Returns:
            Plotly figure object
        """
        try:
            # Create figure from JSON
            fig = go.Figure(chart_json)
            return fig
        except Exception as e:
            self.logger.error(f"Error rendering chart from JSON: {str(e)}")
            # Return empty figure
            return go.Figure()

    # def create_chart_from_data(self, chart_type: ChartType, data: Dict[str, Any],
    #                            config: Optional[Dict[str, Any]] = None) -> go.Figure:
    #     """
    #     DEPRECATED: Create a chart from data. Direct chart creation now happens in reporting_tools.
    #
    #     Args:
    #         chart_type: Type of chart to create
    #         data: Data for the chart
    #         config: Configuration options
    #
    #     Returns:
    #         Plotly figure object
    #     """
    #     try:
    #         # Convert data to chart format
    #         chart_data = convert_to_chart_data(data, chart_type)
    #
    #         # Create chart - This import was removed
    #         # fig = create_chart(chart_type, chart_data, config)
    #         fig = go.Figure() # Return empty figure instead
    #         self.logger.warning("create_chart_from_data is deprecated and called create_chart which was removed.")
    #
    #
    #         # Track created visualization
    #         self.visualizations.append({
    #             "type": chart_type,
    #             "data": data,
    #             "config": config
    #         })
    #
    #         return fig
    #     except Exception as e:
    #         self.logger.error(f"Error creating chart: {str(e)}")
    #         # Return empty figure
    #         return go.Figure()

    def render_project_timeline(self, projects: List[Dict[str, Any]]) -> go.Figure:
        """
        Render a timeline of projects.

        Args:
            projects: List of project dictionaries

        Returns:
            Plotly figure object
        """
        # Extract project data
        tasks = []
        start_dates = []
        end_dates = []
        statuses = []

        for project in projects:
            name = project.get("name", "Unnamed Project")
            start_on = project.get("start_on")
            due_on = project.get("due_on")
            completed = project.get("completed", False)

            # Skip projects without dates
            if not start_on or not due_on:
                continue

            tasks.append(name)
            start_dates.append(start_on)
            end_dates.append(due_on)
            statuses.append("Completed" if completed else "In Progress")

        # Create timeline data
        timeline_data = {
            "tasks": tasks,
            "start_dates": start_dates,
            "end_dates": end_dates,
            "group": statuses
        }

        # Create config
        config = {
            "title": "Project Timeline",
            "height": 500
        }

        # Create chart - Using direct helper call (assuming it exists and takes flat kwargs)
        try:
            from .helpers import create_timeline_chart # Local import if needed
            fig = create_timeline_chart(**timeline_data, **config) # Pass flat kwargs
        except ImportError:
             self.logger.error("create_timeline_chart helper not found.")
             fig = go.Figure()
        except Exception as e:
             self.logger.error(f"Error rendering project timeline: {e}")
             fig = go.Figure()

        # Track created visualization
        self.visualizations.append({
            "type": "timeline",
            "data": projects, # Store original data
            "config": config
        })

        return fig


    def render_task_distribution(self, assignees: List[Dict[str, Any]]) -> go.Figure:
        """
        Render a task distribution chart.

        Args:
            assignees: List of assignee dictionaries with task counts

        Returns:
            Plotly figure object
        """
        # Extract data
        names = []
        completed = []
        incomplete = []

        for assignee in assignees:
            names.append(assignee.get("assignee_name", "Unassigned"))
            completed.append(assignee.get("completed_tasks", 0))
            incomplete.append(assignee.get("incomplete_tasks", 0))

        # Create config
        config = {
            "title": "Task Distribution by Assignee",
            "height": 400,
            "x_axis_title": "Assignee",
            "y_axis_title": "Number of Tasks"
        }

        # Create stacked bar chart
        fig = go.Figure()

        try:
            fig.add_trace(go.Bar(
                x=names,
                y=completed,
                name="Completed"
            ))
            fig.add_trace(go.Bar(
                x=names,
                y=incomplete,
                name="Incomplete"
            ))

            fig.update_layout(
                title=config["title"],
                xaxis_title=config["x_axis_title"],
                yaxis_title=config["y_axis_title"],
                height=config["height"],
                barmode="stack"
            )
        except Exception as e:
             self.logger.error(f"Error rendering task distribution: {e}")
             fig = go.Figure() # Ensure fig is always a Figure object

        # Track created visualization
        self.visualizations.append({
            "type": "task_distribution",
            "data": assignees,
            "config": config
        })

        return fig

    def render_completion_trend(self, dates: List[str], completed_counts: List[int],
                               created_counts: List[int]) -> go.Figure:
        """
        Render a task completion trend chart.

        Args:
            dates: List of dates
            completed_counts: List of completed task counts per date
            created_counts: List of created task counts per date

        Returns:
            Plotly figure object
        """
        # Create line chart data
        line_data = {
            "x_values": dates,
            "y_values": [completed_counts, created_counts],
            "series_names": ["Completed", "Created"],
            "show_markers": True,
            "line_shape": "linear"
        }

        # Create config
        config = {
            "title": "Task Completion Trend",
            "height": 400,
            "x_axis_title": "Date",
            "y_axis_title": "Number of Tasks"
        }

        # Create chart - Using direct helper call
        try:
            from .helpers import create_line_chart # Local import if needed
            fig = create_line_chart(**line_data, **config) # Pass flat kwargs
        except ImportError:
             self.logger.error("create_line_chart helper not found.")
             fig = go.Figure()
        except Exception as e:
             self.logger.error(f"Error rendering completion trend: {e}")
             fig = go.Figure()

        # Track created visualization
        self.visualizations.append({
            "type": "line",
            "data": {"dates": dates, "completed": completed_counts, "created": created_counts},
            "config": config
        })

        return fig


    def render_progress_chart(self, completed: int, total: int) -> go.Figure:
        """
        Render a progress chart.

        Args:
            completed: Number of completed tasks
            total: Total number of tasks

        Returns:
            Plotly figure object
        """
        # Calculate remaining
        remaining = total - completed
        if remaining < 0: remaining = 0 # Ensure non-negative

        # Create pie chart data
        pie_data = {
            "labels": ["Completed", "Remaining"],
            "values": [completed, remaining],
            "hole": 0.4
        }

        # Create config
        config = {
            "title": "Project Progress",
            "height": 300
        }

        # Create chart - Using direct helper call
        try:
            from .helpers import create_pie_chart # Local import if needed
            fig = create_pie_chart(**pie_data, **config) # Pass flat kwargs
        except ImportError:
             self.logger.error("create_pie_chart helper not found.")
             fig = go.Figure()
        except Exception as e:
             self.logger.error(f"Error rendering progress chart: {e}")
             fig = go.Figure()

        # Track created visualization
        self.visualizations.append({
            "type": "pie",
            "data": {"completed": completed, "total": total},
            "config": config
        })

        return fig

    def detect_and_render_visualization(self, function_name: str,
                                       function_args: Dict[str, Any],
                                       function_result: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Detect and render an appropriate visualization based on function call.
        NOTE: This might need further refactoring if create_chart_from_data is fully removed.

        Args:
            function_name: Name of the function called
            function_args: Arguments to the function
            function_result: Result of the function call

        Returns:
            Plotly figure object or None if no visualization is appropriate
        """
        try:
            # Check if result is a chart already (e.g., from create_direct_chart)
            # This path might be less common now if create_direct_chart stores JSON in memory
            if function_name == "create_direct_chart":
                # Assuming create_direct_chart returns JSON in its result now (needs verification)
                if function_result.get("status") == "success" and "chart_json" in function_result:
                     try:
                         return self.render_chart_from_json(json.loads(function_result["chart_json"]))
                     except json.JSONDecodeError:
                         self.logger.error("Failed to decode chart JSON from create_direct_chart result.")
                         return None
                # If create_direct_chart stores in memory, this path might not be hit.
                # The UI component function_chat.py handles memory retrieval.
                self.logger.debug("create_direct_chart called, but no chart_json found in result. Chart likely stored in memory.")
                return None

            # Check for project-related visualizations
            if function_name == "get_portfolio_projects":
                projects = function_result.get("projects", [])
                if projects:
                    return self.render_project_timeline(projects)

            # Check for task distribution visualizations
            if function_name == "get_task_distribution_by_assignee":
                assignees = function_result.get("assignees", [])
                if assignees:
                    return self.render_task_distribution(assignees)

            # Check for completion trend visualizations
            if function_name == "get_task_completion_trend":
                dates = function_result.get("dates", [])
                completed_counts = function_result.get("completed_counts", [])
                created_counts = function_result.get("created_counts", [])

                if dates and (completed_counts or created_counts): # Check if at least one count list exists
                    # Ensure lists have same length as dates, padding with 0 if necessary
                    len_dates = len(dates)
                    completed_counts = (completed_counts + [0] * len_dates)[:len_dates] if completed_counts else [0] * len_dates
                    created_counts = (created_counts + [0] * len_dates)[:len_dates] if created_counts else [0] * len_dates
                    return self.render_completion_trend(dates, completed_counts, created_counts)

            # Check for project progress visualizations
            if function_name == "get_project_progress":
                completed = function_result.get("completed_tasks", 0)
                total = function_result.get("total_tasks", 0)

                if total > 0:
                    return self.render_progress_chart(completed, total)

            return None
        except Exception as e:
            self.logger.error(f"Error detecting/rendering visualization: {str(e)}", exc_info=True)
            return None
