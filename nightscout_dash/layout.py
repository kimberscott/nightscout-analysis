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
                    className="mb-6",
                ),
                html.Br(),
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
                    className="mb-6",
                ),
                html.Br(),
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("Nightscout URL"),
                        dcc.Input(
                            id="nightscout-url",
                            value="",
                        ),
                    ],
                    className="mb-6",
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
        ),
        dbc.Col(
            [
                dbc.Spinner(
                    dcc.Graph(
                        id="loaded-data-graph",
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
        form,
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
