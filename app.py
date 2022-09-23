import numpy as np
from dash import (
    Dash,
    Input,
    Output,
    State,
    callback,
    no_update,
    dash_table,
)
import dash_bootstrap_components as dbc


import pandas as pd
import plotly.graph_objects as go

from nightscout_dash.layout import ns_layout

# Leave this in to make sure we load the callback!
# TODO: create register_callbacks function
from nightscout_dash.update_data import load_nightscout_data


@callback(
    output={
        "graph": Output("loaded-data-graph", "figure"),
    },
    inputs={
        "bg_data": Input("all-bg-data", "data"),
    },
)
def update_graph(bg_data):

    if not bg_data:
        figure = go.Figure()
    else:
        df = pd.read_json(bg_data, orient="split")

        cgm_vs_mbg = (df["eventType"] == "sgv") * 0 + (df["eventType"] == "mbg") * 1

        figure = go.Figure(
            data=go.Scatter(
                x=df["datetime"],
                y=df["bg"],
                mode="markers",
                marker=dict(
                    size=2 + (cgm_vs_mbg * 10),
                    color=df["datetime"].dt.hour,
                    line_color=df["datetime"].dt.hour,
                    colorscale="hsv",
                    showscale=True,
                    # circle and cross
                    symbol=cgm_vs_mbg
                    * 4,  # df["eventType"].astype("category").cat.codes,
                    colorbar=dict(title="Hour"),
                    line_width=0,
                ),
            ),
        )
    figure.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),
        height=200,
        title="All loaded data",
        xaxis_title="Date",
        yaxis_title="mg/dL",
    )
    return {
        "graph": figure,
    }


@callback(
    output={
        "data": Output("distribution-summary-table", "data"),
        "summary_text": Output("distribution-summary-text", "children"),
    },
    inputs={
        "bg_data": Input("subset-bg-data", "data"),
        "table_data": State("distribution-summary-table", "data"),
        "table_update": Input("distribution-summary-table", "data_timestamp"),
    },
)
def update_table(bg_data, table_data, table_update):

    bg_data = pd.read_json(bg_data, orient="split")
    bg = bg_data.loc[bg_data["eventType"] == "sgv", "bg"]
    n_records = len(bg)

    for row in table_data:
        try:
            lower = float(row["lower"] or 0)
            upper = float(row["upper"] or np.inf)
            row["BG range"] = f"[{lower:.0f}, {upper:.0f})"
            row["percent"] = sum((bg >= lower) & (bg < upper)) / n_records
        except ValueError:
            row["BG range"] = "N/A"
            row["percent"] = np.nan

    return {
        "data": table_data,
        "summary_text": f"{n_records} readings over {bg_data['date'].nunique()} days.",
    }


if __name__ == "__main__":
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
    app.layout = ns_layout
    app.title = "Nightscout analysis"
    app.run_server(debug=True)
