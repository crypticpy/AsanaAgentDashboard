"""Utility for safely loading API keys and secrets."""
import os
import json
import streamlit as st

def get_secret(key, default=None):
    """
    Get a secret from Streamlit secrets, environment variables, or config.json in that order.
    
    Args:
        key: The name of the secret/key to fetch
        default: Default value if key is not found
        
    Returns:
        The value of the secret or the default value
    """
    # First try to get from Streamlit secrets
    if key in st.secrets:
        return st.secrets[key]
    
    # Then try environment variables
    if key in os.environ:
        return os.environ[key]
    
    # Lastly, try the config.json file
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
            if key in config and config[key] != f"YOUR_{key}":
                return config[key]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    
    # Return default value if key not found
    return default

def get_asana_token():
    """Get the Asana API token."""
    return get_secret("ASANA_API_TOKEN")

def get_portfolio_gid():
    """Get the Asana portfolio GID."""
    return get_secret("PORTFOLIO_GID")

def get_team_gid():
    """Get the Asana team GID."""
    return get_secret("TEAM_GID")

def get_openai_key():
    """Get the OpenAI API key."""
    return get_secret("OPENAI_API_KEY") 