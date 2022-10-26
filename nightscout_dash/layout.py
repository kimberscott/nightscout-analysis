from dash import html, dcc
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

from nightscout_dash.basal_rate_plot import BasalRatePlot
from nightscout_dash.distribution_table import DistributionTable
from nightscout_dash.site_change_plot import SiteChangePlot
from nightscout_dash.update_data import DataUpdater

load_dotenv()


def generate_ns_layout():

    default_spacing_class = "mb-3"

    ns_layout = html.Div(
        children=[
            html.H1(
                children="Nightscout data analysis", className=default_spacing_class
            ),
            dbc.Row(
                [
                    dbc.Col(
                        DataUpdater().layout_contents,
                        width=5,
                        xs={"width": 6, "offset": 0},
                        lg={"width": 5, "offset": 0},
                        class_name="text-right",
                    ),
                    dbc.Col(
                        [
                            html.H2(children="About"),
                            html.Div(
                                children="""This Dash app displays custom plots to help understand Nightscout data about
                                blood sugar and treatments. It is currently a skeleton with ongoing work on
                                expanding plot types. Coming soon: """
                            ),
                            html.Ul(
                                children=[
                                    html.Li("BG percentiles by day"),
                                    html.Li(
                                        "annotations showing profile change timing"
                                    ),
                                ],
                                className=default_spacing_class,
                            ),
                            html.Div(
                                children="Data is loaded via the Nightscout API, not directly from the MongoDB. When "
                                "data for a given range is loaded, it is then stored so that if the range is "
                                "changed only data not previously requested is loaded.",
                                className=default_spacing_class,
                            ),
                            html.Div(
                                children="The next priority is to implement a simple tool for easily adding "
                                "annotations - e.g. 'forgot to dose' or 'probably underestimated carbs' or "
                                "'pressure low' - as well as special event types like 'exclude this range' "
                                "to more flexibly focus on 'good' data in analysis.",
                                className=default_spacing_class,
                            ),
                        ],
                        width=3,
                        xs={"width": 5, "offset": 0},
                        lg={"width": 3, "offset": 3},
                        class_name="mr-3",
                    ),
                ],
                class_name=default_spacing_class,
            ),
            dbc.Row(
                [
                    html.H2(
                        id="subset-data-header",
                        style={"text-align": "center"},
                    ),
                ]
            ),
            dbc.Row(DistributionTable().layout_contents),
            dbc.Row(
                [
                    dbc.Col(
                        BasalRatePlot().layout_contents,
                        width=6,
                    ),
                    dbc.Col(
                        SiteChangePlot().layout_contents,
                        width=6,
                    ),
                ],
            ),
            dcc.Store(id="all-bg-data"),
            dcc.Store(id="subset-bg-data"),
            dcc.Store(id="first-load-dummy"),
            dcc.Store(id="already-loaded-dates"),
            dcc.Store(id="profile-data"),
            dcc.Store(id="loaded-nightscout-url"),
        ]
    )

    return ns_layout
