"""
Visualization schema definitions for standardizing chart creation.

This module defines standard schemas for various chart types that can be created
by the assistant, ensuring consistent visualization interfaces.
"""
from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, ConfigDict, validator, ValidationError
from dataclasses import dataclass # Keep for ChartConfig if it remains a dataclass

# Define ChartType Literal
ChartType = Literal["bar", "line", "pie", "scatter", "area", "timeline", "heatmap"]

# --- Pydantic Model Configuration ---
# Configuration to ignore extra fields during initialization
ignore_extra_config = ConfigDict(extra='ignore')

# --- Base Chart Configuration (Can remain dataclass or become BaseModel) ---
@dataclass
class ChartConfig:
    """Base configuration for all chart types."""
    title: str = "Chart"
    subtitle: Optional[str] = None
    x_axis_title: Optional[str] = None
    y_axis_title: Optional[str] = None
    height: int = 400
    width: Optional[int] = None
    show_legend: bool = True
    color_scheme: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for Plotly."""
        # Use dataclasses.asdict if sticking with dataclass
        # import dataclasses
        # return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}
        # Or manual dict creation if needed
        return {k: v for k, v in self.__dict__.items() if v is not None}


# --- Chart Data Models (Converted to Pydantic BaseModel) ---

class BarChartData(BaseModel):
    """Data model for bar charts."""
    model_config = ignore_extra_config # Apply config

    x_values: List[str]
    y_values: List[Union[int, float]]
    group_by: Optional[List[str]] = None
    orientation: str = "vertical"  # "vertical" or "horizontal"

    @validator('orientation')
    def orientation_must_be_valid(cls, v):
        if v not in ['vertical', 'horizontal']:
            raise ValueError('orientation must be "vertical" or "horizontal"')
        return v

    @validator('y_values')
    def check_lengths_match_x(cls, y_values, values):
        # Corrected: Access dict directly in @validator compatibility mode
        x_values = values.get('x_values')
        if x_values and len(x_values) != len(y_values):
            raise ValueError('x_values and y_values must have the same length')
        return y_values

    @validator('group_by')
    def check_group_by_length(cls, group_by, values):
        # Corrected: Access dict directly in @validator compatibility mode
        x_values = values.get('x_values')
        if group_by and x_values and len(group_by) != len(x_values):
            raise ValueError('group_by must have the same length as x_values')
        return group_by


class LineChartData(BaseModel):
    """Data model for line charts."""
    model_config = ignore_extra_config

    x_values: List[Union[str, int, float]]
    y_values: List[Union[int, float]] # Changed: Expect a single list for y_values
    # series_names: Optional[List[str]] = None # Removed: Not applicable for single line chart schema
    show_markers: bool = True
    line_shape: str = "linear"  # "linear", "spline", "step", etc.

    @validator('line_shape')
    def shape_must_be_valid(cls, v):
        # Add more valid shapes as needed by Plotly
        if v not in ['linear', 'spline', 'step']:
            raise ValueError('line_shape must be "linear", "spline", or "step"')
        return v

    @validator('y_values')
    def check_lengths_match_x_line(cls, y_values, values): # Renamed validator for clarity
        # Corrected: Access dict directly in @validator compatibility mode
        x_values = values.get('x_values')
        if x_values and len(x_values) != len(y_values): # Changed: Compare length of single y_values list
             raise ValueError('x_values and y_values must have the same length')
        return y_values

    # @validator('series_names') # Removed validator
    # def check_series_names_length(cls, series_names, values):
    #     # Corrected: Access dict directly in @validator compatibility mode
    #     y_values = values.get('y_values')
    #     if series_names and y_values and len(series_names) != len(y_values):
    #         raise ValueError('series_names must have the same length as the number of series in y_values')
    #     return series_names


class PieChartData(BaseModel):
    """Data model for pie charts."""
    model_config = ignore_extra_config

    labels: List[str]
    values: List[Union[int, float]]
    hole: float = 0.0  # 0.0 for pie, >0 for donut

    @validator('values')
    def check_lengths_match_labels(cls, values_list, values):
        # Corrected: Access dict directly in @validator compatibility mode
        labels = values.get('labels')
        if labels and len(labels) != len(values_list):
            raise ValueError('labels and values must have the same length')
        if any(v < 0 for v in values_list):
             raise ValueError('values cannot be negative')
        return values_list

    @validator('hole')
    def hole_must_be_valid(cls, v):
        if not (0.0 <= v < 1.0):
            raise ValueError('hole must be between 0.0 and 1.0 (exclusive of 1.0)')
        return v


class ScatterChartData(BaseModel):
    """Data model for scatter plots."""
    model_config = ignore_extra_config

    x_values: List[Union[int, float]]
    y_values: List[Union[int, float]]
    text_labels: Optional[List[str]] = None
    sizes: Optional[List[Union[int, float]]] = None
    colors: Optional[List[Union[int, float, str]]] = None
    color_scale: Optional[str] = None # Example: 'Viridis', 'Blues', etc.

    @validator('y_values')
    def check_lengths_match_x_scatter(cls, y_values, values):
        # Corrected: Access dict directly in @validator compatibility mode
        x_values = values.get('x_values')
        if x_values and len(x_values) != len(y_values):
            raise ValueError('x_values and y_values must have the same length')
        return y_values

    # Add similar validators for text_labels, sizes, colors if needed


class TimelineChartData(BaseModel):
    """Data model for timeline charts."""
    model_config = ignore_extra_config

    tasks: List[str]
    start_dates: List[str] # Expecting 'YYYY-MM-DD' format
    end_dates: List[str]   # Expecting 'YYYY-MM-DD' format
    colors: Optional[List[str]] = None
    group: Optional[List[str]] = None

    @validator('start_dates', 'end_dates')
    def check_date_format(cls, dates):
        # Basic format check, more robust parsing might be needed
        for date_str in dates:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Date '{date_str}' is not in YYYY-MM-DD format")
        return dates

    @validator('end_dates')
    def check_lengths_match_tasks_timeline(cls, end_dates, values):
        # Corrected: Access dict directly in @validator compatibility mode
        tasks = values.get('tasks')
        start_dates = values.get('start_dates')
        if tasks and start_dates and not (len(tasks) == len(start_dates) == len(end_dates)):
            raise ValueError('tasks, start_dates, and end_dates must have the same length')
        # Could add validation that end_date >= start_date
        return end_dates

    # Add validators for colors and group lengths if needed


class HeatmapChartData(BaseModel):
    """Data model for heatmap charts."""
    model_config = ignore_extra_config

    x_values: List[str]
    y_values: List[str]
    z_values: List[List[Union[int, float]]]
    color_scale: Optional[str] = None # Example: 'Viridis', 'Blues', etc.

    @validator('z_values')
    def check_z_values_dimensions(cls, z_values, values):
        # Corrected: Access dict directly in @validator compatibility mode
        x_values = values.get('x_values')
        y_values = values.get('y_values')
        if y_values and len(y_values) != len(z_values):
            raise ValueError('Length of y_values must match the number of rows in z_values')
        if x_values:
            for row in z_values:
                if len(row) != len(x_values):
                    raise ValueError('Length of each row in z_values must match the length of x_values')
        return z_values


# --- Deprecated get_chart_schema function (kept for reference, but not used by create_direct_chart) ---
def get_chart_schema(chart_type: ChartType) -> Dict[str, Any]:
    """
    DEPRECATED: Get the JSON schema for a specific chart type.
    This is kept for reference but the dynamic schema builder is used now.

    Args:
        chart_type: Type of chart

    Returns:
        JSON schema dictionary for the chart type
    """
    # ... (implementation remains the same as before, but is effectively unused
    #      by the create_direct_chart tool which builds its schema dynamically)
    base_schema = {
        "type": "object",
        "properties": {
            "config": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "x_axis_title": {"type": "string"},
                    "y_axis_title": {"type": "string"},
                    "height": {"type": "integer"},
                    "width": {"type": "integer"},
                    "show_legend": {"type": "boolean"},
                    "color_scheme": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }

    chart_specific_schemas = {
        "bar": {
            "properties": {
                "x_values": {"type": "array", "items": {"type": "string"}},
                "y_values": {"type": "array", "items": {"type": "number"}},
                "group_by": {"type": "array", "items": {"type": "string"}},
                "orientation": {"type": "string", "enum": ["vertical", "horizontal"]}
            },
            "required": ["x_values", "y_values"]
        },
        "line": {
            "properties": {
                "x_values": {"type": "array"},
                "y_values": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                "series_names": {"type": "array", "items": {"type": "string"}},
                "show_markers": {"type": "boolean"},
                "line_shape": {"type": "string"}
            },
            "required": ["x_values", "y_values"]
        },
        "pie": {
            "properties": {
                "labels": {"type": "array", "items": {"type": "string"}},
                "values": {"type": "array", "items": {"type": "number"}},
                "hole": {"type": "number"}
            },
            "required": ["labels", "values"]
        },
        "scatter": {
            "properties": {
                "x_values": {"type": "array", "items": {"type": "number"}},
                "y_values": {"type": "array", "items": {"type": "number"}},
                "text_labels": {"type": "array", "items": {"type": "string"}},
                "sizes": {"type": "array", "items": {"type": "number"}},
                "colors": {"type": "array"},
                "color_scale": {"type": "string"}
            },
            "required": ["x_values", "y_values"]
        },
        "area": {
            "properties": {
                "x_values": {"type": "array"},
                "y_values": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                "series_names": {"type": "array", "items": {"type": "string"}},
                "stack": {"type": "boolean"} # Example specific property for area
            },
            "required": ["x_values", "y_values"]
        },
        "timeline": {
            "properties": {
                "tasks": {"type": "array", "items": {"type": "string"}},
                "start_dates": {"type": "array", "items": {"type": "string"}},
                "end_dates": {"type": "array", "items": {"type": "string"}},
                "colors": {"type": "array", "items": {"type": "string"}},
                "group": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["tasks", "start_dates", "end_dates"]
        },
        "heatmap": {
            "properties": {
                "x_values": {"type": "array", "items": {"type": "string"}},
                "y_values": {"type": "array", "items": {"type": "string"}},
                "z_values": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                "color_scale": {"type": "string"}
            },
            "required": ["x_values", "y_values", "z_values"]
        }
    }

    if chart_type in chart_specific_schemas:
        schema_properties = chart_specific_schemas[chart_type]
        # Ensure 'data' key exists before updating properties
        if 'properties' not in base_schema:
             base_schema['properties'] = {}
        if 'data' not in base_schema['properties']:
             base_schema['properties']['data'] = {'type': 'object', 'properties': {}}

        base_schema["properties"]['data']['properties'].update(schema_properties["properties"])
        # Update required fields within the 'data' object
        base_schema["properties"]['data']["required"] = schema_properties.get("required", [])

    return base_schema
