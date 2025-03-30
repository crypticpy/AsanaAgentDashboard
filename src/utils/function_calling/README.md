# Function Calling Module for Asana Chat Assistant

This module provides tools for the LLM to directly query the Asana API using
OpenAI's function calling capabilities.

## Overview

The function calling module has been completely refactored to improve maintainability and readability. The new structure follows a modular approach, with each file focused on a specific responsibility and kept under 300 lines of code.

## Directory Structure

```
src/utils/function_calling/
├── __init__.py                 # Main entry point and exports
├── assistant/                  # Assistant implementation
│   ├── __init__.py             # FunctionCallingAssistant class
│   ├── base.py                 # Base functionality
│   ├── conversation.py         # Conversation management
│   ├── streaming.py            # Streaming response handling
│   ├── visualization.py        # Visualization generation
│   └── error_handling.py       # Error handling and recovery
├── tools/                      # Asana API tools
│   ├── __init__.py             # AsanaToolSet class
│   ├── base.py                 # Base tool functionality
│   ├── project_tools.py        # Project-related tools
│   ├── task_tools.py           # Task-related tools
│   ├── user_tools.py           # User-related tools
│   ├── reporting_tools.py      # Reporting and analytics tools
│   └── helpers.py              # Helper utilities for visualizations
├── schemas/                    # Schema definitions
│   ├── __init__.py             # Schema exports
│   ├── function_definitions.py # Function specifications
│   ├── response_models.py      # Standardized response models
│   └── visualization_schemas.py # Visualization schemas
└── utils/                      # Utility functions
    ├── __init__.py             # Utility exports
    ├── api_helpers.py          # API interaction helpers
    ├── formatting.py           # Text and data formatting
    └── validators.py           # Input validation
```

## Main Classes

### FunctionCallingAssistant

The main class that combines all the specialized modules into a single interface for creating an AI assistant that can call functions in the Asana API.

### AsanaToolSet

Provides a set of tools for interacting with the Asana API through OpenAI's function calling capability.

## Features

- **Modular Design**: Each component has a single responsibility
- **Better Error Handling**: Comprehensive error handling and recovery
- **Standardized Responses**: Consistent response formats across all tools
- **Visualization Support**: Rich visualization capabilities
- **Streaming Responses**: Support for streaming responses with visualization signals

## Usage

```python
from src.utils.function_calling import FunctionCallingAssistant

# Create an instance with API instances
assistant = FunctionCallingAssistant(api_instances)

# Generate a response
response = assistant.generate_response("Show me all my projects")

# Generate a streaming response
for chunk in assistant.generate_streaming_response("Generate a report on task distribution"):
    print(chunk, end="", flush=True)

# Create visualizations
visualization = assistant.generate_visualization()
```

## Backup Directory

The `backup/` directory contains the original monolithic implementation files before the refactoring:

- `assistant.py`: The original FunctionCallingAssistant implementation (~2,800 lines)
- `tools.py`: The original AsanaToolSet implementation (~950 lines)

These files are kept for reference purposes only and should not be imported or used in new code. All functionality has been migrated to the modular structure described above.

## Validators

The `utils/validators.py` file includes validation functions to ensure the OpenAI API requirements are met:

- `validate_tool_definition()`: Validates a single tool definition against OpenAI's requirements
- `validate_tool_definitions()`: Validates a list of tool definitions and returns any errors found

## OpenAI API Compatibility

This module is compatible with the OpenAI API as of March 2023. Key compatibility notes:

1. All tools must include a `"type": "function"` field
2. Responses use the "tool" role format for function results
3. The code uses the "gpt-4o" model by default
