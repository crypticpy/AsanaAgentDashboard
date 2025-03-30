"""
Asana API utility functions for fetching and processing data from Asana.
"""
import asana
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
from datetime import datetime, timedelta, timezone
import streamlit as st

def api_error_handler(func: Callable) -> Callable:
    """
    Decorator to handle API errors gracefully.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except asana.rest.ApiException as e:
            st.error(f"API Error in {func.__name__}: {e}")
            return None
    return wrapper

def setup_asana_client(api_token: str) -> asana.ApiClient:
    """
    Set up the Asana API client.
    
    Args:
        api_token: Asana API token
        
    Returns:
        Configured Asana API client
    """
    configuration = asana.Configuration()
    configuration.access_token = api_token
    return asana.ApiClient(configuration)

def initialize_api_instances(api_client: asana.ApiClient) -> Dict[str, Any]:
    """
    Initialize Asana API instances.
    
    Args:
        api_client: Configured Asana API client
        
    Returns:
        Dictionary of API instances
    """
    return {
        "_portfolios_api": asana.PortfoliosApi(api_client),
        "_projects_api": asana.ProjectsApi(api_client),
        "_tasks_api": asana.TasksApi(api_client),
        "_sections_api": asana.SectionsApi(api_client),
        # Keep the old keys for backward compatibility
        "portfolios_api": asana.PortfoliosApi(api_client),
        "projects_api": asana.ProjectsApi(api_client),
        "tasks_api": asana.TasksApi(api_client),
        "sections_api": asana.SectionsApi(api_client)
    }

@st.cache_data(ttl=3600, hash_funcs={asana.PortfoliosApi: lambda _: None})
@api_error_handler
def get_portfolio_projects(_portfolios_api: asana.PortfoliosApi, portfolio_gid: str) -> List[Dict[str, Any]]:
    """
    Get all projects in a portfolio.
    
    Args:
        _portfolios_api: Asana Portfolios API instance
        portfolio_gid: Portfolio GID
        
    Returns:
        List of projects in the portfolio
    """
    opts = {
        'opt_fields': 'name,gid',
    }
    return list(_portfolios_api.get_items_for_portfolio(portfolio_gid, opts=opts))

@st.cache_data(ttl=3600, hash_funcs={asana.TasksApi: lambda _: None})
@api_error_handler
def get_tasks(_tasks_api: asana.TasksApi, project_gid: str) -> List[Dict[str, Any]]:
    """
    Get all tasks in a project.
    
    Args:
        _tasks_api: Asana Tasks API instance
        project_gid: Project GID
        
    Returns:
        List of tasks in the project
    """
    opts = {
        'opt_fields': 'name,completed,due_on,created_at,completed_at,assignee.name,memberships.section.name,custom_fields,tags,num_subtasks',
    }
    return list(_tasks_api.get_tasks_for_project(project_gid, opts=opts))

@st.cache_data(ttl=3600, hash_funcs={asana.SectionsApi: lambda _: None})
@api_error_handler
def get_sections(_sections_api: asana.SectionsApi, project_gid: str) -> List[Dict[str, Any]]:
    """
    Get all sections in a project.
    
    Args:
        _sections_api: Asana Sections API instance
        project_gid: Project GID
        
    Returns:
        List of sections in the project
    """
    opts = {
        'opt_fields': 'name',
    }
    return list(_sections_api.get_sections_for_project(project_gid, opts=opts))

def safe_get(data: Dict[str, Any], *keys: str) -> Optional[Any]:
    """
    Safely get a nested value from a dictionary.
    
    Args:
        data: Dictionary to get value from
        *keys: Keys to traverse
        
    Returns:
        Value if found, None otherwise
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data

def process_tasks(tasks: List[Dict[str, Any]], project_name: str, project_gid: str) -> List[Dict[str, Any]]:
    """
    Process tasks from Asana API into a standardized format.
    
    Args:
        tasks: List of tasks from Asana API
        project_name: Name of the project
        project_gid: GID of the project
        
    Returns:
        List of processed tasks
    """
    processed_tasks = []
    for task in tasks:
        task_data = {
            'project': project_name,
            'project_gid': project_gid,
            'name': safe_get(task, 'name'),
            'status': 'Completed' if safe_get(task, 'completed') else 'In Progress',
            'due_date': safe_get(task, 'due_on'),
            'created_at': safe_get(task, 'created_at'),
            'completed_at': safe_get(task, 'completed_at'),
            'assignee': safe_get(task, 'assignee', 'name') or 'Unassigned',
            'section': safe_get(task, 'memberships', 0, 'section', 'name') or 'No section',
            'tags': [tag['name'] for tag in safe_get(task, 'tags') or []],
            'num_subtasks': safe_get(task, 'num_subtasks') or 0,
        }

        # Process custom fields
        custom_fields = safe_get(task, 'custom_fields') or []
        for field in custom_fields:
            if field_name := safe_get(field, 'name'):
                task_data[f"custom_{field_name}"] = safe_get(field, 'display_value')

        processed_tasks.append(task_data)
    return processed_tasks

def get_project_owner(project_name: str, project_gid: str, _projects_api: asana.ProjectsApi) -> str:
    """
    Get the owner of a project.
    
    Args:
        project_name: Name of the project
        project_gid: GID of the project
        _projects_api: Asana Projects API instance
        
    Returns:
        Name of the project owner
    """
    try:
        opts = {
            'opt_fields': 'owner.name'
        }
        project_details = _projects_api.get_project(project_gid, opts=opts)
        return project_details['owner']['name'] if project_details.get('owner') else "Unassigned"
    except Exception as e:
        print(f"Error fetching project owner for {project_name}: {e}")
        return "Unknown"

def get_project_members_count(project_name: str, project_gid: str, _projects_api: asana.ProjectsApi) -> int:
    """
    Get the number of members in a project.
    
    Args:
        project_name: Name of the project
        project_gid: GID of the project
        _projects_api: Asana Projects API instance
        
    Returns:
        Number of members in the project
    """
    try:
        opts = {
            'opt_fields': 'members'
        }
        project_details = _projects_api.get_project(project_gid, opts=opts)
        return len(project_details.get('members', []))
    except Exception as e:
        print(f"Error fetching project members count for {project_name}: {e}")
        return 0

def get_project_gid(project_name: str, _portfolios_api: asana.PortfoliosApi, portfolio_gid: str) -> str:
    """
    Get the GID of a project by name.
    
    Args:
        project_name: Name of the project
        _portfolios_api: Asana Portfolios API instance
        portfolio_gid: Portfolio GID
        
    Returns:
        GID of the project
    """
    try:
        opts = {
            'opt_fields': 'name,gid',
        }
        portfolio_items = list(_portfolios_api.get_items_for_portfolio(portfolio_gid, opts=opts))
        for item in portfolio_items:
            if item['name'] == project_name:
                return item['gid']
        raise ValueError(f"Project '{project_name}' not found in the portfolio")
    except Exception as e:
        print(f"Error fetching project GID for {project_name}: {e}")
        return "Unknown" 