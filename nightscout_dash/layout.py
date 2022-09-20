
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

from datetime import date

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])



form = dbc.Row(
    [
        dbc.Col(
            [
                dbc.Label("Email", html_for="example-email-grid"),
                dbc.Input(
                    type="email",
                    id="example-email-grid",
                    placeholder="Enter email",
                ),
            ],
            width=6,
        ),
        dbc.Col(
            [
                dbc.Label("Range", html_for="example-password-grid"),
dcc.DatePickerRange(
        id='my-date-picker-range',
        min_date_allowed=date(1995, 8, 5),
        max_date_allowed=date(2017, 9, 19),
        initial_visible_month=date(2017, 8, 5),
        end_date=date(2017, 8, 25),
className='form-control',
    ),
            ],
            width=6,
        ),
    ],
    className="g-3",
)

ns_layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    form,

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='example-graph',
    ),

    dcc.Store(id='bg-data'),
    dcc.Store(id='treatment-data'),

    dcc.Store(id='first-load-dummy'),
])
