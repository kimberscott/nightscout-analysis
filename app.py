from dash import (
    Dash,
    Input,
    Output,
    callback,
)
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from nightscout_dash.layout import ns_layout

# Leave this in to make sure we load the callback!
# TODO: create register_callbacks functions
from nightscout_dash.update_data import load_nightscout_data
import nightscout_dash.distribution_table
import nightscout_dash.basal_rate_plot


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


if __name__ == "__main__":
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
    app.layout = ns_layout
    app.title = "Nightscout analysis"
    app.run_server(debug=True)
