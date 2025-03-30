"""
Task-related tools for interacting with Asana tasks.

This module provides tools for working with Asana tasks, including
retrieving tasks for projects, getting task details, and searching tasks.
"""
from typing import Dict, Any, List, Optional, Union
import logging

from src.utils.function_calling.tools.base import BaseAsanaTools
from src.utils.function_calling.utils import (
    handle_api_error, 
    safe_get,
    dataclass_to_dict
)
from src.utils.function_calling.schemas import TaskResponse, TasksListResponse


class TaskTools(BaseAsanaTools):
    """Tools for working with Asana tasks."""
    
    @handle_api_error
    def get_project_tasks(self, project_gid: str, 
                          limit: int = 50, 
                          completed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Get tasks in a project with optional filtering.
        
        Args:
            project_gid: Project GID
            limit: Maximum number of tasks to return (default: 50)
            completed: Filter by completion status (None for all tasks)
            
        Returns:
            Dictionary with list of tasks
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
        
        # Set up parameters for the API call
        params = {
            'limit': min(int(limit), 100),  # Cap at 100 for performance
            'opt_fields': 'name,gid,assignee,assignee.name,due_on,completed,completed_at,created_at,notes,projects,tags,custom_fields' # Added created_at
        }
        
        # Only add completed filter if it's not None
        if completed is not None:
            params['completed'] = completed
            if completed:
                self.logger.info(f"Getting completed tasks for project GID: {valid_gid}")
            else:
                self.logger.info(f"Getting incomplete tasks for project GID: {valid_gid}")
        else:
            self.logger.info(f"Getting all tasks for project GID: {valid_gid}")
            
        # Make API call
        tasks = list(self.api_instances["_tasks_api"].get_tasks_for_project(valid_gid, params))
        
        # Format the results using the schema
        task_responses = []
        for task in tasks:
            task_responses.append({
                "gid": task.get("gid", ""),
                "name": task.get("name", ""),
                "assignee": task.get("assignee", {}),
                "due_on": task.get("due_on"),
                "completed": task.get("completed", False),
                "completed_at": task.get("completed_at"),
                "created_at": task.get("created_at"), # Added created_at
                "notes": task.get("notes", ""),
                "projects": [{"gid": valid_gid}]  # Add the project as parent
            })
            
        # Create response using the schema
        response = TasksListResponse.from_api(task_responses)
        
        # Convert to serializable dictionary
        self.logger.debug(f"Project tasks response object: {response}")
        serialized_response = dataclass_to_dict(response)
        self.logger.debug(f"Serialized project tasks response: {serialized_response}")
        
        return serialized_response
    
    @handle_api_error
    def get_task_details(self, task_gid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific task.
        
        Args:
            task_gid: The GID of the task
            
        Returns:
            Dictionary with task details
        """
        # Validate task_gid
        valid_gid = self.validate_gid_param(task_gid, "task_gid")
        if not valid_gid:
            return {
                "status": "error",
                "error": f"Invalid task GID: {task_gid}"
            }
            
        # Apply rate limiting
        self._apply_rate_limit()
        
        self.logger.info(f"Getting details for task GID: {valid_gid}")
        
        # Make API call with expanded fields
        opts = {
            'opt_fields': 'name,gid,assignee,assignee.name,due_on,completed,completed_at,created_at,' # Added created_at
                        'notes,projects,projects.name,tags,tags.name,'
                        'custom_fields,custom_fields.name,custom_fields.type,'
                        'custom_fields.enum_value,parent,parent.name,dependencies'
        }
        task = self.api_instances["_tasks_api"].get_task(valid_gid, opts=opts)
        
        # Create response using the schema
        response = TaskResponse.from_api(task)
        
        # Convert to serializable dictionary
        self.logger.debug(f"Task details response object: {response}")
        serialized_response = dataclass_to_dict(response)
        self.logger.debug(f"Serialized task details response: {serialized_response}")
        
        return serialized_response
    
    @handle_api_error
    def search_tasks(self, search_text: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for tasks by name or description across all projects in the portfolio.
        
        Args:
            search_text: Text to search for in task names or descriptions
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not search_text:
            return {
                "status": "error",
                "error": "Search text is required"
            }
            
        if not self.portfolio_gid or self.portfolio_gid == "your_portfolio_gid_here":
            return self.handle_missing_portfolio()
            
        self.logger.info(f"Searching for tasks with text: {search_text}")
        
        # First, get all projects in the portfolio
        portfolio_projects_result = self.get_portfolio_projects()
        
        if portfolio_projects_result.get("status") != "success":
            return portfolio_projects_result
            
        # Get a list of project GIDs
        project_gids = []
        for project in portfolio_projects_result.get("projects", []):
            project_gids.append(project.get("gid"))
            
        if not project_gids:
            return {
                "status": "error",
                "error": "No projects found in portfolio"
            }
            
        # Search tasks across all projects
        matching_tasks = []
        for project_gid in project_gids:
            # Get tasks for this project
            tasks_result = self.get_project_tasks(project_gid, limit=100)
            
            if tasks_result.get("status") != "success":
                continue  # Skip this project if there was an error
                
            # Filter tasks by search text
            for task in tasks_result.get("tasks", []):
                task_name = task.get("name", "").lower()
                task_notes = task.get("notes", "").lower()
                
                if (search_text.lower() in task_name or 
                    search_text.lower() in task_notes):
                    # Add project name to each task
                    matching_tasks.append(task)
                    
                    # Stop if we've reached the limit
                    if len(matching_tasks) >= limit:
                        break
                        
            # Stop if we've reached the limit
            if len(matching_tasks) >= limit:
                break
                
        # Format the response
        return {
            "status": "success",
            "tasks": matching_tasks,
            "search_text": search_text,
            "task_count": len(matching_tasks)
        }
    
    @handle_api_error
    def get_task_subtasks(self, task_gid: str) -> Dict[str, Any]:
        """
        Get subtasks for a specific task.
        
        Args:
            task_gid: The GID of the parent task
            
        Returns:
            Dictionary with list of subtasks
        """
        # Validate task_gid
        valid_gid = self.validate_gid_param(task_gid, "task_gid")
        if not valid_gid:
            return {
                "status": "error",
                "error": f"Invalid task GID: {task_gid}"
            }
            
        # Apply rate limiting
        self._apply_rate_limit()
        
        self.logger.info(f"Getting subtasks for task GID: {valid_gid}")
        
        # Make API call
        opts = {
            'opt_fields': 'name,gid,assignee,assignee.name,due_on,'
                        'completed,completed_at,created_at,notes' # Added created_at
        }
        
        subtasks = list(self.api_instances["_tasks_api"].get_subtasks_for_task(valid_gid, opts=opts))
        
        # Format the results
        formatted_subtasks = []
        for task in subtasks:
            formatted_subtasks.append({
                "gid": task.get("gid", ""),
                "name": task.get("name", ""),
                "assignee": task.get("assignee", {}),
                "due_on": task.get("due_on"),
                "completed": task.get("completed", False),
                "completed_at": task.get("completed_at"),
                "created_at": task.get("created_at"), # Added created_at
                "notes": task.get("notes", "")
            })
            
        # Create response using the schema
        response = TasksListResponse.from_api(formatted_subtasks)
        
        # Convert to serializable dictionary
        self.logger.debug(f"Task subtasks response object: {response}")
        serialized_response = dataclass_to_dict(response)
        self.logger.debug(f"Serialized task subtasks response: {serialized_response}")
        
        return serialized_response
    
    @handle_api_error
    def get_task_by_name(self, task_name: str, project_gid: Optional[str] = None) -> Dict[str, Any]:
        """
        Find a task by name within a project or across all projects.
        
        Args:
            task_name: Name of the task to search for
            project_gid: Optional project GID to search within
            
        Returns:
            Dictionary with search results
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not task_name:
            return {
                "status": "error",
                "error": "Task name is required"
            }
            
        # If project_gid is provided, search only in that project
        if project_gid:
            valid_gid = self.validate_gid_param(project_gid, "project_gid")
            if not valid_gid:
                return {
                    "status": "error",
                    "error": f"Invalid project GID: {project_gid}"
                }
                
            self.logger.info(f"Searching for task '{task_name}' in project GID: {valid_gid}")
            
            # Get tasks for this project
            tasks_result = self.get_project_tasks(valid_gid, limit=100)
            
            if tasks_result.get("status") != "success":
                return tasks_result
                
            # Find the task by name
            matching_tasks = []
            for task in tasks_result.get("tasks", []):
                if task_name.lower() in task.get("name", "").lower():
                    matching_tasks.append(task)
                    
            # Return the best match or an error
            if matching_tasks:
                best_match = matching_tasks[0]  # Assume first match is best
                return {
                    "status": "success",
                    "task": best_match,
                    "task_gid": best_match.get("gid", ""),
                    "task_name": best_match.get("name", ""),
                    "all_matches": matching_tasks,
                    "match_count": len(matching_tasks)
                }
            else:
                return {
                    "status": "error",
                    "error": f"No tasks found matching name: {task_name}",
                    "all_matches": [],
                    "match_count": 0
                }
        
        # If no project_gid, search across all projects
        return self.search_tasks(task_name)
