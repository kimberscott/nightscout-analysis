from dash import Input, Output, State, callback
import pandas as pd
from datetime import date
import datetime
import string
import random
import math
import plotly.express as px
import plotly.graph_objects as go

from nightscout_loader import (
    get_basal_per_hour,
)


@callback(
    output={
        "graph": Output("basal-rate-graph", "figure"),
    },
    inputs={
        "bg_json": Input("subset-bg-data", "data"),
        "profile_json": Input("profile-data", "data"),
        "start_date_str": State(
            component_id="data-date-range", component_property="start_date"
        ),
        "end_date_str": State(
            component_id="data-date-range", component_property="end_date"
        ),
        "timezone_name": Input(
            component_id="timezone-name", component_property="value"
        ),
        "basal_rate_includes_scheduled": Input(
            component_id="basal-rate-includes-scheduled", component_property="value"
        ),
    },
)
def update_figure(
    bg_json,
    profile_json,
    start_date_str,
    end_date_str,
    timezone_name: str,
    basal_rate_includes_scheduled,
):

    all_bg_data = pd.read_json(bg_json, orient="split")
    all_bg_data["datetime"] = pd.to_datetime(
        all_bg_data["datetime"], utc=True
    ).dt.tz_convert(timezone_name)

    profiles = pd.read_json(profile_json, orient="split")
    profiles["profile_start_datetime"] = pd.to_datetime(
        profiles["profile_start_datetime"], utc=True
    ).dt.tz_convert(timezone_name)

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    basals_per_hour = get_basal_per_hour(
        all_bg_data, profiles, start_date, end_date, timezone_name
    )
    if not basal_rate_includes_scheduled:
        basals_per_hour = basals_per_hour.loc[basals_per_hour["is_adjusted"] == True]
    hourly_grouped = basals_per_hour[["time_label", "scheduled", "avg_basal"]].groupby(
        "time_label"
    )
    hourly_summary = pd.DataFrame(
        data={
            "median": hourly_grouped["avg_basal"].quantile(q=0.5),
            "perc_10": hourly_grouped["avg_basal"].quantile(q=0.1),
            "perc_90": hourly_grouped["avg_basal"].quantile(q=0.9),
            "min": hourly_grouped["avg_basal"].min(),
            "max": hourly_grouped["avg_basal"].max(),
            "mean": hourly_grouped["avg_basal"].mean(),
            "mean_scheduled": hourly_grouped["scheduled"].mean(),
            "min_scheduled": hourly_grouped["scheduled"].min(),
            "max_scheduled": hourly_grouped["scheduled"].max(),
        }
    )

    def add_area_to_plot(fig, x, lo, hi, legend_text, color, **trace_params):
        legend_group = "".join(random.sample(string.ascii_letters, 6))
        fig.add_trace(
            go.Scatter(
                x=x,
                y=lo,
                mode="lines",
                fill="none",
                line_color=color,
                legendgroup=legend_group,
                showlegend=False,
                **trace_params,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=hi,
                fill="tonexty",
                mode="none",
                fillcolor=color,
                legendgroup=legend_group,
                name=legend_text,
                **trace_params,
            )
        )

    # Individual day basals

    fig = px.line(
        basals_per_hour,
        x="time_label",
        y="avg_basal",
        color="date",
        symbol="date",
        line_dash="date",
        markers=True,
    )
    fig.update_traces(
        line=dict(width=1),
        legendgroup="Individual day basal rates",
        legendrank=1001,
        legendgrouptitle_text="Individual date",
        marker_size=5,
        line_shape="spline",
    )

    # Actual basal range
    add_area_to_plot(
        fig,
        x=hourly_summary.index,
        lo=hourly_summary["perc_10"],
        hi=hourly_summary["perc_90"],
        legend_text="10th - 90th percentile rate",
        color="rgba(100, 100, 100, 0.5)",
        line_shape="hvh",
        fillpattern_shape="x",
        line_width=0.1,
    )
    # Scheduled basal rate/range
    add_area_to_plot(
        fig,
        x=hourly_summary.index,
        lo=hourly_summary["min_scheduled"],
        hi=hourly_summary["max_scheduled"],
        legend_text="Scheduled rate (range)",
        color="rgba(255, 87, 51, 0.8)",
        line_shape="hvh",
        fillpattern_shape=".",
        line_width=5,
    )

    # Mean actual basal
    fig.add_trace(
        go.Scatter(
            x=hourly_summary.index,
            y=hourly_summary["mean"],
            mode="lines",
            name="Mean actual rate",
            line_color="black",
            line_shape="hvh",
            line_width=3,
        )
    )

    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),
        height=400,
        # title="Basal rates",
        xaxis_title="Time of day",
        yaxis_title="u/hr",
        legend_title="Summary",
    )
    fig.update_xaxes(
        dtick=60 * 60 * 1000,
        tickformat="%I%p",
        ticklabelmode="period",
        range=[
            basals_per_hour["time_label"].min() - datetime.timedelta(minutes=5),
            basals_per_hour["time_label"].max() + datetime.timedelta(minutes=5),
        ],
    )
    fig.update_yaxes(
        range=[
            -0.05,
            math.ceil(basals_per_hour["avg_basal"].max() * 2) / 2.0,
        ],
    )

    return {
        "graph": fig,
    }
