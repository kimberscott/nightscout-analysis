import datetime

from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
from demo import fetch_nightscout_data

app = Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

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


@app.callback(
    output={
        'bg_data': Output(component_id='bg-data', component_property='data'),
        'treatment_data': Output(component_id='treatment-data', component_property='data'),
    },
    inputs={
        'dummy': Input(component_id='first-load-dummy', component_property='data'),
    }
)
def load_nightscout_data(dummy):
    start_dt = datetime.timedelta(days=21)
    end_dt = datetime.timedelta(days=20)
    now = datetime.datetime.now()
    bg, treatments = fetch_nightscout_data(now - start_dt, now - end_dt)
    return {
        'bg_data': bg.to_json(orient='split'),
        'treatment_data': treatments.to_json(orient='split'),
    }

@app.callback(
    output={
        'graph': Output('example-graph', 'figure'),
    },
    inputs={
        'bg_data': Input('bg-data', 'data'),
    }
)
def update_graph(bg_data):

    df = pd.read_json(bg_data, orient='split')

    figure = px.line(df, x='datetime', y="sgv")
    return {
        'graph': figure,
    }

if __name__ == '__main__':
    app.run_server(debug=True)