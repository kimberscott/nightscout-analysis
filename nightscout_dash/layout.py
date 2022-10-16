from dash import html, dcc
import dash_bootstrap_components as dbc
import datetime
import tzlocal
import zoneinfo
from dotenv import load_dotenv
import os

from nightscout_dash.distribution_table import distribution_table_column_contents

load_dotenv()


def generate_ns_layout():

    default_spacing_class = "mb-3"

    select_and_check = [
        html.H2(children="Select data"),
        dbc.InputGroup(
            [
                dbc.InputGroupText("Time zone"),
                dbc.Select(
                    id="timezone-name",
                    options=[
                        {"label": zone_name, "value": zone_name}
                        for zone_name in zoneinfo.available_timezones()
                    ],
                    value=os.getenv(
                        "LOCALZONE_NAME",
                        default=tzlocal.get_localzone_name(),
                    ),
                ),
                dbc.Tooltip(
                    "Set a LOCALZONE_NAME environment variable to control the default value.",
                    target="timezone-name",
                ),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("Date range"),
                dcc.DatePickerRange(
                    id="data-date-range",
                    max_date_allowed=datetime.date.today(),
                    end_date=datetime.date.today(),
                    start_date=datetime.date.today() - datetime.timedelta(days=7),
                    className="form-control",
                ),
            ],
            className="mb-2",
        ),
        dbc.InputGroup(
            [
                dbc.InputGroupText("Nightscout URL"),
                dcc.Input(
                    id="nightscout-url",
                    type="text",
                    value=os.getenv("NIGHTSCOUT_URL"),
                    className="form-control",
                ),
            ],
            className="mb-2",
            id="nightscout-url-input-group",
        ),
        dbc.Alert(
            children="Error loading data from Nightscout",
            color="danger",
            id="nightscout-error",
            is_open=False,
        ),
        dbc.Tooltip(
            "Set a NIGHTSCOUT_URL environment variable to control the default value.",
            target="nightscout-url-input-group",
        ),
        dbc.Row(
            [
                dbc.Button(
                    "Submit",
                    outline=True,
                    color="primary",
                    className="ms-auto w-auto",
                    id="submit-button",
                ),
            ]
        ),
        dbc.Spinner(
            dcc.Graph(
                id="loaded-data-graph",
                style={"height": "300px"},
            )
        ),
    ]

    ns_layout = html.Div(
        children=[
            html.H1(
                children="Nightscout data analysis", className=default_spacing_class
            ),
            dbc.Row(
                [
                    dbc.Col(
                        select_and_check,
                        width=5,
                        xs={"width": 6, "offset": 0},
                        lg={"width": 5, "offset": 0},
                        class_name="text-right",
                    ),
                    dbc.Col(
                        [
                            html.H2(children="About"),
                            html.Div(
                                children="This Dash app displays custom plots to help understand Nightscout data about "
                                "blood sugar and treatments. It is currently a skeleton with ongoing work on "
                                "expanding plot types. Coming soon: blood sugar as a function of time since "
                                "site change; plots of the number of distinct lows over time; BG percentiles "
                                "by day; annotations showing profile change timing.",
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
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Spinner(distribution_table_column_contents),
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dcc.Graph(
                                id="percentile-by-day-graph",
                                figure={
                                    "layout": {
                                        "title": "Placeholder: stacked area plot of time per day in <br> each of the ranges defined in the table to the left."
                                    }
                                },
                            ),
                        ],
                        width=6,
                    ),
                ],
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(children="Basal rates"),
                            dbc.Switch(
                                id="basal-rate-includes-scheduled",
                                label="Include regularly-scheduled basals (when Control IQ was not active or we don't have data)",
                                value=False,
                            ),
                            dbc.Spinner(
                                dcc.Graph(
                                    id="basal-rate-graph",
                                )
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
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
