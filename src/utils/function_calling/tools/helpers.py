"""
Helper functions for working with Asana data, visualizations, and chart creation.

This module provides utility functions that support the tool classes by providing
specialized functionalities for data transformation and chart creation.
"""
from typing import Dict, Any, List, Optional, Union
import logging
import json

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from src.utils.function_calling.schemas import ChartType
from src.utils.function_calling.utils import safe_get


logger = logging.getLogger("asana_tools_helpers")


def create_bar_chart(**kwargs: Any) -> go.Figure:
    """
    Create a bar chart using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: x_values, y_values, title, x_axis_title,
                            y_axis_title, orientation, color_scheme,
                            height, width, show_legend.

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    x_values = kwargs.get("x_values", [])
    y_values = kwargs.get("y_values", [])
    title = kwargs.get("title", "Bar Chart")
    x_axis_title = kwargs.get("x_axis_title", "")
    y_axis_title = kwargs.get("y_axis_title", "")
    orientation = kwargs.get("orientation", "vertical")
    color_scheme = kwargs.get("color_scheme") # Note: Plotly bar uses one color or a list matching bars
    height = kwargs.get("height", 400)
    width = kwargs.get("width")
    show_legend = kwargs.get("show_legend", True) # Bar charts usually don't need legends unless grouped

    # Ensure we have data
    if not x_values or not y_values or len(x_values) != len(y_values):
        logger.warning("Invalid or mismatched data for bar chart (x_values, y_values)")
        # Return an empty figure with a title indicating the issue
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig

    # Create the figure
    try:
        if orientation == "horizontal":
            fig = go.Figure(go.Bar(
                y=x_values,
                x=y_values,
                orientation='h',
                marker_color=color_scheme[0] if color_scheme else None # Simple color assignment
            ))
            # Swap axis titles for horizontal
            effective_x_title = y_axis_title
            effective_y_title = x_axis_title
        else:
            fig = go.Figure(go.Bar(
                x=x_values,
                y=y_values,
                marker_color=color_scheme[0] if color_scheme else None # Simple color assignment
            ))
            effective_x_title = x_axis_title
            effective_y_title = y_axis_title

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=effective_x_title,
            yaxis_title=effective_y_title,
            height=height,
            width=width,
            showlegend=show_legend
        )
    except Exception as e:
        logger.error(f"Error creating bar chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


def create_line_chart(**kwargs: Any) -> go.Figure:
    """
    Create a line chart using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: x_values, y_values (list of lists), series_names,
                            title, x_axis_title, y_axis_title, show_markers,
                            line_shape, color_scheme, height, width, show_legend,
                            fill (optional, e.g., 'tozeroy' for area chart).

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    x_values = kwargs.get("x_values", [])
    y_values_list = kwargs.get("y_values", []) # Expect list of lists
    series_names = kwargs.get("series_names", [])
    title = kwargs.get("title", "Line Chart")
    x_axis_title = kwargs.get("x_axis_title", "")
    y_axis_title = kwargs.get("y_axis_title", "")
    show_markers = kwargs.get("show_markers", True)
    line_shape = kwargs.get("line_shape", "linear")
    color_scheme = kwargs.get("color_scheme")
    height = kwargs.get("height", 400)
    width = kwargs.get("width")
    show_legend = kwargs.get("show_legend", True)
    fill = kwargs.get("fill") # For area charts

    # Basic data validation
    if not x_values or not y_values_list or not isinstance(y_values_list, list):
        logger.warning("Invalid data for line chart (x_values or y_values missing/invalid)")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig

    # --- Modification Start: Handle single list y_values ---
    # Check if y_values_list is a list of numbers (single series) instead of list of lists
    if y_values_list and all(isinstance(val, (int, float)) for val in y_values_list):
        logger.debug("Detected single series format for y_values. Wrapping in a list.")
        y_values_list = [y_values_list] # Wrap the single list into a list of lists
    # --- Modification End ---

    # Now perform checks assuming y_values_list is a list of lists
    elif not all(isinstance(y, list) for y in y_values_list): # Check if it's not list of lists (after potential wrapping)
         logger.warning("Invalid data format for line chart y_values (expected list of lists or single list)")
         fig = go.Figure()
         fig.update_layout(title=f"{title} - Error: Invalid Y-Values Format")
         return fig

    if not all(len(x_values) == len(y) for y in y_values_list):
         logger.warning("Mismatched lengths between x_values and y_values series")
         fig = go.Figure()
         fig.update_layout(title=f"{title} - Error: Mismatched Data Lengths")
         return fig
    if series_names and len(series_names) != len(y_values_list):
         logger.warning("Length of series_names does not match number of y_values series")
         # Proceed without names or adjust logic? For now, proceed.
         series_names = [f"Series {i+1}" for i in range(len(y_values_list))]


    # Create the figure
    fig = go.Figure()

    try:
        # Add traces for each series
        for i, y_values in enumerate(y_values_list):
            name = series_names[i] if series_names and i < len(series_names) else f"Series {i+1}"
            color = color_scheme[i % len(color_scheme)] if color_scheme else None

            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers' if show_markers else 'lines',
                name=name,
                line=dict(shape=line_shape, color=color),
                fill=fill if fill else None # Apply fill if provided
            ))

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_axis_title,
            yaxis_title=y_axis_title,
            height=height,
            width=width,
            showlegend=show_legend
        )
    except Exception as e:
        logger.error(f"Error creating line chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


def create_pie_chart(**kwargs: Any) -> go.Figure:
    """
    Create a pie chart using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: labels, values, title, hole, color_scheme,
                            height, width, show_legend.

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    labels = kwargs.get("labels", [])
    values = kwargs.get("values", [])
    title = kwargs.get("title", "Pie Chart")
    hole = kwargs.get("hole", 0.0)
    color_scheme = kwargs.get("color_scheme")
    height = kwargs.get("height", 400)
    width = kwargs.get("width")
    show_legend = kwargs.get("show_legend", True)

    # Ensure we have data
    if not labels or not values or len(labels) != len(values):
        logger.warning("Invalid or mismatched data for pie chart (labels, values)")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig

    # Create the figure
    try:
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=hole,
            marker_colors=color_scheme
        ))

        # Update layout
        fig.update_layout(
            title=title,
            height=height,
            width=width,
            showlegend=show_legend
        )
    except Exception as e:
        logger.error(f"Error creating pie chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


def create_scatter_chart(**kwargs: Any) -> go.Figure:
    """
    Create a scatter chart using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: x_values, y_values, text_labels, sizes, colors,
                            color_scale, title, x_axis_title, y_axis_title,
                            height, width, show_legend.

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    x_values = kwargs.get("x_values", [])
    y_values = kwargs.get("y_values", [])
    text_labels = kwargs.get("text_labels", [])
    sizes = kwargs.get("sizes", [])
    colors = kwargs.get("colors", [])
    color_scale = kwargs.get("color_scale")
    title = kwargs.get("title", "Scatter Plot")
    x_axis_title = kwargs.get("x_axis_title", "")
    y_axis_title = kwargs.get("y_axis_title", "")
    height = kwargs.get("height", 400)
    width = kwargs.get("width")
    show_legend = kwargs.get("show_legend", False) # Scatter usually doesn't need legend

    # Ensure we have data
    if not x_values or not y_values or len(x_values) != len(y_values):
        logger.warning("Invalid or mismatched data for scatter chart (x_values, y_values)")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig

    # Create the figure
    fig = go.Figure()

    try:
        # Set up marker properties
        marker = {}
        if sizes and len(sizes) == len(x_values):
            marker["size"] = sizes
        if colors:
            marker["color"] = colors
            if color_scale:
                marker["colorscale"] = color_scale
                marker["showscale"] = True # Show color scale bar

        # Set up text for hover
        text = text_labels if text_labels and len(text_labels) == len(x_values) else None

        # Add trace
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers',
            marker=marker,
            text=text
        ))

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_axis_title,
            yaxis_title=y_axis_title,
            height=height,
            width=width,
            showlegend=show_legend
        )
    except Exception as e:
        logger.error(f"Error creating scatter chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


def create_timeline_chart(**kwargs: Any) -> go.Figure:
    """
    Create a timeline chart (Gantt) using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: tasks, start_dates, end_dates, colors, group,
                            title, height, width, show_legend.

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    tasks = kwargs.get("tasks", [])
    start_dates = kwargs.get("start_dates", [])
    end_dates = kwargs.get("end_dates", [])
    colors = kwargs.get("colors", []) # Optional: color per task/group
    groups = kwargs.get("group", []) # Optional: group tasks (e.g., by project)
    title = kwargs.get("title", "Timeline")
    height = kwargs.get("height", 400)
    width = kwargs.get("width")
    show_legend = kwargs.get("show_legend", True)

    # Ensure we have data
    if not tasks or not start_dates or not end_dates:
        logger.warning("Invalid data for timeline chart (missing tasks, start_dates, or end_dates)")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig

    if not (len(tasks) == len(start_dates) == len(end_dates)):
        logger.warning("Mismatched data lengths for timeline chart")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Mismatched Data Lengths")
        return fig
    if colors and len(colors) != len(tasks):
         logger.warning("Timeline chart colors length mismatch, ignoring colors.")
         colors = None
    if groups and len(groups) != len(tasks):
         logger.warning("Timeline chart groups length mismatch, ignoring groups.")
         groups = None

    # Create DataFrame for Plotly Express timeline
    df_data = {'Task': tasks, 'Start': start_dates, 'Finish': end_dates}
    if groups:
        df_data['Group'] = groups
        color_map_key = 'Group'
    else:
        # If no groups, color individually if colors provided
        if colors:
             df_data['Color'] = colors
             color_map_key = 'Color'
        else:
             color_map_key = 'Task' # Default color by task if no groups/colors

    df = pd.DataFrame(df_data)

    # Create the figure using Plotly Express for easier Gantt creation
    try:
        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color=color_map_key,
            title=title,
            color_discrete_map= {c:c for c in colors} if colors and color_map_key == 'Color' else None # Use direct colors if provided
        )

        # Update layout for better Gantt appearance
        fig.update_layout(
            height=height,
            width=width,
            showlegend=show_legend,
            xaxis_title="Date",
            yaxis_title="Task",
            # Ensure y-axis categories are ordered as provided
            yaxis={'categoryorder':'array', 'categoryarray':tasks[::-1]} # Reverse for typical Gantt top-down
        )
        fig.update_xaxes(type='date')

    except Exception as e:
        logger.error(f"Error creating timeline chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


def create_heatmap_chart(**kwargs: Any) -> go.Figure:
    """
    Create a heatmap chart using Plotly from flat keyword arguments.

    Args:
        **kwargs: Keyword arguments including chart data and config.
                  Expected: x_values, y_values, z_values, color_scale,
                            title, x_axis_title, y_axis_title, height, width.

    Returns:
        Plotly figure object
    """
    # Extract data and config directly from kwargs
    x_values = kwargs.get("x_values", [])
    y_values = kwargs.get("y_values", [])
    z_values = kwargs.get("z_values", [])
    color_scale = kwargs.get("color_scale")
    title = kwargs.get("title", "Heatmap")
    x_axis_title = kwargs.get("x_axis_title", "")
    y_axis_title = kwargs.get("y_axis_title", "")
    height = kwargs.get("height", 400)
    width = kwargs.get("width")

    # Ensure we have data
    if not x_values or not y_values or not z_values:
        logger.warning("Invalid data for heatmap chart (missing x, y, or z values)")
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Invalid Data")
        return fig
    # Add dimension checks if needed (e.g., len(z) == len(y), len(z[0]) == len(x))

    # Create the figure
    try:
        fig = go.Figure(go.Heatmap(
            z=z_values,
            x=x_values,
            y=y_values,
            colorscale=color_scale
        ))

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_axis_title,
            yaxis_title=y_axis_title,
            height=height,
            width=width
        )
    except Exception as e:
        logger.error(f"Error creating heatmap chart figure: {e}", exc_info=True)
        fig = go.Figure()
        fig.update_layout(title=f"{title} - Error: Chart Creation Failed")

    return fig


# --- Deprecated/Unused Functions ---

# The create_chart function is less useful now as create_direct_chart calls helpers directly
# def create_chart(chart_type: ChartType, data: Dict[str, Any],
#                  config: Optional[Dict[str, Any]] = None) -> go.Figure:
#     """
#     DEPRECATED: Create a chart of the specified type using Plotly.
#     Use specific create_*_chart functions instead.
#     """
#     # ... (implementation remains the same, but marked as deprecated)
#     pass

# fig_to_json is no longer needed here as serialization happens in reporting_tools.py
# def fig_to_json(fig: go.Figure) -> Dict[str, Any]:
#     """
#     DEPRECATED: Convert a Plotly figure to a JSON representation.
#     Use plotly.io.to_json directly.
#     """
#     # return json.loads(fig.to_json())
#     pass

# convert_to_chart_data might still be useful internally or elsewhere, but not directly
# needed for the create_direct_chart -> helper flow with flat kwargs.
# Keeping it for now in case other parts of the system rely on it.
def convert_to_chart_data(data: Dict[str, Any], chart_type: ChartType) -> Dict[str, Any]:
    """
    Convert raw data to the format needed for a specific chart type.
    NOTE: This might be less relevant now that helpers accept flat kwargs.

    Args:
        data: Raw data
        chart_type: Type of chart

    Returns:
        Formatted data for the chart
    """
    if not data:
        return {}

    if chart_type == "bar":
        return {
            "x_values": data.get("categories", data.get("labels", [])),
            "y_values": data.get("values", []),
            "orientation": data.get("orientation", "vertical")
        }
    elif chart_type == "line":
        if "series" in data:
            # Multiple series format
            series = data.get("series", [])
            series_names = [s.get("name", f"Series {i+1}") for i, s in enumerate(series)]
            y_values = [s.get("values", []) for s in series]
            return {
                "x_values": data.get("categories", []),
                "y_values": y_values,
                "series_names": series_names,
                "show_markers": data.get("show_markers", True),
                "line_shape": data.get("line_shape", "linear")
            }
        else:
            # Single series format
            return {
                "x_values": data.get("categories", []),
                "y_values": [data.get("values", [])], # Wrap in list for consistency
                "series_names": ["Series 1"],
                "show_markers": data.get("show_markers", True),
                "line_shape": data.get("line_shape", "linear")
            }
    elif chart_type == "pie":
        return {
            "labels": data.get("labels", []),
            "values": data.get("values", []),
            "hole": data.get("hole", 0.0)
        }
    elif chart_type == "scatter":
        return {
            "x_values": data.get("x", []),
            "y_values": data.get("y", []),
            "text_labels": data.get("text", []),
            "sizes": data.get("sizes", []),
            "colors": data.get("colors", []),
            "color_scale": data.get("color_scale")
        }
    elif chart_type == "timeline":
        return {
            "tasks": data.get("tasks", []),
            "start_dates": data.get("start_dates", []),
            "end_dates": data.get("end_dates", []),
            "colors": data.get("colors", []),
            "group": data.get("group", [])
        }
    elif chart_type == "heatmap":
        return {
            "x_values": data.get("x_values", []),
            "y_values": data.get("y_values", []),
            "z_values": data.get("z_values", []),
            "color_scale": data.get("color_scale")
        }
    else:
        # Return original data if type is unknown or doesn't need conversion
        return data
