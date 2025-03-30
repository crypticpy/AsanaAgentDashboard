"""
Project-related tools for interacting with Asana projects.

This module provides tools for working with Asana projects, including
listing projects, getting project details, and finding projects by name or owner.
"""
from typing import Dict, Any, List, Optional

from src.utils.function_calling.tools.base import BaseAsanaTools
from src.utils.function_calling.utils import (
    handle_api_error, 
    safe_get, 
    dataclass_to_dict
)
from src.utils.function_calling.schemas import ProjectResponse, ProjectsListResponse


class ProjectTools(BaseAsanaTools):
    """Tools for working with Asana projects."""
    
    @handle_api_error
    def get_portfolio_projects(self, portfolio_gid: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all projects in a portfolio.
        
        Args:
            portfolio_gid: Portfolio GID (optional, will use the one from session state if not provided)
            
        Returns:
            Dictionary with list of projects and status
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Use provided portfolio_gid or default from session state
        if not portfolio_gid:
            portfolio_gid = self.portfolio_gid
        
        if not portfolio_gid or portfolio_gid == "your_portfolio_gid_here":
            return self.handle_missing_portfolio()
        
        # Update our cached value
        self.portfolio_gid = portfolio_gid
        
        self.logger.info(f"Fetching projects for portfolio GID: {portfolio_gid}")
        
        try:
            # Make API call
            opts = {
                'opt_fields': 'name,gid,created_at,completed,start_on,due_on,owner,owner.name,resource_type',
            }
            
            # Important debug information
            self.logger.debug(f"Portfolio API instance: {self.api_instances['_portfolios_api']}")
            
            # Get portfolio items
            projects = []
            try:
                items = list(self.api_instances["_portfolios_api"].get_items_for_portfolio(portfolio_gid, opts=opts))
                self.logger.debug(f"Raw portfolio items response, count={len(items)}: {items}")
                projects = items
            except Exception as e:
                self.logger.error(f"Error getting portfolio items: {str(e)}")
                return {
                    "status": "error",
                    "error": f"Failed to retrieve portfolio projects: {str(e)}",
                    "projects": [],
                    "project_count": 0
                }
            
            if not projects:
                self.logger.warning(f"No projects found in portfolio {portfolio_gid}")
                return {
                    "status": "success", 
                    "projects": [],
                    "project_count": 0,
                    "system_message": "No projects found in this portfolio."
                }
            
            # Format the results
            formatted_projects = []
            for item in projects:
                # Make sure this is a project (portfolios can contain other items too)
                resource_type = item.get("resource_type")
                self.logger.debug(f"Processing item with resource_type: {resource_type}, data: {item}")
                
                if resource_type != "project":
                    continue
                    
                formatted_projects.append({
                    "gid": item.get("gid", ""),
                    "name": item.get("name", ""),
                    "owner": safe_get(item, "owner"),
                    "created_at": item.get("created_at"),
                    "due_on": item.get("due_on"),
                    "start_on": item.get("start_on"),
                    "completed": item.get("completed", False)
                })
            
            # Create response using the schema
            response = ProjectsListResponse.from_api(formatted_projects)
            
            # Convert the response to a serializable dictionary
            self.logger.debug(f"Portfolio projects response object: {response}")
            serialized_response = dataclass_to_dict(response)
            self.logger.debug(f"Serialized portfolio projects response: {serialized_response}")
            
            return serialized_response
            
        except Exception as e:
            self.logger.error(f"Error in get_portfolio_projects: {str(e)}")
            return {
                "status": "error",
                "error": f"An error occurred: {str(e)}",
                "projects": [],
                "project_count": 0
            }
    
    @handle_api_error
    def get_project_details(self, project_gid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific project.
        
        Args:
            project_gid: The GID of the project
            
        Returns:
            Dictionary with project details
        """
        # Validate GID
        valid_gid = self.validate_gid_param(project_gid, "project_gid")
        if not valid_gid:
            return {
                "status": "error",
                "error": f"Invalid project GID: {project_gid}"
            }
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        self.logger.info(f"Getting details for project GID: {valid_gid}")
        
        # Make API call with expanded fields
        opts = {
            'opt_fields': 'name,gid,created_at,completed,start_on,due_on,owner,owner.name,'
                         'members,members.name,custom_fields,custom_fields.name,'
                         'custom_fields.type,custom_fields.enum_options,notes'
        }
        project = self.api_instances["_projects_api"].get_project(valid_gid, opts=opts)
        
        # Create response using the schema
        response = ProjectResponse.from_api(project)
        
        # Convert to serializable dictionary
        self.logger.debug(f"Project details response object: {response}")
        serialized_response = dataclass_to_dict(response)
        self.logger.debug(f"Serialized project details response: {serialized_response}")
        
        return serialized_response
    
    @handle_api_error
    def get_project_gid_by_name(self, project_name: str) -> Dict[str, Any]:
        """
        Find a project's GID by searching for its name.
        
        Args:
            project_name: Full or partial name of the project to search for
            
        Returns:
            Dictionary with search results
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not project_name:
            return {
                "status": "error",
                "error": "Project name is required"
            }
        
        if not self.portfolio_gid or self.portfolio_gid == "your_portfolio_gid_here":
            return self.handle_missing_portfolio()
        
        self.logger.info(f"Searching for project by name: {project_name}")
        
        # First, get all projects in the portfolio
        portfolio_projects = self.get_portfolio_projects()
        
        if portfolio_projects.get("status") != "success":
            return portfolio_projects
        
        # Search for matching projects
        matching_projects = []
        for project in portfolio_projects.get("projects", []):
            if project_name.lower() in project.get("name", "").lower():
                matching_projects.append({
                    "gid": project.get("gid", ""),
                    "name": project.get("name", "")
                })
        
        # Format the response
        if matching_projects:
            best_match = matching_projects[0]  # Assume first match is best
            return {
                "status": "success",
                "project_gid": best_match.get("gid", ""),
                "project_name": best_match.get("name", ""),
                "all_matches": matching_projects,
                "match_count": len(matching_projects)
            }
        else:
            return {
                "status": "error",
                "error": f"No projects found matching name: {project_name}",
                "all_matches": [],
                "match_count": 0
            }
    
    @handle_api_error
    def get_project_info_by_name(self, project_name: str) -> Dict[str, Any]:
        """
        Get project details by searching for a project name.
        
        Args:
            project_name: Full or partial name of the project to search for
            
        Returns:
            Dictionary with project details
        """
        # First, get the project GID by name
        result = self.get_project_gid_by_name(project_name)
        
        if result.get("status") != "success":
            return result
        
        # Now get the project details
        project_gid = result.get("project_gid", "")
        return self.get_project_details(project_gid)
    
    @handle_api_error
    def get_projects_by_owner(self, owner_name: str) -> Dict[str, Any]:
        """
        Get projects owned by a specific user.
        
        Args:
            owner_name: Name of the project owner to search for
            
        Returns:
            Dictionary with list of projects
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        if not owner_name:
            return {
                "status": "error",
                "error": "Owner name is required"
            }
        
        if not self.portfolio_gid or self.portfolio_gid == "your_portfolio_gid_here":
            return self.handle_missing_portfolio()
        
        self.logger.info(f"Searching for projects by owner: {owner_name}")
        
        # First, get all projects in the portfolio
        portfolio_projects = self.get_portfolio_projects()
        
        if portfolio_projects.get("status") != "success":
            return portfolio_projects
        
        # Filter projects by owner name
        matching_projects = []
        for project in portfolio_projects.get("projects", []):
            owner = project.get("owner", {})
            if owner and owner_name.lower() in owner.get("name", "").lower():
                matching_projects.append(project)
        
        # Add debug logging
        self.logger.debug(f"Found {len(matching_projects)} projects for owner {owner_name}")
        
        # Format the response
        return {
            "status": "success",
            "projects": matching_projects,
            "project_count": len(matching_projects),
            "owner_name": owner_name
        }
