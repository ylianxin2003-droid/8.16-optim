"""
Plotly-based visualisation functions for the aviation space weather dashboard.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Colour maps ─────────────────────────────────────────────────────────────




# ── Time series ─────────────────────────────────────────────────────────────


def create_time_series_plot(
    df: pd.DataFrame,
    variable: str | None = None,
    title: str | None = None,
) -> go.Figure:
    """Create a time-series line plot for one or all variables.

    Parameters
    ----------
    df : DataFrame
        Must contain at least ``time``, ``value``, and ``variable`` columns.
    variable : str, optional
        Filter to a single variable.  If ``None``, plot all variables.
    title : str, optional
        Chart title.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for time-series plot.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    work = df.copy()
    if variable:
        work = work[work["variable"] == variable]

    if work.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No data for variable '{variable}'.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    if "time" in work.columns:
        work["time"] = pd.to_datetime(work["time"], errors="coerce")
    else:
        work["time"] = pd.NaT
    if work["time"].notna().any():
        x_col = "time"
        x_label = "Time"
    else:
        work = work.reset_index(drop=True)
        work["sample"] = work.index + 1
        x_col = "sample"
        x_label = "API sample"

    # Aggregate: mean value per time step per variable.
    grouped = work.groupby([x_col, "variable"], as_index=False)["value"].mean()

    if grouped["variable"].nunique() <= 1:
        fig = px.line(
            grouped, x=x_col, y="value", color="variable",
            title=title or "Ionospheric parameter over time",
            labels={"value": "Value", x_col: x_label, "variable": "Variable"},
            markers=True,
        )
    else:
        fig = make_subplots(
            rows=grouped["variable"].nunique(),
            cols=1,
            shared_xaxes=True,
            subplot_titles=list(grouped["variable"].unique()),
        )
        for i, var in enumerate(grouped["variable"].unique()):
            sub = grouped[grouped["variable"] == var]
            fig.add_trace(
                go.Scatter(x=sub[x_col], y=sub["value"], mode="lines+markers", name=var),
                row=i + 1, col=1,
            )
        fig.update_xaxes(title_text=x_label, row=grouped["variable"].nunique(), col=1)
        fig.update_layout(
            title_text=title or "Ionospheric parameters over time",
            height=250 * grouped["variable"].nunique(),
        )

    fig.update_layout(template="plotly_white", hovermode="x unified")
    return fig

# ── Map plot ────────────────────────────────────────────────────────────────


def create_map_plot(
    df: pd.DataFrame,
    variable: str | None = None,
    title: str | None = None,
) -> go.Figure:
    """Create a scatter-geo map of the data.

    Expects ``lat``, ``lon``, ``value`` columns.

    Parameters
    ----------
    df : DataFrame
    variable : str, optional
        Filter to one variable.
    title : str, optional

    Returns
    -------
    plotly.graph_objects.Figure
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for map plot.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    work = df.copy()
    if variable:
        work = work[work["variable"] == variable]

    if "lat" not in work.columns or "lon" not in work.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Data does not contain lat/lon columns for map display.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    for col in ("lat", "lon", "value"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.dropna(subset=["lat", "lon", "value"])
    if work.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No mappable lat/lon data for {variable or 'selected data'}.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    # Keep maps responsive for large API point grids.
    if len(work) > 3000:
        work = work.sample(n=3000, random_state=42)

    # If multiple time steps, use the latest.
    if "time" in work.columns:
        work["time"] = pd.to_datetime(work["time"], errors="coerce")
        valid_times = work["time"].dropna()
        if not valid_times.empty:
            work = work[work["time"] == valid_times.max()]

    fig = px.scatter_geo(
        work,
        lat="lat",
        lon="lon",
        color="value",
        size="value",
        hover_name="variable" if "variable" in work.columns else None,
        hover_data=["value", "variable"] if "variable" in work.columns else ["value"],
        title=title or f"Global {variable or 'ionospheric'} map",
        color_continuous_scale="Plasma",
        projection="natural earth",
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="gray",
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="aliceblue",
    )
    fig.update_layout(template="plotly_white", height=500)
    return fig


# ── Alert timeline ──────────────────────────────────────────────────────────




# ── Alert summary ───────────────────────────────────────────────────────────
