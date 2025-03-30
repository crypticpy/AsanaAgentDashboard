"""
Asana API tool functions for direct LLM function calling.

This module defines all the Asana API tools that can be called directly
by the LLM through OpenAI's function calling capability.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import asana
import streamlit as st
from datetime import datetime, timedelta

logger = logging.getLogger("asana_function_tools")

class AsanaToolSet:
    """
    Provides a set of tools for the LLM to interact directly with the Asana API.
    Each method represents a function that can be called by the LLM.
    """
    
    def __init__(self, api_instances: Dict[str, Any]):
        """
        Initialize the tool set with Asana API instances.
        
        Args:
            api_instances: Dictionary of Asana API instances
        """
        self.api_instances = api_instances
        
        # Get portfolio_gid and team_gid from session state if available
        self.portfolio_gid = st.session_state.get("portfolio_gid", "")
        self.team_gid = st.session_state.get("team_gid", "")
        
        # Cache for user GIDs to avoid repeated lookups
        self._user_gid_cache = {}
        
        # Rate limiting settings
        self.last_call_time = 0
        self.min_call_interval = 1  # 1 second between calls
        
        # Add logger to the instance
        self.logger = logger
        
        logger.info(f"AsanaToolSet initialized with portfolio_gid={self.portfolio_gid}, team_gid={self.team_gid}")
    
    def _apply_rate_limit(self):
        """Apply rate limiting to API calls."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def _safe_get(self, data, *keys):
        """
        Safely get nested values from a dictionary.
        
        Args:
            data: Dictionary to extract from
            *keys: Keys to traverse
            
        Returns:
            Value or None if not found
        """
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        return data
    
    def _find_user_gid(self, assignee_name: str) -> Optional[str]:
        """
        Find the GID of a user by name.
        
        Args:
            assignee_name: Name of the assignee
            
        Returns:
            User GID or None if not found
        """
        # Check cache first
        if assignee_name in self._user_gid_cache:
            return self._user_gid_cache[assignee_name]
            
        # Use team_gid to get users if available
        if self.team_gid:
            try:
                users = list(self.api_instances["_teams_api"].get_users_for_team(
                    self.team_gid,
                    {'opt_fields': 'name,gid'}
                ))
                
                for user in users:
                    if assignee_name.lower() in user["name"].lower():
                        # Cache the result
                        self._user_gid_cache[assignee_name] = user["gid"]
                        return user["gid"]
            except Exception as e:
                logger.warning(f"Error getting users for team: {e}")
        
        # No match found
        return None
    
    def get_portfolio_projects(self, portfolio_gid: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all projects in a portfolio.
        
        Args:
            portfolio_gid: Portfolio GID (optional, will use the one from session state if not provided)
            
        Returns:
            Dictionary with list of projects and status
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Use provided portfolio_gid or default from session state
            if not portfolio_gid:
                portfolio_gid = self.portfolio_gid or st.session_state.get("portfolio_gid", "")
                self.logger.info(f"Using portfolio_gid from session state: {portfolio_gid}")
            
            if not portfolio_gid or portfolio_gid == "your_portfolio_gid_here":
                logger.error("No valid portfolio GID found in configuration. This is a system configuration issue.")
                return {
                    "status": "error",
                    "error": "No valid portfolio GID found in the application settings. Please contact your administrator to configure a valid portfolio.",
                    "project_count": 0,
                    "projects": [],
                    "system_message": "This is a configuration issue that requires administrator attention."
                }
            
            # Update our cached value
            self.portfolio_gid = portfolio_gid
            
            logger.info(f"Fetching projects for portfolio GID: {portfolio_gid}")
            
            # Make API call
            opts = {
                'opt_fields': 'name,gid,created_at,completed,start_on,due_on,owner,owner.name',
            }
            projects = list(self.api_instances["_portfolios_api"].get_items_for_portfolio(portfolio_gid, opts=opts))
            
            # Format the results
            formatted_projects = []
            for project in projects:
                owner_name = self._safe_get(project, "owner", "name") or "Unassigned"
                formatted_projects.append({
                    "name": project.get("name", "Unnamed"),
                    "gid": project.get("gid", ""),
                    "due_date": project.get("due_on"),
                    "start_date": project.get("start_on"),
                    "owner": owner_name,
                    "completed": project.get("completed", False)
                })
            
            # Group projects by owner
            owners = {}
            for project in formatted_projects:
                owner = project["owner"]
                if owner not in owners:
                    owners[owner] = []
                owners[owner].append(project["name"])
            
            # Format owners summary
            owners_summary = []
            for owner, projects in owners.items():
                owners_summary.append({
                    "name": owner,
                    "project_count": len(projects),
                    "projects": projects
                })
            
            return {
                "status": "success",
                "portfolio_gid": portfolio_gid,
                "project_count": len(formatted_projects),
                "projects": formatted_projects,
                "owners": owners_summary
            }
            
        except Exception as e:
            logger.error(f"Error getting projects for portfolio {portfolio_gid}: {e}")
            return {
                "status": "error",
                "error": "Error fetching projects from Asana. Please ensure your Asana integration is correctly configured.",
                "system_message": f"API Error: {str(e)}",
                "project_count": 0,
                "projects": []
            }
    
    def get_project_details(self, project_gid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific project.
        
        Args:
            project_gid: Project GID
            
        Returns:
            Dictionary with project details
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Make API call
            opts = {
                'opt_fields': 'name,gid,created_at,modified_at,owner.name,due_on,start_on,notes,completed,members,followers_count',
            }
            project = self.api_instances["_projects_api"].get_project(project_gid, opts=opts)
            
            return {
                "status": "success",
                "project": {
                    "name": project.get("name", "Unnamed"),
                    "gid": project.get("gid", ""),
                    "notes": project.get("notes", ""),
                    "due_date": project.get("due_on"),
                    "start_date": project.get("start_on"),
                    "created_at": project.get("created_at"),
                    "modified_at": project.get("modified_at"),
                    "owner": self._safe_get(project, "owner", "name") or "Unassigned",
                    "completed": project.get("completed", False),
                    "members_count": len(project.get("members", [])),
                    "followers_count": project.get("followers_count", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting details for project {project_gid}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "project": {}
            }
    
    def get_project_tasks(self, project_gid: str, limit: int = 50, completed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Get tasks for a specific project.
        
        Args:
            project_gid: Project GID
            limit: Maximum number of tasks to return
            completed: Filter for completed tasks (None for all tasks)
            
        Returns:
            Dictionary with task list and stats
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Make API call
            opts = {
                'opt_fields': 'name,gid,created_at,completed,due_on,completed_at,assignee.name,memberships.section.name,tags,num_subtasks',
                'limit': limit
            }
            
            # Get raw tasks
            tasks = list(self.api_instances["_tasks_api"].get_tasks_for_project(project_gid, opts=opts))
            
            # Get project name for context
            project_name = ""
            try:
                project = self.api_instances["_projects_api"].get_project(project_gid, opts={'opt_fields': 'name'})
                project_name = project.get("name", "Unknown Project")
            except:
                pass
                
            # Process tasks
            formatted_tasks = []
            completed_count = 0
            overdue_count = 0
            today = datetime.now().date()
            
            for task in tasks:
                # Apply completed filter if specified
                if completed is not None and task.get("completed", False) != completed:
                    continue
                    
                # Check if task is overdue
                due_on = task.get("due_on")
                is_overdue = False
                if due_on and not task.get("completed", False):
                    due_date = datetime.strptime(due_on, "%Y-%m-%d").date()
                    is_overdue = due_date < today
                
                # Count stats
                if task.get("completed", False):
                    completed_count += 1
                if is_overdue:
                    overdue_count += 1
                
                # Format task
                formatted_task = {
                    "name": task.get("name", "Unnamed"),
                    "gid": task.get("gid", ""),
                    "status": "Completed" if task.get("completed", False) else "In Progress",
                    "due_date": due_on,
                    "created_at": task.get("created_at"),
                    "completed_at": task.get("completed_at"),
                    "assignee": self._safe_get(task, "assignee", "name") or "Unassigned",
                    "section": self._safe_get(task, "memberships", 0, "section", "name") or "No section",
                    "tags": [tag.get("name", "") for tag in task.get("tags", [])],
                    "num_subtasks": task.get("num_subtasks", 0),
                    "is_overdue": is_overdue
                }
                
                formatted_tasks.append(formatted_task)
            
            # Calculate stats
            total_tasks = len(formatted_tasks)
            completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
            overdue_rate = (overdue_count / (total_tasks - completed_count) * 100) if (total_tasks - completed_count) > 0 else 0
                
            return {
                "status": "success",
                "project_name": project_name,
                "task_count": total_tasks,
                "completed_count": completed_count,
                "in_progress_count": total_tasks - completed_count,
                "overdue_count": overdue_count,
                "completion_rate": round(completion_rate, 1),
                "overdue_rate": round(overdue_rate, 1),
                "tasks": formatted_tasks
            }
            
        except Exception as e:
            logger.error(f"Error getting tasks for project {project_gid}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_count": 0,
                "tasks": []
            }
    
    def get_task_details(self, task_gid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific task.
        
        Args:
            task_gid: Task GID
            
        Returns:
            Dictionary with task details
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Make API call
            opts = {
                'opt_fields': 'name,gid,created_at,completed,due_on,completed_at,assignee.name,notes,projects,memberships.project.name,memberships.section.name,tags,parent,custom_fields,num_subtasks,followers_count,liked',
            }
            task = self.api_instances["_tasks_api"].get_task(task_gid, opts=opts)
            
            # Get project name
            project_name = "Unknown Project"
            if task.get("memberships"):
                for membership in task.get("memberships", []):
                    if self._safe_get(membership, "project", "name"):
                        project_name = self._safe_get(membership, "project", "name")
                        break
            
            # Process custom fields
            custom_fields = {}
            for field in task.get("custom_fields", []):
                if field_name := field.get("name"):
                    custom_fields[field_name] = field.get("display_value")
            
            return {
                "status": "success",
                "task": {
                    "name": task.get("name", "Unnamed"),
                    "gid": task.get("gid", ""),
                    "status": "Completed" if task.get("completed", False) else "In Progress",
                    "due_date": task.get("due_on"),
                    "created_at": task.get("created_at"),
                    "completed_at": task.get("completed_at"),
                    "assignee": self._safe_get(task, "assignee", "name") or "Unassigned",
                    "notes": task.get("notes", ""),
                    "project": project_name,
                    "section": self._safe_get(task, "memberships", 0, "section", "name") or "No section",
                    "tags": [tag.get("name", "") for tag in task.get("tags", [])],
                    "parent_task": self._safe_get(task, "parent", "name"),
                    "custom_fields": custom_fields,
                    "num_subtasks": task.get("num_subtasks", 0),
                    "followers_count": task.get("followers_count", 0),
                    "liked": task.get("liked", False)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting details for task {task_gid}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task": {}
            }
    
    def search_tasks(self, query: str, assignee: Optional[str] = None, completed: Optional[bool] = None, limit: int = 20) -> Dict[str, Any]:
        """
        Search for tasks based on various criteria.
        
        Args:
            query: Search text (can be empty)
            assignee: Filter by assignee name (optional)
            completed: Filter for completed status (optional)
            limit: Maximum number of tasks to return
            
        Returns:
            Dictionary with search results
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # We'll use a different approach - first get all projects from the portfolio
            # and then get tasks from each project
            if not self.portfolio_gid:
                return {
                    "status": "error",
                    "error": "No portfolio GID set. Please provide a portfolio_gid in the configuration.",
                    "task_count": 0,
                    "tasks": []
                }
            
            # Get projects in the portfolio
            projects_response = self.get_portfolio_projects()
            if projects_response["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to get projects: {projects_response.get('error', 'Unknown error')}",
                    "task_count": 0,
                    "tasks": []
                }
            
            # Get tasks for each project
            all_matching_tasks = []
            for project in projects_response["projects"]:
                project_gid = project["gid"]
                try:
                    # Get tasks for this project
                    opts = {
                        'opt_fields': 'name,gid,completed,due_on,assignee.name,projects.name',
                        'limit': 100  # Get more to filter down later
                    }
                    
                    # Add completed filter if specified
                    if completed is not None:
                        opts['completed'] = completed
                    
                    project_tasks = list(self.api_instances["_tasks_api"].get_tasks_for_project(project_gid, opts=opts))
                    
                    # Filter by assignee if specified
                    if assignee:
                        project_tasks = [
                            task for task in project_tasks 
                            if self._safe_get(task, "assignee", "name") and 
                               assignee.lower() in self._safe_get(task, "assignee", "name").lower()
                        ]
                    
                    # Filter by query if specified
                    if query:
                        project_tasks = [
                            task for task in project_tasks
                            if query.lower() in task.get("name", "").lower()
                        ]
                    
                    # Add to our list
                    all_matching_tasks.extend(project_tasks)
                    
                    # Apply limit
                    if len(all_matching_tasks) >= limit:
                        all_matching_tasks = all_matching_tasks[:limit]
                        break
                        
                except Exception as e:
                    logger.warning(f"Error getting tasks for project {project_gid}: {e}")
                    continue
            
            # Process matching tasks
            formatted_tasks = []
            for task in all_matching_tasks:
                # Get project names
                project_names = []
                if task.get("projects"):
                    for project in task.get("projects", []):
                        if project_name := project.get("name"):
                            project_names.append(project_name)
                else:
                    # Try to get from memberships
                    for membership in task.get("memberships", []):
                        if project_name := self._safe_get(membership, "project", "name"):
                            project_names.append(project_name)
                            break
                
                formatted_task = {
                    "name": task.get("name", "Unnamed"),
                    "gid": task.get("gid", ""),
                    "status": "Completed" if task.get("completed", False) else "In Progress",
                    "due_date": task.get("due_on"),
                    "assignee": self._safe_get(task, "assignee", "name") or "Unassigned",
                    "projects": project_names
                }
                
                formatted_tasks.append(formatted_task)
                
            return {
                "status": "success",
                "search_query": query,
                "assignee_filter": assignee,
                "task_count": len(formatted_tasks),
                "tasks": formatted_tasks
            }
            
        except Exception as e:
            logger.error(f"Error searching tasks: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_count": 0,
                "tasks": []
            }
    
    def get_tasks_by_assignee(self, assignee: str, completed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Get tasks assigned to a specific person across all projects in the portfolio.
        
        Args:
            assignee: Name of the assignee
            completed: Filter for completed status (optional)
            
        Returns:
            Dictionary with task information
        """
        # This is a wrapper around search_tasks with assignee focus
        result = self.search_tasks("", assignee=assignee, completed=completed, limit=100)
        
        if result["status"] != "success":
            return result
            
        # Reformat to better emphasize the assignee focus
        tasks = result["tasks"]
        
        # If no tasks found, return quickly
        if not tasks:
            return {
                "status": "success",
                "assignee": assignee,
                "total_tasks": 0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "result": f"No tasks found for assignee '{assignee}'.",
                "tasks": []
            }
            
        # Count tasks by status
        completed_count = len([t for t in tasks if t["status"] == "Completed"])
        in_progress_count = len([t for t in tasks if t["status"] == "In Progress"])
        
        # Get projects the assignee is working on
        projects = set()
        for task in tasks:
            for project in task.get("projects", []):
                projects.add(project)
        
        assignee_result = {
            "status": "success",
            "assignee": assignee,
            "total_tasks": len(tasks),
            "completed_tasks": completed_count,
            "in_progress_tasks": in_progress_count,
            "projects": list(projects),
            "tasks": tasks,
            "result": f"Assignee: {assignee}\n"
                    f"Total tasks: {len(tasks)}\n"
                    f"Completed tasks: {completed_count}\n"
                    f"In progress tasks: {in_progress_count}\n"
                    f"Working on projects: {', '.join(projects) if projects else 'None'}"
        }
        
        return assignee_result
    
    def get_task_distribution_by_assignee(self) -> Dict[str, Any]:
        """
        Get task distribution statistics across all assignees.
        
        Returns:
            Dictionary with assignee workload statistics
        """
        try:
            # First, we need to get all tasks across projects
            all_tasks = []
            
            # Get projects in the portfolio
            if not self.portfolio_gid:
                return {
                    "status": "error",
                    "error": "No portfolio GID set. Please provide a portfolio_gid in the configuration.",
                    "assignee_count": 0,
                    "assignees": []
                }
                
            portfolio_projects = self.get_portfolio_projects()
            
            if portfolio_projects["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to get projects: {portfolio_projects.get('error', 'Unknown error')}",
                    "assignee_count": 0,
                    "assignees": []
                }
                
            for project in portfolio_projects["projects"]:
                project_tasks = self.get_project_tasks(project["gid"], limit=100)
                if project_tasks["status"] == "success":
                    all_tasks.extend(project_tasks.get("tasks", []))
                
            # Group tasks by assignee
            assignee_stats = {}
            for task in all_tasks:
                assignee = task["assignee"]
                if assignee not in assignee_stats:
                    assignee_stats[assignee] = {
                        "total_tasks": 0,
                        "completed_tasks": 0,
                        "in_progress_tasks": 0,
                        "overdue_tasks": 0,
                        "projects": set()
                    }
                
                assignee_stats[assignee]["total_tasks"] += 1
                if task["status"] == "Completed":
                    assignee_stats[assignee]["completed_tasks"] += 1
                else:
                    assignee_stats[assignee]["in_progress_tasks"] += 1
                    if task.get("is_overdue", False):
                        assignee_stats[assignee]["overdue_tasks"] += 1
                
                if "project" in task:
                    assignee_stats[assignee]["projects"].add(task["project"])
            
            # Format results
            formatted_results = []
            for assignee, stats in assignee_stats.items():
                # Convert projects from set to list
                projects_list = list(stats["projects"])
                
                # Calculate completion rate
                completion_rate = 0
                if stats["total_tasks"] > 0:
                    completion_rate = (stats["completed_tasks"] / stats["total_tasks"]) * 100
                
                formatted_results.append({
                    "assignee": assignee,
                    "total_tasks": stats["total_tasks"],
                    "completed_tasks": stats["completed_tasks"],
                    "in_progress_tasks": stats["in_progress_tasks"],
                    "overdue_tasks": stats["overdue_tasks"],
                    "completion_rate": round(completion_rate, 1),
                    "projects": projects_list,
                    "project_count": len(projects_list)
                })
            
            # Sort by total tasks (descending)
            formatted_results.sort(key=lambda x: x["total_tasks"], reverse=True)
            
            return {
                "status": "success",
                "assignee_count": len(formatted_results),
                "assignees": formatted_results
            }
            
        except Exception as e:
            logger.error(f"Error getting task distribution: {e}")
            return {
                "status": "error",
                "error": str(e),
                "assignee_count": 0,
                "assignees": []
            }
    
    def get_task_completion_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Get task completion trend over a specified time period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with completion trend data
        """
        try:
            # First, we need to get all tasks across projects
            all_tasks = []
            
            # Get projects in the portfolio
            if not self.portfolio_gid:
                return {
                    "status": "error",
                    "error": "No portfolio GID set. Please provide a portfolio_gid in the configuration.",
                    "trend_data": []
                }
                
            portfolio_projects = self.get_portfolio_projects()
            
            if portfolio_projects["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to get projects: {portfolio_projects.get('error', 'Unknown error')}",
                    "trend_data": []
                }
                
            for project in portfolio_projects["projects"]:
                project_tasks = self.get_project_tasks(project["gid"], limit=100)
                if project_tasks["status"] == "success":
                    all_tasks.extend(project_tasks.get("tasks", []))
            
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Initialize trend data
            trend_data = {}
            current_date = start_date
            while current_date <= end_date:
                trend_data[current_date.isoformat()] = {
                    "completed_tasks": 0,
                    "created_tasks": 0,
                    "date": current_date.isoformat()
                }
                current_date += timedelta(days=1)
            
            # Process tasks
            for task in all_tasks:
                # Check completed tasks
                if task.get("completed_at"):
                    try:
                        completed_date = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00")).date()
                        if start_date <= completed_date <= end_date:
                            date_str = completed_date.isoformat()
                            if date_str in trend_data:
                                trend_data[date_str]["completed_tasks"] += 1
                    except:
                        pass
                
                # Check created tasks
                if task.get("created_at"):
                    try:
                        created_date = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")).date()
                        if start_date <= created_date <= end_date:
                            date_str = created_date.isoformat()
                            if date_str in trend_data:
                                trend_data[date_str]["created_tasks"] += 1
                    except:
                        pass
            
            # Convert to list and sort by date
            trend_list = list(trend_data.values())
            trend_list.sort(key=lambda x: x["date"])
            
            # Calculate cumulative stats
            cumulative_created = 0
            cumulative_completed = 0
            for day in trend_list:
                cumulative_created += day["created_tasks"]
                cumulative_completed += day["completed_tasks"]
                day["cumulative_created"] = cumulative_created
                day["cumulative_completed"] = cumulative_completed
            
            return {
                "status": "success",
                "days_analyzed": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_created": cumulative_created,
                "total_completed": cumulative_completed,
                "trend_data": trend_list
            }
            
        except Exception as e:
            logger.error(f"Error getting task completion trend: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trend_data": []
            }
    
    def get_projects_by_owner(self, owner_name: str, portfolio_gid: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all projects owned by a specific person.
        
        Args:
            owner_name: Name of the project owner
            portfolio_gid: Portfolio GID (optional, will use the one from session state if not provided)
            
        Returns:
            Dictionary with list of projects owned by the person
        """
        try:
            # Get all projects in the portfolio
            all_projects_result = self.get_portfolio_projects(portfolio_gid)
            
            if all_projects_result["status"] != "success":
                return {
                    "status": "error",
                    "error": all_projects_result.get("error", "Unknown error fetching projects"),
                    "owner": owner_name,
                    "project_count": 0,
                    "projects": []
                }
            
            # Find the owner in the owners summary
            matching_owners = []
            for owner in all_projects_result.get("owners", []):
                if owner_name.lower() in owner["name"].lower():
                    matching_owners.append(owner)
            
            # If no exact match, try to find projects with matching owner
            if not matching_owners:
                # Check individual projects
                matching_projects = []
                for project in all_projects_result.get("projects", []):
                    if owner_name.lower() in project["owner"].lower():
                        matching_projects.append(project)
                
                if matching_projects:
                    return {
                        "status": "success",
                        "owner": owner_name,
                        "project_count": len(matching_projects),
                        "projects": matching_projects
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"No projects found with owner matching '{owner_name}'",
                        "owner": owner_name,
                        "project_count": 0,
                        "projects": []
                    }
            
            # Combine projects from all matching owners
            all_matching_projects = []
            for owner in matching_owners:
                # Find the full project details
                for project_name in owner["projects"]:
                    # Find the project in the original list
                    for full_project in all_projects_result.get("projects", []):
                        if full_project["name"] == project_name:
                            all_matching_projects.append(full_project)
                            break
            
            return {
                "status": "success",
                "owner": owner_name,
                "matching_owners": [owner["name"] for owner in matching_owners],
                "project_count": len(all_matching_projects),
                "projects": all_matching_projects
            }
            
        except Exception as e:
            logger.error(f"Error getting projects for owner {owner_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "owner": owner_name,
                "project_count": 0,
                "projects": []
            }
    
    def get_project_gid_by_name(self, project_name: str) -> Optional[str]:
        """
        Find a project's GID by its name.
        
        Args:
            project_name: Name of the project to find
            
        Returns:
            Project GID if found, None otherwise
        """
        try:
            # Get all projects in the portfolio
            all_projects_result = self.get_portfolio_projects()
            
            if all_projects_result["status"] != "success":
                return None
            
            # Look for a matching project name
            for project in all_projects_result.get("projects", []):
                if project_name.lower() in project["name"].lower():
                    return project["gid"]
                
            return None
        except Exception as e:
            logger.error(f"Error finding project GID for '{project_name}': {e}")
            return None
    
    def get_project_info_by_name(self, project_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a project by its name.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary with project details and tasks
        """
        try:
            # Find the project GID first
            project_gid = self.get_project_gid_by_name(project_name)
            
            if not project_gid:
                return {
                    "status": "error",
                    "error": f"Project with name '{project_name}' not found",
                    "project_name": project_name
                }
            
            # Get project details
            project_details = self.get_project_details(project_gid)
            
            if project_details["status"] != "success":
                return project_details
            
            # Get project tasks
            project_tasks = self.get_project_tasks(project_gid, limit=100)
            
            # Combine the information
            result = {
                "status": "success",
                "project_name": project_name,
                "project_gid": project_gid,
                "project_details": project_details.get("project", {}),
                "task_count": project_tasks.get("task_count", 0),
                "completed_count": project_tasks.get("completed_count", 0),
                "in_progress_count": project_tasks.get("in_progress_count", 0),
                "completion_rate": project_tasks.get("completion_rate", 0),
                "tasks": project_tasks.get("tasks", [])
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting project info for '{project_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "project_name": project_name
            } 