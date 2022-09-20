import datetime

from nightscout_dash.layout import ns_layout

from dash import Dash, html, dcc, Input, Output, State
import dash
import dash_bootstrap_components as dbc

import plotly.express as px
import pandas as pd
from demo import fetch_nightscout_data


@dash.callback(
    output={
        "bg_data": Output(component_id="bg-data", component_property="data"),
        "treatment_data": Output(
            component_id="treatment-data", component_property="data"
        ),
    },
    inputs={
        "dummy": Input(component_id="first-load-dummy", component_property="data"),
    },
)
def load_nightscout_data(dummy):
    start_dt = datetime.timedelta(days=21)
    end_dt = datetime.timedelta(days=20)
    now = datetime.datetime.now()
    bg, treatments = fetch_nightscout_data(now - start_dt, now - end_dt)
    return {
        "bg_data": bg.to_json(orient="split"),
        "treatment_data": treatments.to_json(orient="split"),
    }


@dash.callback(
    output={
        "graph": Output("example-graph", "figure"),
    },
    inputs={
        "bg_data": Input("bg-data", "data"),
    },
)
def update_graph(bg_data):

    df = pd.read_json(bg_data, orient="split")

    figure = px.line(df, x="datetime", y="sgv")
    return {
        "graph": figure,
    }


if __name__ == "__main__":
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
    app.layout = ns_layout
    app.run_server(debug=True)
