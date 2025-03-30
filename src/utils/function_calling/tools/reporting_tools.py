"""
Reporting and analytics tools for Asana data.

This module provides tools for generating reports and analytics from Asana data,
including task distribution by assignee, completion trends, and custom visualizations.
"""
from typing import Dict, Any, List, Optional, Union, Callable
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src.utils.function_calling.tools.base import BaseAsanaTools
from src.utils.function_calling.tools.project_tools import ProjectTools
from src.utils.function_calling.tools.task_tools import TaskTools
from src.utils.function_calling.utils import (
    handle_api_error,
    safe_get,
    format_date,
    calculate_date_range,
    create_dataframe_from_tasks
)
from src.utils.function_calling.schemas import (
    TaskDistributionResponse,
    TaskCompletionTrendResponse,
    VisualizationResponse
)
# Import helper functions for chart creation
from src.utils.function_calling.tools.helpers import (
    create_bar_chart, create_line_chart, create_pie_chart,
    create_scatter_chart, create_timeline_chart, create_heatmap_chart
)

from typing import Dict, Any, List, Optional, Union, Callable # Added Optional

class ReportingTools(BaseAsanaTools):
    """Tools for generating reports and analytics from Asana data."""

    def __init__(self, api_instances: Dict[str, Any], assistant_memory: Optional[Dict[str, Any]] = None):
        """
        Initialize with API instances, assistant memory, and create linked tools.

        Args:
            api_instances: Dictionary of Asana API instances.
            assistant_memory: Reference to the assistant's memory dictionary.
        """
        super().__init__(api_instances)
        # Set the assistant memory reference for this tool instance
        self.set_assistant_memory(assistant_memory)

        # Create instances of related tools for internal use
        self.project_tools = ProjectTools(api_instances)
        self.task_tools = TaskTools(api_instances)
        self.task_tools = TaskTools(api_instances)

    @handle_api_error
    def get_task_distribution_by_assignee(self,
                                         project_gid: Optional[str] = None,
                                         include_completed: bool = True) -> Dict[str, Any]:
        """
        Get task distribution statistics grouped by assignee.

        Args:
            project_gid: The GID of the project (optional, will get data for all portfolio projects if not provided)
            include_completed: Whether to include completed tasks in the statistics

        Returns:
            Dictionary with task distribution statistics
        """
        # Apply rate limiting
        self._apply_rate_limit()

        # Get tasks from project(s)
        if project_gid:
            # Validate project_gid
            valid_gid = self.validate_gid_param(project_gid, "project_gid")
            if not valid_gid:
                return {
                    "status": "error",
                    "error": f"Invalid project GID: {project_gid}"
                }

            self.logger.info(f"Getting task distribution for project GID: {valid_gid}")

            # Get tasks for the specified project
            tasks_result = self.task_tools.get_project_tasks(valid_gid, limit=500)

            if tasks_result.get("status") != "success":
                return tasks_result

            tasks = tasks_result.get("tasks", [])
        else:
            # Get tasks for all projects in the portfolio
            if not self.portfolio_gid or self.portfolio_gid == "your_portfolio_gid_here":
                return self.handle_missing_portfolio()

            self.logger.info("Getting task distribution for all projects in portfolio")

            # Get all projects in the portfolio
            projects_result = self.project_tools.get_portfolio_projects()

            if projects_result.get("status") != "success":
                return projects_result

            # Get tasks from all projects
            tasks = []
            for project in projects_result.get("projects", []):
                project_gid = project.get("gid")
                if project_gid:
                    tasks_result = self.task_tools.get_project_tasks(project_gid, limit=100)
                    if tasks_result.get("status") == "success":
                        tasks.extend(tasks_result.get("tasks", []))

        # Create DataFrame from tasks
        df = create_dataframe_from_tasks(tasks)

        # Filter out completed tasks if not included
        if not include_completed:
            df = df[~df['completed']]

        # Calculate statistics
        total_tasks = len(df)
        completed_tasks = df['completed'].sum()
        incomplete_tasks = total_tasks - completed_tasks

        # Group by assignee
        assignee_stats = []

        if not df.empty:
            # Group by assignee and count tasks
            grouped = df.groupby('assignee_name').agg({
                'gid': 'count',
                'completed': 'sum'
            }).reset_index()

            grouped = grouped.rename(columns={
                'gid': 'total_tasks',
                'completed': 'completed_tasks'
            })

            grouped['incomplete_tasks'] = grouped['total_tasks'] - grouped['completed_tasks']
            grouped['completion_rate'] = (grouped['completed_tasks'] / grouped['total_tasks']).fillna(0)

            # Convert to list of dictionaries
            for _, row in grouped.iterrows():
                assignee_stats.append({
                    'assignee_name': row['assignee_name'],
                    'total_tasks': int(row['total_tasks']),
                    'completed_tasks': int(row['completed_tasks']),
                    'incomplete_tasks': int(row['incomplete_tasks']),
                    'completion_rate': float(row['completion_rate'])
                })

        # Count unassigned tasks
        unassigned_count = df[df['assignee_name'] == 'Unassigned'].shape[0]

        # Create response
        return {
            "status": "success",
            "assignees": assignee_stats,
            "total_tasks": total_tasks,
            "completed_tasks": int(completed_tasks),
            "incomplete_tasks": incomplete_tasks,
            "unassigned_tasks": unassigned_count,
            "project_gid": project_gid if project_gid else "all_projects",
            "include_completed": include_completed
        }

    @handle_api_error
    def get_task_completion_trend(self,
                                 project_gid: Optional[str] = None,
                                 days: int = 30) -> Dict[str, Any]:
        """
        Get task completion trend over time.

        Args:
            project_gid: The GID of the project (optional, will get data for all portfolio projects if not provided)
            days: Number of days to look back

        Returns:
            Dictionary with task completion trend data
        """
        # Apply rate limiting
        self._apply_rate_limit()

        # Get tasks from project(s)
        if project_gid:
            # Validate project_gid
            valid_gid = self.validate_gid_param(project_gid, "project_gid")
            if not valid_gid:
                return {
                    "status": "error",
                    "error": f"Invalid project GID: {project_gid}"
                }

            self.logger.info(f"Getting task completion trend for project GID: {valid_gid}")

            # Get tasks for the specified project
            tasks_result = self.task_tools.get_project_tasks(valid_gid, limit=500)

            if tasks_result.get("status") != "success":
                return tasks_result

            tasks = tasks_result.get("tasks", [])
        else:
            # Get tasks for all projects in the portfolio
            if not self.portfolio_gid or self.portfolio_gid == "your_portfolio_gid_here":
                return self.handle_missing_portfolio()

            self.logger.info("Getting task completion trend for all projects in portfolio")

            # Get all projects in the portfolio
            projects_result = self.project_tools.get_portfolio_projects()

            if projects_result.get("status") != "success":
                return projects_result

            # Get tasks from all projects
            tasks = []
            for project in projects_result.get("projects", []):
                project_gid = project.get("gid")
                if project_gid:
                    tasks_result = self.task_tools.get_project_tasks(project_gid, limit=100)
                    if tasks_result.get("status") == "success":
                        tasks.extend(tasks_result.get("tasks", []))

        # Create DataFrame from tasks
        df = create_dataframe_from_tasks(tasks)

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Create date range for the trend
        date_range = pd.date_range(start=start_date, end=end_date)
        date_range_str = [date.strftime('%Y-%m-%d') for date in date_range]

        # Initialize counters
        completed_counts = [0] * len(date_range)
        created_counts = [0] * len(date_range)

        # Count completed and created tasks per day
        if not df.empty:
            # Convert date columns to datetime
            if 'completed_at' in df.columns:
                df['completed_at'] = pd.to_datetime(df['completed_at'], errors='coerce')

            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

            # Count completions per day
            if 'completed_at' in df.columns:
                for i, date in enumerate(date_range):
                    date_str = date.strftime('%Y-%m-%d')
                    completed_counts[i] = df[df['completed_at'].dt.strftime('%Y-%m-%d') == date_str].shape[0]

            # Count created tasks per day
            if 'created_at' in df.columns:
                for i, date in enumerate(date_range):
                    date_str = date.strftime('%Y-%m-%d')
                    created_counts[i] = df[df['created_at'].dt.strftime('%Y-%m-%d') == date_str].shape[0]

        # Calculate totals
        total_completed = sum(completed_counts)
        total_created = sum(created_counts)

        # Create response
        return {
            "status": "success",
            "dates": date_range_str,
            "completed_counts": completed_counts,
            "created_counts": created_counts,
            "total_completed": total_completed,
            "total_created": total_created,
            "project_gid": project_gid if project_gid else "all_projects",
            "days": days,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }

    @handle_api_error
    def get_project_progress(self, project_gid: str) -> Dict[str, Any]:
        """
        Get progress statistics for a specific project.

        Args:
            project_gid: The GID of the project

        Returns:
            Dictionary with project progress statistics
        """
        # Validate project_gid
        valid_gid = self.validate_gid_param(project_gid, "project_gid")
        if not valid_gid:
            return {
                "status": "error",
                "error": f"Invalid project GID: {project_gid}"
            }

        # Apply rate limiting
        self._apply_rate_limit()

        self.logger.info(f"Getting progress statistics for project GID: {valid_gid}")

        # Get project details
        project_result = self.project_tools.get_project_details(valid_gid)

        if project_result.get("status") != "success":
            return project_result

        # Get tasks for the project
        tasks_result = self.task_tools.get_project_tasks(valid_gid, limit=500)

        if tasks_result.get("status") != "success":
            return tasks_result

        tasks = tasks_result.get("tasks", [])

        # Create DataFrame from tasks
        df = create_dataframe_from_tasks(tasks)

        # Calculate statistics
        total_tasks = len(df)
        if total_tasks == 0:
            completion_rate = 0
            completed_tasks = 0
        else:
            completed_tasks = df['completed'].sum()
            completion_rate = completed_tasks / total_tasks

        # Calculate due date information
        today = datetime.now().strftime('%Y-%m-%d')
        project_due_date = project_result.get("due_on")

        # Calculate days until due
        days_until_due = None
        if project_due_date:
            try:
                due_date = datetime.strptime(project_due_date, '%Y-%m-%d')
                today_date = datetime.strptime(today, '%Y-%m-%d')
                days_until_due = (due_date - today_date).days
            except Exception as e:
                self.logger.warning(f"Error calculating days until due: {e}")

        # Calculate overdue tasks
        overdue_tasks = []
        if not df.empty:
            for _, row in df.iterrows():
                if not row['completed'] and row['due_on'] and row['due_on'] < today:
                    overdue_tasks.append({
                        'gid': row['gid'],
                        'name': row['name'],
                        'assignee_name': row['assignee_name'],
                        'due_on': row['due_on']
                    })

        # Create response
        return {
            "status": "success",
            "project_gid": valid_gid,
            "project_name": project_result.get("name", ""),
            "total_tasks": total_tasks,
            "completed_tasks": int(completed_tasks),
            "incomplete_tasks": total_tasks - int(completed_tasks),
            "completion_rate": float(completion_rate),
            "start_date": project_result.get("start_on"),
            "due_date": project_result.get("due_on"),
            "days_until_due": days_until_due,
            "overdue_tasks": overdue_tasks,
            "overdue_count": len(overdue_tasks)
        }

    @handle_api_error
    def get_team_workload(self) -> Dict[str, Any]:
        """
        Get workload statistics for the entire team.

        Returns:
            Dictionary with team workload statistics
        """
        # Apply rate limiting
        self._apply_rate_limit()

        self.logger.info("Getting workload statistics for the team")

        # Get all users in the team
        if not self.team_gid or self.team_gid == "your_team_gid_here":
            return {
                "status": "error",
                "error": "No valid team GID found in the application settings. Please contact your administrator."
            }

        # Get task distribution by assignee across all projects
        distribution_result = self.get_task_distribution_by_assignee()

        if distribution_result.get("status") != "success":
            return distribution_result

        # Get all projects in the portfolio
        projects_result = self.project_tools.get_portfolio_projects()

        if projects_result.get("status") != "success":
            return projects_result

        # Calculate project statistics
        total_projects = len(projects_result.get("projects", []))
        completed_projects = sum(1 for p in projects_result.get("projects", []) if p.get("completed", False))

        # Create response
        return {
            "status": "success",
            "team_gid": self.team_gid,
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "active_projects": total_projects - completed_projects,
            "assignees": distribution_result.get("assignees", []),
            "total_tasks": distribution_result.get("total_tasks", 0),
            "completed_tasks": distribution_result.get("completed_tasks", 0),
            "incomplete_tasks": distribution_result.get("incomplete_tasks", 0),
            "unassigned_tasks": distribution_result.get("unassigned_tasks", 0)
        }

    @handle_api_error
    def create_direct_chart(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Validates data, creates the Plotly chart figure, serializes it to JSON,
        and stores the JSON in memory for rendering.

        Args:
            **kwargs: Arbitrary keyword arguments representing chart data and config.
                      Expected args depend on chart_type.

        Returns:
            Dictionary indicating success or failure, including the chart JSON on success.
        """
        # Need to import dataclasses for field inspection
        import dataclasses
        # Import ValidationError for specific exception handling
        from pydantic import ValidationError

        from src.utils.function_calling.schemas.visualization_schemas import (
            ChartType, ChartConfig, BarChartData, LineChartData, PieChartData,
            ScatterChartData, TimelineChartData, HeatmapChartData
        )

        self.logger.info(f"Attempting to create direct chart with args: {kwargs}")

        chart_type: Optional[ChartType] = kwargs.get("chart_type")
        if not chart_type:
            return {"status": "error", "error": "Missing required argument: chart_type"}

        # Map chart types to their Pydantic data models AND rendering functions
        chart_renderers: Dict[ChartType, Callable] = {
            "bar": create_bar_chart,
            "line": create_line_chart,
            "pie": create_pie_chart,
            "scatter": create_scatter_chart,
            "timeline": create_timeline_chart,
            "heatmap": create_heatmap_chart,
            "area": lambda **args: create_line_chart(fill='tozeroy', **args) # Area is line with fill
        }
        chart_data_models: Dict[ChartType, type] = {
            "bar": BarChartData,
            "line": LineChartData,
            "pie": PieChartData,
            "scatter": ScatterChartData,
            "area": LineChartData, # Area chart uses LineChartData
            "timeline": TimelineChartData,
            "heatmap": HeatmapChartData,
        }

        DataModel = chart_data_models.get(chart_type)
        renderer = chart_renderers.get(chart_type)

        if not DataModel or not renderer:
            return {"status": "error", "error": f"Unsupported chart_type: {chart_type}"}

        try:
            # Separate config (dataclass) and data (Pydantic) args based on model fields
            # Use __dataclass_fields__ directly to avoid potential issues with dataclasses.fields() interaction
            config_fields = set(ChartConfig.__dataclass_fields__.keys())
            data_fields = set(DataModel.model_fields.keys()) # Use Pydantic method for DataModel

            config_args = {k: v for k, v in kwargs.items() if k in config_fields and k != 'title'} # title is handled separately
            data_args = {k: v for k, v in kwargs.items() if k in data_fields}

            # Validate data using the specific model
            # Pydantic models validate on instantiation, so an explicit call is not needed here.
            # If validation fails, a ValidationError will be raised and caught by the outer try-except block.
            data_instance = DataModel(**data_args)

            # Validation passed (or would have raised ValidationError), now create the figure using the renderer
            # Pass the original kwargs to the renderer as it expects the flat dictionary
            chart_args_for_renderer = kwargs.copy()
            # Remove chart_type as the renderer doesn't need it
            chart_args_for_renderer.pop("chart_type", None)

            self.logger.debug(f"Calling chart renderer '{renderer.__name__}' with args: {chart_args_for_renderer}")
            fig = renderer(**chart_args_for_renderer)

            if not fig or not isinstance(fig, go.Figure):
                 self.logger.error(f"Chart renderer for '{chart_type}' did not return a valid Plotly Figure.")
                 return {"status": "error", "error": f"Failed to generate figure for chart type '{chart_type}'."}

            # Serialize the figure to JSON
            try:
                fig_json = pio.to_json(fig)
                self.logger.info(f"Successfully created and serialized chart figure for '{kwargs.get('title', 'chart')}'")
            except Exception as serialize_err:
                self.logger.error(f"Failed to serialize Plotly figure to JSON: {serialize_err}", exc_info=True)
                return {"status": "error", "error": f"Failed to serialize chart figure: {serialize_err}"}

            # Store the JSON in memory (append to a list for multiple charts)
            if self.assistant_memory is not None:
                # Initialize the list if it doesn't exist
                if 'charts_json_list' not in self.assistant_memory:
                    self.assistant_memory['charts_json_list'] = []
                # Append the current chart JSON
                self.assistant_memory['charts_json_list'].append(fig_json)
                self.logger.info(f"Appended chart JSON to 'charts_json_list' in memory. List now contains {len(self.assistant_memory['charts_json_list'])} chart(s).")
            else:
                self.logger.warning("Assistant memory not set in ReportingTools. Cannot store chart JSON.")
                # Optionally return the JSON here if memory isn't available,
                # though the current flow relies on memory storage.
                # return {"status": "warning", "message": "Chart created but could not be stored in memory.", "chart_json": fig_json}

            return {
                "status": "success",
                "message": f"Chart '{kwargs.get('title', 'chart')}' created and prepared successfully. It will be displayed.",
                "chart_type": chart_type,
                # Optionally return json for debugging, but not strictly needed by LLM
                # "chart_json": fig_json
            }

        except (TypeError, ValueError, ValidationError) as e: # Catch Pydantic's ValidationError too
            # Log the specific validation error details if available
            details = getattr(e, 'errors', lambda: None)() if isinstance(e, ValidationError) else None
            self.logger.error(f"Error validating/processing chart data for {chart_type}: {e}. Details: {details}", exc_info=True)
            return {"status": "error", "error": f"Invalid arguments for {chart_type} chart: {e}", "details": details, "received_args": kwargs}
        except Exception as e:
            self.logger.error(f"Unexpected error in create_direct_chart: {e}", exc_info=True)
            return {"status": "error", "error": f"An unexpected error occurred: {e}"}
