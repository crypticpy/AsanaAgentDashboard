"""
Configuration utilities for the Asana Portfolio Dashboard.
"""
import json
import os
from typing import Dict, Any, Optional
import streamlit as st
from pydantic import BaseModel

class Config(BaseModel):
    """
    Configuration model for the Asana Portfolio Dashboard.
    """
    ASANA_API_TOKEN: str
    PORTFOLIO_GID: str
    TEAM_GID: str

def load_config() -> Optional[Dict[str, Any]]:
    """
    Load configuration from the config file.
    
    Returns:
        Configuration dictionary or None if not found
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None

def save_config(config: Dict[str, Any]) -> None:
    """
    Save configuration to the config file.
    
    Args:
        config: Configuration dictionary
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

def get_manager() -> Dict[str, Any]:
    """
    Get the configuration manager.
    
    Returns:
        Configuration manager dictionary
    """
    if "config" not in st.session_state:
        st.session_state.config = load_config() or {}
    
    return st.session_state.config 