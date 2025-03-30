"""
Asana API tools for function calling.

This package provides a set of tools for interacting with the Asana API
through OpenAI's function calling capability.
"""

from src.utils.function_calling.tools.base import BaseAsanaTools
from src.utils.function_calling.tools.project_tools import ProjectTools
from src.utils.function_calling.tools.task_tools import TaskTools
import asana # Import the asana library

from typing import Dict, Any, Optional # Added Optional and Dict, Any
from src.utils.function_calling.tools.user_tools import UserTools
from src.utils.function_calling.tools.reporting_tools import ReportingTools
from src.utils.function_calling.tools.helpers import (
    # create_chart, # Deprecated: Use specific create_*_chart helpers
    # fig_to_json, # Deprecated: Use plotly.io.to_json directly
    convert_to_chart_data # May still be used elsewhere
)


class AsanaToolSet:
    """
    Main toolset for Asana API function calling.
    
    This class combines all the specialized tool classes into a single interface
    for use with the OpenAI function calling capability. It also distributes
    the assistant's memory reference to tools that need it.
    """
    
    def __init__(self, api_client: asana.ApiClient, assistant_memory: Optional[Dict[str, Any]] = None):
        """
        Initialize the toolset with the main Asana API client and assistant memory.
        
        Args:
            api_client: The configured Asana ApiClient instance.
            assistant_memory: Reference to the assistant's memory dictionary.
        """
        self.assistant_memory = assistant_memory # Store memory reference

        # Create specific API endpoint instances required by the tools
        specific_api_instances = {
            "_portfolios_api": asana.PortfoliosApi(api_client),
            "_projects_api": asana.ProjectsApi(api_client),
            "_tasks_api": asana.TasksApi(api_client),
            "_users_api": asana.UsersApi(api_client),
            "_teams_api": asana.TeamsApi(api_client),
            # Add other specific API classes here if needed by tools
        }

        # Create specialized tool instances, passing the dictionary of specific APIs
        self.base_tools = BaseAsanaTools(specific_api_instances)
        self.project_tools = ProjectTools(specific_api_instances)
        self.task_tools = TaskTools(specific_api_instances)
        self.user_tools = UserTools(specific_api_instances)
        # Pass memory to ReportingTools constructor
        self.reporting_tools = ReportingTools(specific_api_instances, assistant_memory=self.assistant_memory)

        # Set memory for base tools as well, if needed by any base methods
        self.base_tools.set_assistant_memory(self.assistant_memory)

    # Project-related functions
    def get_portfolio_projects(self, portfolio_gid=None):
        """Get all projects in a portfolio."""
        self.base_tools.logger.info("Calling get_portfolio_projects tool function")
        result = self.project_tools.get_portfolio_projects(portfolio_gid)
        self.base_tools.logger.debug(f"get_portfolio_projects result: {result}")
        return result
    
    def get_project_details(self, project_gid):
        """Get detailed information about a specific project."""
        self.base_tools.logger.info("Calling get_project_details tool function")
        result = self.project_tools.get_project_details(project_gid)
        self.base_tools.logger.debug(f"get_project_details result: {result}")
        return result
    
    def get_project_gid_by_name(self, project_name):
        """Find a project's GID by searching for its name."""
        self.base_tools.logger.info("Calling get_project_gid_by_name tool function")
        result = self.project_tools.get_project_gid_by_name(project_name)
        self.base_tools.logger.debug(f"get_project_gid_by_name result: {result}")
        return result
    
    def get_project_info_by_name(self, project_name):
        """Get project details by searching for a project name."""
        self.base_tools.logger.info("Calling get_project_info_by_name tool function")
        result = self.project_tools.get_project_info_by_name(project_name)
        self.base_tools.logger.debug(f"get_project_info_by_name result: {result}")
        return result
    
    def get_projects_by_owner(self, owner_name):
        """Get projects owned by a specific user."""
        self.base_tools.logger.info("Calling get_projects_by_owner tool function")
        result = self.project_tools.get_projects_by_owner(owner_name)
        self.base_tools.logger.debug(f"get_projects_by_owner result: {result}")
        return result
    
    # Task-related functions
    def get_project_tasks(self, project_gid, limit=50, completed=None):
        """Get tasks for a specific project."""
        return self.task_tools.get_project_tasks(project_gid, limit, completed)
    
    def get_task_details(self, task_gid):
        """Get detailed information about a specific task."""
        return self.task_tools.get_task_details(task_gid)
    
    def search_tasks(self, search_text, limit=20):
        """Search for tasks by name or description."""
        return self.task_tools.search_tasks(search_text, limit)
    
    def get_task_subtasks(self, task_gid):
        """Get subtasks for a specific task."""
        return self.task_tools.get_task_subtasks(task_gid)
    
    def get_task_by_name(self, task_name, project_gid=None):
        """Find a task by name within a project or across all projects."""
        return self.task_tools.get_task_by_name(task_name, project_gid)
    
    # User-related functions
    def get_users_in_team(self):
        """Get all users in the team."""
        return self.user_tools.get_users_in_team()
    
    def get_user_details(self, user_gid):
        """Get detailed information about a specific user."""
        return self.user_tools.get_user_details(user_gid)
    
    def find_user_by_name(self, user_name):
        """Find a user by name."""
        return self.user_tools.find_user_by_name(user_name)
    
    def get_tasks_by_assignee(self, assignee_name, completed=None, limit=50):
        """Get tasks assigned to a specific user."""
        return self.user_tools.get_tasks_by_assignee(assignee_name, completed, limit)
    
    def get_user_workload(self, user_name):
        """Get workload information for a specific user."""
        return self.user_tools.get_user_workload(user_name)
    
    # Reporting and analytics functions
    def get_task_distribution_by_assignee(self, project_gid=None, include_completed=True):
        """Get task distribution statistics grouped by assignee."""
        return self.reporting_tools.get_task_distribution_by_assignee(project_gid, include_completed)
    
    def get_task_completion_trend(self, project_gid=None, days=30):
        """Get task completion trend over time."""
        return self.reporting_tools.get_task_completion_trend(project_gid, days)
    
    def get_project_progress(self, project_gid):
        """Get progress statistics for a specific project."""
        return self.reporting_tools.get_project_progress(project_gid)
    
    def get_team_workload(self):
        """Get workload statistics for the entire team."""
        return self.reporting_tools.get_team_workload()
    
    # Visualization function
    def create_direct_chart(self, chart_type, data, title=None, config=None):
        """
        Create a visualization chart directly from provided data.
        
        Args:
            chart_type: Type of chart to create
            data: Data for the chart
            title: Title for the chart
            config: Additional configuration options
            
        Returns:
            Dictionary with chart data
        """
        # Prepare config
        config = config or {}
        if title:
            config["title"] = title
            
        # Prepare data
        chart_data = convert_to_chart_data(data, chart_type)
        
        # Create figure
        fig = create_chart(chart_type, chart_data, config)
        
        # Convert to JSON
        chart_json = fig_to_json(fig)
        
        # Return response
        return {
            "status": "success",
            "chart_data": chart_json,
            "chart_type": chart_type,
            "title": title or config.get("title", "Chart")
        }


__all__ = [
    "AsanaToolSet",
    "BaseAsanaTools",
    "ProjectTools",
    "TaskTools",
    "UserTools",
    "ReportingTools",
    # "create_chart", # Deprecated
    # "fig_to_json", # Deprecated
    "convert_to_chart_data"
]
