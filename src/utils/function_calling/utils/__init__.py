"""
Utility functions for the function calling module.

This package contains utility functions for working with the Asana API,
formatting responses, and validating input data.
"""

from src.utils.function_calling.utils.api_helpers import (
    rate_limit,
    handle_api_error,
    safe_get,
    format_date,
    calculate_date_range,
    parse_gid,
    get_portfolio_gid,
    get_team_gid,
    create_dataframe_from_tasks
)

from src.utils.function_calling.utils.formatting import (
    format_json_for_display,
    truncate_text,
    format_message_for_display,
    format_table_for_display,
    format_time_ago,
    extract_code_blocks,
    format_dataframe_as_markdown,
    clean_html_tags,
    format_duration
)

from src.utils.function_calling.utils.validators import (
    validate_gid,
    validate_date_string,
    validate_int_range,
    validate_non_empty_string,
    validate_function_args,
    validate_chart_data,
    validate_boolean
)

from src.utils.function_calling.utils.serialization import (
    dataclass_to_dict,
    DataclassJSONEncoder,
    to_serializable,
    serialize_response,
    json_dumps
)

__all__ = [
    # API helpers
    "rate_limit",
    "handle_api_error",
    "safe_get",
    "format_date",
    "calculate_date_range",
    "parse_gid",
    "get_portfolio_gid",
    "get_team_gid",
    "create_dataframe_from_tasks",
    
    # Formatting
    "format_json_for_display",
    "truncate_text",
    "format_message_for_display",
    "format_table_for_display",
    "format_time_ago",
    "extract_code_blocks",
    "format_dataframe_as_markdown",
    "clean_html_tags",
    "format_duration",
    
    # Validators
    "validate_gid",
    "validate_date_string",
    "validate_int_range",
    "validate_non_empty_string",
    "validate_function_args",
    "validate_chart_data",
    "validate_boolean",
    
    # Serialization
    "dataclass_to_dict",
    "DataclassJSONEncoder",
    "to_serializable",
    "serialize_response",
    "json_dumps"
]
