"""
User-related tools for interacting with Asana users.

This module provides tools for working with Asana users, including
getting user information, finding users, and retrieving tasks assigned to users.
"""
from typing import Dict, Any, List, Optional, Union
import logging

from src.utils.function_calling.tools.base import BaseAsanaTools
from src.utils.function_calling.tools.task_tools import TaskTools
from src.utils.function_calling.utils import (
    handle_api_error, 
    safe_get,
    dataclass_to_dict
)
from src.utils.function_calling.schemas import (
    UserResponse, UsersListResponse, TasksListResponse
)


class UserTools(BaseAsanaTools):
    """Tools for working with Asana users and assignments."""
    
    @handle_api_error
    def get_users_in_team(self) -> Dict[str, Any]:
        """
        Get all users in the team.
        
        Returns:
            Dictionary with list of users
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not self.team_gid or self.team_gid == "your_team_gid_here":
            return {
                "status": "error",
                "error": "No valid team GID found in the application settings. Please contact your administrator."
            }
            
        self.logger.info(f"Getting users for team GID: {self.team_gid}")
        
        # Make API call
        opts = {'opt_fields': 'name,gid,email'}
        users = list(self.api_instances["_teams_api"].get_users_for_team(self.team_gid, opts=opts))
        
        # Format the results
        formatted_users = []
        for user in users:
            formatted_users.append({
                "gid": user.get("gid", ""),
                "name": user.get("name", ""),
                "email": user.get("email")
            })
            
        # Create the response
        response = UsersListResponse.from_api(formatted_users)
        
        return vars(response)
    
    @handle_api_error
    def get_user_details(self, user_gid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific user.
        
        Args:
            user_gid: The GID of the user
            
        Returns:
            Dictionary with user details
        """
        # Validate user_gid
        valid_gid = self.validate_gid_param(user_gid, "user_gid")
        if not valid_gid:
            return {
                "status": "error",
                "error": f"Invalid user GID: {user_gid}"
            }
            
        # Apply rate limiting
        self._apply_rate_limit()
        
        self.logger.info(f"Getting details for user GID: {valid_gid}")
        
        # Make API call
        opts = {'opt_fields': 'name,gid,email,workspaces,photo'}
        user = self.api_instances["_users_api"].get_user(valid_gid, opts=opts)
        
        # Create response using the schema
        response = UserResponse.from_api(user)
        
        # Convert to serializable dictionary
        self.logger.debug(f"User details response object: {response}")
        serialized_response = dataclass_to_dict(response)
        self.logger.debug(f"Serialized user details response: {serialized_response}")
        
        return serialized_response
    
    @handle_api_error
    def find_user_by_name(self, user_name: str) -> Dict[str, Any]:
        """
        Find a user by name.
        
        Args:
            user_name: Name of the user to search for
            
        Returns:
            Dictionary with search results
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not user_name:
            return {
                "status": "error",
                "error": "User name is required"
            }
            
        if not self.team_gid or self.team_gid == "your_team_gid_here":
            return {
                "status": "error",
                "error": "No valid team GID found in the application settings. Please contact your administrator."
            }
            
        self.logger.info(f"Searching for user by name: {user_name}")
        
        # Get all users in the team
        users_result = self.get_users_in_team()
        
        if users_result.get("status") != "success":
            return users_result
            
        # Find users matching the name
        matching_users = []
        for user in users_result.get("users", []):
            if user_name.lower() in user.get("name", "").lower():
                matching_users.append(user)
                
        # Format the response
        if matching_users:
            best_match = matching_users[0]  # Assume first match is best
            return {
                "status": "success",
                "user": best_match,
                "user_gid": best_match.get("gid", ""),
                "user_name": best_match.get("name", ""),
                "all_matches": matching_users,
                "match_count": len(matching_users)
            }
        else:
            return {
                "status": "error",
                "error": f"No users found matching name: {user_name}",
                "all_matches": [],
                "match_count": 0
            }
    
    @handle_api_error
    def get_tasks_by_assignee(self, assignee_name: str, 
                            completed: Optional[bool] = None, 
                            limit: int = 50) -> Dict[str, Any]:
        """
        Get tasks assigned to a specific user.
        
        Args:
            assignee_name: Name of the task assignee
            completed: Filter for completed tasks (None for all tasks)
            limit: Maximum number of tasks to return (default: 50)
            
        Returns:
            Dictionary with list of tasks
        """
        # Verify assignee_name
        if not assignee_name:
            return {
                "status": "error",
                "error": "Assignee name is required"
            }
            
        # Apply rate limiting
        self._apply_rate_limit()
        
        # First, find the user GID from the name
        user_gid = self._find_user_gid(assignee_name)
        if not user_gid:
            return {
                "status": "error",
                "error": f"No user found with name: {assignee_name}"
            }
            
        # Find the workspace GID (required for searching tasks)
        workspace_gid = self._get_workspace_gid()
        if not workspace_gid:
            return {
                "status": "error",
                "error": "No workspace found for your account"
            }
            
        self.logger.info(f"Getting tasks for assignee: {assignee_name} (GID: {user_gid})")
        
        # Set up parameters for the API call
        params = {
            'assignee.any': user_gid,
            'limit': limit,
            'opt_fields': 'name,gid,assignee,assignee.name,due_on,completed,completed_at,notes,projects,projects.name'
        }
        
        # Only add completed filter if it's not None
        if completed is not None:
            params['completed'] = completed
            
        # Make API call to search for tasks with this assignee
        tasks = list(self.api_instances["_tasks_api"].search_tasks_for_workspace(
            workspace_gid, params))
            
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
                "notes": task.get("notes", ""),
                "projects": task.get("projects", [])
            })
            
        # Create response using the schema
        response = TasksListResponse.from_api(task_responses)
        task_list_response = dataclass_to_dict(response)
        
        # Add assignee info to the response
        task_list_response["assignee_name"] = assignee_name
        task_list_response["assignee_gid"] = user_gid
        
        # Debug the response
        self.logger.debug(f"Serialized assignee tasks response: {task_list_response}")
        
        return task_list_response
    
    @handle_api_error
    def get_user_workload(self, user_name: str) -> Dict[str, Any]:
        """
        Get workload information for a specific user.
        
        Args:
            user_name: Name of the user
            
        Returns:
            Dictionary with workload information
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not user_name:
            return {
                "status": "error",
                "error": "User name is required"
            }
            
        # Find the user GID by name
        user_gid = self._find_user_gid(user_name)
        
        if not user_gid:
            return {
                "status": "error",
                "error": f"No user found matching name: {user_name}"
            }
            
        # Get tasks assigned to the user
        complete_tasks_result = self.get_tasks_by_assignee(user_name, completed=True, limit=100)
        incomplete_tasks_result = self.get_tasks_by_assignee(user_name, completed=False, limit=100)
        
        # Calculate workload statistics
        total_complete = complete_tasks_result.get("task_count", 0) if complete_tasks_result.get("status") == "success" else 0
        total_incomplete = incomplete_tasks_result.get("task_count", 0) if incomplete_tasks_result.get("status") == "success" else 0
        
        # Count overdue tasks
        overdue_tasks = []
        if incomplete_tasks_result.get("status") == "success":
            import datetime
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            for task in incomplete_tasks_result.get("tasks", []):
                due_on = task.get("due_on")
                if due_on and due_on < today:
                    overdue_tasks.append(task)
        
        # Format the response
        return {
            "status": "success",
            "user_name": user_name,
            "user_gid": user_gid,
            "total_tasks": total_complete + total_incomplete,
            "completed_tasks": total_complete,
            "incomplete_tasks": total_incomplete,
            "overdue_tasks": len(overdue_tasks),
            "overdue_task_list": overdue_tasks
        }

    def _get_workspace_gid(self) -> Optional[str]:
        """
        Get the workspace GID for the current user.
        
        Returns:
            Workspace GID if found, None otherwise
        """
        # Check if we have a workspace_gid in the API instances
        workspace_gid = self.api_instances.get("workspace_gid")
        if workspace_gid:
            return workspace_gid
        
        # Try to get the workspace from the user's profile
        try:
            # Get the current user (me)
            current_user = self.api_instances["_users_api"].get_user("me", {'opt_fields': 'workspaces'})
            workspaces = current_user.get("workspaces", [])
            if workspaces:
                # Use the first workspace
                return workspaces[0].get("gid")
        except Exception as e:
            self.logger.warning(f"Error getting user workspaces: {e}")
        
        return None
