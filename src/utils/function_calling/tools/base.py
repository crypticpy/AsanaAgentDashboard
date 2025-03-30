"""
Base class for Asana API tools.

This module defines the base class for all Asana API tools with common
utilities and helper methods.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Union

import streamlit as st
import asana

from src.utils.function_calling.utils import (
    rate_limit, 
    handle_api_error, 
    safe_get, 
    parse_gid,
    get_portfolio_gid,
    get_team_gid
)
from src.utils.function_calling.schemas import format_error_response


class BaseAsanaTools:
    """
    Base class for all Asana API tools with common utilities.
    """
    
    def __init__(self, api_instances: Dict[str, Any]):
        """
        Initialize the base tools.
        
        Args:
            api_instances: Dictionary with API instances
        """
        # Configure logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Store API instances
        self.api_instances = api_instances
        
        # Get portfolio GID from session state if available
        from streamlit import session_state
        
        # Get the portfolio GID from session state
        self.portfolio_gid = session_state.get("portfolio_gid", "")
        self.logger.info(f"Initialized with portfolio_gid: {self.portfolio_gid}")
        
        # Initialize rate limiter
        self.last_api_call = 0
        self.min_call_interval = 0.2  # seconds
        
        # Get team_gid from session state if available
        self.team_gid = session_state.get("team_gid", "")
        self.logger.info(f"Initialized with team_gid: {self.team_gid}")
        
        # Cache for user GIDs to avoid repeated lookups
        self._user_gid_cache = {}
        # Placeholder for assistant memory reference
        self.assistant_memory: Optional[Dict[str, Any]] = None

    def set_assistant_memory(self, memory: Dict[str, Any]):
        """
        Sets a reference to the assistant's memory dictionary.
        This allows tools to store temporary data (like chart JSON)
        that needs to be accessed by the UI component later.

        Args:
            memory: The memory dictionary from the BaseFunctionCallingAssistant.
        """
        self.assistant_memory = memory
        self.logger.debug("Assistant memory reference set for tools.")

    def _apply_rate_limit(self):
        """Apply rate limiting to API calls."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_api_call = time.time()

    @handle_api_error
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
                self.logger.warning(f"Error getting users for team: {e}")
        
        # No match found
        return None
    
    @handle_api_error
    def check_connection(self) -> Dict[str, Any]:
        """
        Check connection to Asana API.
        
        Returns:
            Status dictionary
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Try to get current user info as a simple API test
            user = self.api_instances["_users_api"].get_user("me", {"opt_fields": "name,email"})
            
            return {
                "status": "success",
                "connected": True,
                "user": {
                    "name": user.get("name", "Unknown"),
                    "email": user.get("email", "Unknown")
                },
                "portfolio_gid": self.portfolio_gid,
                "team_gid": self.team_gid
            }
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "status": "error",
                "connected": False,
                "error": str(e)
            }
    
    def handle_missing_portfolio(self) -> Dict[str, Any]:
        """
        Handle missing portfolio GID.
        
        Returns:
            Error response dictionary
        """
        self.logger.error("Missing portfolio GID")
        # Check if we're in portfolio setup mode
        from streamlit import session_state
        
        if session_state.get("portfolio_setup_mode", False):
            return {
                "status": "error",
                "error": "No portfolio has been set up yet. Please complete the portfolio setup first.",
                "system_message": "Portfolio setup required"
            }
        else:
            return {
                "status": "error",
                "error": "No portfolio GID has been configured. Please select a portfolio in the sidebar.",
                "system_message": "Portfolio selection required"
            }
    
    def validate_gid_param(self, gid: Optional[str], param_name: str) -> Optional[str]:
        """
        Validate a GID parameter and return a standardized error if invalid.
        
        Args:
            gid: GID to validate
            param_name: Name of the parameter (for error messages)
            
        Returns:
            Validated GID or None if invalid
        """
        valid_gid = parse_gid(gid)
        
        if not valid_gid:
            self.logger.warning(f"Invalid {param_name}: {gid}")
            return None
        
        return valid_gid
