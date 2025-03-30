"""
Test script for the refactored FunctionCallingAssistant.

This script tests the compatibility of the refactored FunctionCallingAssistant
with the existing codebase.
"""
import os
import sys
import json
import streamlit as st
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Import the old and new implementations
from src.utils.function_calling.backup.assistant import FunctionCallingAssistant as OldAssistant
from src.utils.function_calling.main import FunctionCallingAssistant as NewAssistant

# Mock API instances for testing
mock_api_instances = {
    "_client": None,
    "_portfolios_api": None,
    "_projects_api": None,
    "_tasks_api": None,
    "_teams_api": None,
    "_users_api": None,
    "_workspaces_api": None,
    "workspace_gid": "1234567890"
}

def test_compatibility():
    """Test the compatibility of the old and new assistant implementations."""
    
    print("Testing compatibility of old and new FunctionCallingAssistant implementations...")
    
    # Mock session state
    st.session_state = {
        "portfolio_gid": "1234567890",
        "team_gid": "0987654321",
        "openai_api_key": os.environ.get("OPENAI_API_KEY", "")
    }
    
    # Initialize both assistants
    old_assistant = OldAssistant(mock_api_instances)
    new_assistant = NewAssistant(mock_api_instances)
    
    # Test API method compatibility
    verify_method_existence(old_assistant, new_assistant)
    
    print("Compatibility test complete!")

def verify_method_existence(old_instance, new_instance):
    """Verify that all methods in the old instance exist in the new instance."""
    
    # Get all public methods from the old instance
    old_methods = [method for method in dir(old_instance) 
                  if not method.startswith('_') and callable(getattr(old_instance, method))]
    
    # Get all public methods from the new instance
    new_methods = [method for method in dir(new_instance)
                  if not method.startswith('_') and callable(getattr(new_instance, method))]
    
    # Print all methods for comparison
    print("\nOld implementation methods:")
    for method in sorted(old_methods):
        print(f"  - {method}")
    
    print("\nNew implementation methods:")
    for method in sorted(new_methods):
        print(f"  - {method}")
    
    # Check for missing methods
    missing_methods = [method for method in old_methods if method not in new_methods]
    
    if missing_methods:
        print("\nWARNING: The following methods are missing in the new implementation:")
        for method in missing_methods:
            print(f"  - {method}")
    else:
        print("\nAll methods from the old implementation are present in the new implementation.")
    
    # Check property compatibility
    verify_property_existence(old_instance, new_instance)

def verify_property_existence(old_instance, new_instance):
    """Verify that all properties in the old instance exist in the new instance."""
    
    # List of common properties to check
    properties_to_check = ["conversation_history", "memory"]
    
    print("\nChecking properties:")
    for prop in properties_to_check:
        old_has_prop = hasattr(old_instance, prop)
        new_has_prop = hasattr(new_instance, prop)
        
        print(f"  - {prop}: {'✓' if new_has_prop else '✗'} (Old: {'✓' if old_has_prop else '✗'})")

if __name__ == "__main__":
    test_compatibility() 