from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
import datetime
import tzlocal
import zoneinfo


from nightscout_dash.distribution_table import distribution_table_column_contents

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


form = dbc.Row(
    [
        dbc.Col(
            [
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
                            value=tzlocal.get_localzone_name(),
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
                            end_date=datetime.date.today()
                            - datetime.timedelta(days=40),
                            start_date=datetime.date.today()
                            - datetime.timedelta(days=47),
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
                            placeholder="Not yet implemented - using value in .env file",
                            className="form-control",
                        ),
                    ],
                    className="mb-2",
                ),
            ],
            width=5,
        ),
        dbc.Col(
            [
                dbc.Button(
                    "Submit",
                    outline=True,
                    color="primary",
                    className="me-1",
                    id="submit-button",
                ),
            ],
            width=1,
            class_name="align-self-end",
        ),
        dbc.Col(
            [
                dbc.Spinner(
                    dcc.Graph(
                        id="loaded-data-graph",
                        style={"height": "300px"},
                    )
                ),
            ],
            width=5,
        ),
    ],
    className="g-3",
)

ns_layout = html.Div(
    children=[
        html.H1(children="Nightscout data analysis"),
        html.H2(children="About"),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        children="""This Dash app displays custom plots to help understand Nightscout data about blood sugar and treatments. It is currently a skeleton with ongoing work on expanding plot types. Coming soon: blood sugar as a function of time since site change; plots of the number of distinct lows over time; BG percentiles by day; annotations showing profile change timing."""
                    ),
                    width=4,
                ),
                dbc.Col(
                    html.Div(
                        children="""Data is loaded via the Nightscout API, not directly from the MongoDB. When data for a given range is loaded, it is then stored so that if the range is changed only data not previously requested is loaded."""
                    ),
                    width=4,
                ),
                dbc.Col(
                    html.Div(
                        children="""The next priority is to implement a simple tool for easily adding annotations - e.g. 'forgot to dose' or 'probably underestimated carbs' or 'pressure low' - as well as special event types like 'exclude this range' to more flexibly focus on 'good' data in analysis."""
                    ),
                    width=4,
                ),
            ]
        ),
        html.Br(),
        form,
        html.Br(),
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
                                    "title": "Placeholder: stacked area plot of time per day in each of the ranges defined in the table to the left."
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
                    width=6,
                ),
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
            ],
        ),
        dcc.Store(id="all-bg-data"),
        dcc.Store(id="subset-bg-data"),
        dcc.Store(id="first-load-dummy"),
        dcc.Store(id="already-loaded-dates"),
        dcc.Store(id="profile-data"),
    ]
)
