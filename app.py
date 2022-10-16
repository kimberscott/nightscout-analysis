import datetime

from dash import (
    Dash,
    Input,
    Output,
    callback,
    State,
)
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from nightscout_dash.layout import generate_ns_layout

import flask

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
        margin=dict(l=40, r=40, t=80, b=40),
        height=240,
        title="All loaded data<br><sub>To confirm availability of data (not intended for direct use in analysis)</sub>",
        xaxis_title="Date",
        yaxis_title="mg/dL",
    )
    return {
        "graph": figure,
    }


@callback(
    output={
        "title": Output("subset-data-header", "children"),
    },
    inputs={
        "submit_button": Input(
            component_id="submit-button", component_property="n_clicks"
        ),
        "start_date_str": State(
            component_id="data-date-range", component_property="start_date"
        ),
        "end_date_str": State(
            component_id="data-date-range", component_property="end_date"
        ),
    },
)
def update_header(submit_button, start_date_str, end_date_str):

    # TODO: store info in URL query params
    # import urllib.parse

    # parsed_url = urllib.parse.urlparse(flask.request.referrer)
    # parsed_query = urllib.parse.parse_qs(parsed_url.query)

    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)
    if start_date.year == end_date.year:
        date_description = (
            f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        )
    else:
        date_description = (
            f"{start_date.strftime('%b %d %y')} - {end_date.strftime('%b %d %y')}"
        )

    n_days = (end_date - start_date).days + 1  # inclusive of endpoints
    header_str = f"{date_description} ({n_days} days)"
    return {
        "title": header_str,
    }


if __name__ == "__main__":
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
    server = app.server
    app.layout = generate_ns_layout
    app.title = "Nightscout analysis"
    app.run_server(debug=True)
