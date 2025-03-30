# Asana Portfolio Dashboard

## Overview

A Streamlit application designed to provide comprehensive insights into your Asana projects and tasks. It offers visualizations and metrics to help project managers and team leaders make data-driven decisions, with an AI-powered chat interface for natural language interaction with your project data.

## Features

- **Project Overview**: High-level view of all projects with completion estimates and status indicators
- **Task Analytics**: Analyze task distribution, completion rates, and overdue tasks
- **Resource Allocation**: Visualize resource allocation across projects
- **Interactive Charts**: Explore data with interactive charts and filters
- **Project Cards**: View detailed project information in a clean, modern UI
- **AI Assistant**: Ask questions about your projects using natural language (requires OpenAI API key)
- **Responsive Design**: Optimized for both desktop and mobile viewing

## Installation

### Prerequisites

- Python 3.10 or higher
- Asana Personal Access Token
- Portfolio GID and Team GID from Asana
- OpenAI API Key (for AI assistant features)

### Setup

1. Clone this repository:

   ```
   git clone https://github.com/crypticpy/AsanaAgentDash.git
   cd AsanaAgentDash
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Set up your API credentials (see "Setting up Secrets" section below)

2. Run the application:

   ```
   python run.py
   ```

   Or directly with Streamlit:

   ```
   streamlit run app.py
   ```

3. Open your web browser and navigate to the provided URL (typically http://localhost:8501)

4. Explore your Asana data and interact with the AI assistant!

## Project Structure

```
AsanaAgentDash/
├── app.py                     # Main Streamlit application file
├── run.py                     # Script to run the application
├── config.json                # Configuration file template for API credentials
├── requirements.txt           # Project dependencies
├── .gitignore                 # Git ignore file for excluding files from version control
├── .cursorindexingignore      # File for cursor IDE indexing configuration
├── pages/                     # Additional Streamlit pages
│   └── 1_💬_Advanced_Chat.py  # Advanced chat interface
├── src/                       # Source code
│   ├── __init__.py            # Package initialization
│   ├── components/            # UI components
│   │   ├── __init__.py        # Package initialization
│   │   ├── dashboard_metrics.py  # Dashboard metrics components
│   │   ├── fiscal_overview.py    # Fiscal overview component
│   │   ├── function_chat.py      # Function chat component
│   │   ├── project_card.py       # Project card component
│   │   └── sidebar.py            # Sidebar component
│   ├── pages/                 # Page-specific components
│   │   ├── __init__.py        # Package initialization
│   │   ├── resource_allocation_page.py  # Resource allocation page
│   │   └── resource_components/   # Resource page components
│   │       ├── __init__.py        # Package initialization
│   │       ├── performance_trends.py    # Performance trends
│   │       ├── project_allocation.py    # Project allocation
│   │       ├── resource_utilization.py  # Resource utilization
│   │       └── team_member_metrics.py   # Team member metrics
│   ├── styles/                # CSS and styling
│   │   ├── __init__.py        # Package initialization
│   │   └── custom.py          # Custom CSS styles
│   └── utils/                 # Utility functions
│       ├── __init__.py        # Package initialization
│       ├── asana_api.py       # Asana API utilities
│       ├── config.py          # Configuration utilities
│       ├── data_processing.py # Data processing utilities
│       ├── fiscal_visualizations.py  # Fiscal visualizations
│       ├── fiscal_year.py     # Fiscal year utilities
│       ├── chat/              # Chat assistant utilities
│       │   ├── __init__.py           # Package initialization
│       │   ├── api_wrapper.py        # API wrapper for chat
│       │   ├── assistant.py          # Assistant implementation
│       │   ├── data_context.py       # Data context for chat
│       │   ├── document_indexer.py   # Document indexing
│       │   ├── formatting.py         # Response formatting
│       │   ├── query_processor.py    # Query processing
│       │   ├── tool_functions.py     # Tool functions
│       │   └── visualization_handler.py  # Visualization handling
│       ├── function_calling/  # Function calling for AI assistant
│       │   ├── README.md      # Documentation for function calling
│       │   ├── __init__.py    # Package initialization
│       │   ├── assistant/     # Assistant implementation
│       │   │   ├── __init__.py        # Package initialization
│       │   │   ├── base.py            # Base assistant class
│       │   │   ├── conversation.py    # Conversation handling
│       │   │   ├── error_handling.py  # Error handling utilities
│       │   │   ├── streaming.py       # Streaming response handling
│       │   │   └── visualization.py   # Visualization handling
│       │   ├── backup/        # Backup implementations
│       │   │   ├── assistant.py       # Backup assistant implementation
│       │   │   └── tools.py           # Backup tools implementation
│       │   ├── schemas/       # Response schemas
│       │   │   ├── __init__.py        # Package initialization
│       │   │   ├── function_definitions.py    # Function definitions
│       │   │   ├── response_models.py         # Response models
│       │   │   └── visualization_schemas.py   # Visualization schemas
│       │   ├── tools/         # Tool implementations
│       │   │   ├── __init__.py        # Package initialization
│       │   │   ├── base.py            # Base tool class
│       │   │   ├── helpers.py         # Helper functions
│       │   │   ├── project_tools.py   # Project-related tools
│       │   │   ├── reporting_tools.py # Reporting tools
│       │   │   ├── task_tools.py      # Task-related tools
│       │   │   └── user_tools.py      # User-related tools
│       │   └── utils/         # Helper utilities
│       │       ├── __init__.py        # Package initialization
│       │       ├── api_helpers.py     # API helper functions
│       │       ├── formatting.py      # Response formatting utilities
│       │       ├── serialization.py   # Serialization utilities
│       │       └── validators.py      # Input validation utilities
│       ├── secrets.py         # Secret management utilities
│       └── visualizations.py  # Visualization utilities
├── tests/                     # Test files
│   └── test_refactored_assistant.py  # Tests for assistant
├── .streamlit/                # Streamlit configuration
│   └── secrets.toml           # Secrets file (not in git)
└── .cursor/                   # Cursor IDE configuration
    └── rules/                 # Cursor rules
        ├── tasks.mdc          # Tasks rules
        └── todos.mdc          # Todos rules
```

> Note: `venv/`, `project_docs/`, and `scripts/` directories are excluded from version control via `.gitignore`.

## Setting up Secrets

This application requires several API keys to function properly. For security reasons, these are not stored in the repository. You have three options for providing these secrets:

### Option 1: Streamlit Secrets (Recommended)

1. Create or edit the `.streamlit/secrets.toml` file (this file should never be committed to Git)
2. Add your API keys:

```toml
# Asana API settings
ASANA_API_TOKEN = "your-asana-api-token"
PORTFOLIO_GID = "your-portfolio-gid"
TEAM_GID = "your-team-gid"

# OpenAI API settings
OPENAI_API_KEY = "your-openai-api-key"
```

### Option 2: Environment Variables

Set the required environment variables before running the app:

```bash
export ASANA_API_TOKEN="your-asana-api-token"
export PORTFOLIO_GID="your-portfolio-gid"
export TEAM_GID="your-team-gid"
export OPENAI_API_KEY="your-openai-api-key"
```

### Option 3: Config File

Update the `config.json` file in the root directory with your actual API keys:

```json
{
  "ASANA_API_TOKEN": "your-asana-api-token",
  "PORTFOLIO_GID": "your-portfolio-gid",
  "TEAM_GID": "your-team-gid",
  "OPENAI_API_KEY": "your-openai-api-key"
}
```

**Note:** Option 3 is not recommended for production use as it may inadvertently lead to committing secrets to your repository.

## API Keys

### Asana API Token

Required for accessing your Asana data. You can get it from the [Asana Developer Console](https://app.asana.com/0/developer-console).

### Portfolio GID

Required for accessing your Asana portfolio. You can find it in the URL when viewing your portfolio in Asana.

### Team GID

Used for team-specific features. You can find it in the URL when viewing your team in Asana.

### OpenAI API Key

Required for AI assistant features. You can get it from [OpenAI API Keys](https://platform.openai.com/api-keys).

## Deploying to Streamlit Cloud

To deploy this application to Streamlit Cloud:

1. Push your code to GitHub (make sure your API keys are not included)
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Add your API keys as secrets in the Streamlit Cloud dashboard
5. Deploy your application

## Data Privacy

This application does not store any of your Asana data or API keys on external servers. All data is fetched in real-time using the provided API credentials and is only stored temporarily in memory during the session or locally in your config file.

## Contributing

Contributions to improve the dashboard are welcome. Please feel free to submit a Pull Request or open an Issue to discuss potential improvements.
