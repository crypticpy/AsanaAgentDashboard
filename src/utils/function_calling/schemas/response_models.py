"""
Response models for standardizing API responses.

This module defines standardized data structures for API responses to ensure
consistent formatting of data returned from tool functions.
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class BaseResponse:
    """Base response class for all API responses."""
    status: str = "success"
    error: Optional[str] = None
    system_message: Optional[str] = None


@dataclass
class ProjectResponse:
    """Response model for project data."""
    gid: str
    name: str
    status: str = "success"
    error: Optional[str] = None
    system_message: Optional[str] = None
    owner: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    due_on: Optional[str] = None
    start_on: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None
    members: List[Dict[str, Any]] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, project_data: Dict[str, Any]) -> 'ProjectResponse':
        """Create a ProjectResponse from raw API data."""
        return cls(
            gid=project_data.get("gid", ""),
            name=project_data.get("name", ""),
            owner=project_data.get("owner", {}),
            created_at=project_data.get("created_at"),
            due_on=project_data.get("due_on"),
            start_on=project_data.get("start_on"),
            completed=project_data.get("completed", False),
            completed_at=project_data.get("completed_at"),
            members=project_data.get("members", []),
            custom_fields=project_data.get("custom_fields", {})
        )


@dataclass
class ProjectsListResponse(BaseResponse):
    """Response model for a list of projects."""
    projects: List[ProjectResponse] = field(default_factory=list)
    project_count: int = 0
    
    @classmethod
    def from_api(cls, projects_data: List[Dict[str, Any]]) -> 'ProjectsListResponse':
        """Create a ProjectsListResponse from raw API data."""
        if not projects_data:
            return cls(
                projects=[],
                project_count=0
            )
            
        projects = [ProjectResponse.from_api(p) for p in projects_data]
        return cls(
            projects=projects,
            project_count=len(projects)
        )


@dataclass
class TaskResponse:
    """Response model for task data."""
    gid: str
    name: str
    status: str = "success"
    error: Optional[str] = None
    system_message: Optional[str] = None
    assignee: Optional[Dict[str, Any]] = None
    due_on: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None
    projects: List[Dict[str, str]] = field(default_factory=list)
    tags: List[Dict[str, str]] = field(default_factory=list)
    notes: str = ""
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, task_data: Dict[str, Any]) -> 'TaskResponse':
        """Create a TaskResponse from raw API data."""
        return cls(
            gid=task_data.get("gid", ""),
            name=task_data.get("name", ""),
            assignee=task_data.get("assignee", {}),
            due_on=task_data.get("due_on"),
            completed=task_data.get("completed", False),
            completed_at=task_data.get("completed_at"),
            projects=task_data.get("projects", []),
            tags=task_data.get("tags", []),
            notes=task_data.get("notes", ""),
            custom_fields=task_data.get("custom_fields", {})
        )


@dataclass
class TasksListResponse(BaseResponse):
    """Response model for a list of tasks."""
    tasks: List[TaskResponse] = field(default_factory=list)
    task_count: int = 0
    
    @classmethod
    def from_api(cls, tasks_data: List[Dict[str, Any]]) -> 'TasksListResponse':
        """Create a TasksListResponse from raw API data."""
        if not tasks_data:
            return cls(
                tasks=[],
                task_count=0
            )
            
        tasks = [TaskResponse.from_api(t) for t in tasks_data]
        return cls(
            tasks=tasks,
            task_count=len(tasks)
        )


@dataclass
class UserResponse:
    """Response model for user data."""
    gid: str
    name: str
    status: str = "success"
    error: Optional[str] = None
    system_message: Optional[str] = None
    email: Optional[str] = None
    
    @classmethod
    def from_api(cls, user_data: Dict[str, Any]) -> 'UserResponse':
        """Create a UserResponse from raw API data."""
        return cls(
            gid=user_data.get("gid", ""),
            name=user_data.get("name", ""),
            email=user_data.get("email")
        )


@dataclass
class UsersListResponse(BaseResponse):
    """Response model for a list of users."""
    users: List[UserResponse] = field(default_factory=list)
    user_count: int = 0
    
    @classmethod
    def from_api(cls, users_data: List[Dict[str, Any]]) -> 'UsersListResponse':
        """Create a UsersListResponse from raw API data."""
        if not users_data:
            return cls(
                users=[],
                user_count=0
            )
            
        users = [UserResponse.from_api(u) for u in users_data]
        return cls(
            users=users,
            user_count=len(users)
        )


@dataclass
class TaskDistributionResponse(BaseResponse):
    """Response model for task distribution data."""
    assignees: List[Dict[str, Any]] = field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0
    incomplete_tasks: int = 0
    unassigned_tasks: int = 0


@dataclass
class TaskCompletionTrendResponse(BaseResponse):
    """Response model for task completion trend data."""
    dates: List[str] = field(default_factory=list)
    completed_counts: List[int] = field(default_factory=list)
    created_counts: List[int] = field(default_factory=list)
    total_completed: int = 0
    total_created: int = 0


@dataclass
class SearchResponse(BaseResponse):
    """Response model for search results."""
    results: List[Dict[str, Any]] = field(default_factory=list)
    result_count: int = 0


@dataclass
class VisualizationResponse(BaseResponse):
    """Response model for visualization data."""
    chart_data: Dict[str, Any] = field(default_factory=dict)
    chart_type: str = ""
    title: str = ""


def format_error_response(error_message: str, 
                         system_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format a standardized error response.
    
    Args:
        error_message: Error message to include in the response
        system_message: Optional system message for logging/debugging
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "status": "error",
        "error": error_message,
        "system_message": system_message or "An error occurred while processing your request."
    }
