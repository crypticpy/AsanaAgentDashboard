"""
Schema definitions for function calling.

This package contains schema definitions for function specifications,
response models, and visualization schemas.
"""

from src.utils.function_calling.schemas.function_definitions import (
    get_function_definitions,
    get_function_definition_by_name,
    PROJECT_FUNCTIONS,
    TASK_FUNCTIONS,
    USER_FUNCTIONS,
    REPORTING_FUNCTIONS,
    ALL_FUNCTION_DEFINITIONS
)

from src.utils.function_calling.schemas.response_models import (
    BaseResponse,
    ProjectResponse,
    ProjectsListResponse,
    TaskResponse,
    TasksListResponse,
    UserResponse,
    UsersListResponse,
    TaskDistributionResponse,
    TaskCompletionTrendResponse,
    SearchResponse,
    VisualizationResponse,
    format_error_response
)

from src.utils.function_calling.schemas.visualization_schemas import (
    ChartType,
    ChartConfig,
    BarChartData,
    LineChartData,
    PieChartData,
    ScatterChartData,
    TimelineChartData,
    HeatmapChartData,
    get_chart_schema
)

__all__ = [
    # Function definitions
    "get_function_definitions",
    "get_function_definition_by_name",
    "PROJECT_FUNCTIONS",
    "TASK_FUNCTIONS",
    "USER_FUNCTIONS",
    "REPORTING_FUNCTIONS",
    "ALL_FUNCTION_DEFINITIONS",
    
    # Response models
    "BaseResponse",
    "ProjectResponse",
    "ProjectsListResponse",
    "TaskResponse",
    "TasksListResponse",
    "UserResponse",
    "UsersListResponse",
    "TaskDistributionResponse",
    "TaskCompletionTrendResponse",
    "SearchResponse",
    "VisualizationResponse",
    "format_error_response",
    
    # Visualization schemas
    "ChartType",
    "ChartConfig",
    "BarChartData",
    "LineChartData",
    "PieChartData",
    "ScatterChartData",
    "TimelineChartData",
    "HeatmapChartData",
    "get_chart_schema"
]
