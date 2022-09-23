import numpy as np
from dash import Input, Output, State, callback, ctx, dash_table, html
import dash_bootstrap_components as dbc
import pandas as pd


distribution_table_column_contents = [
    html.H2(children="CGM distribution summary"),
    html.Div(id="distribution-summary-text", children=""),
    dash_table.DataTable(
        id="distribution-summary-table",
        row_deletable=True,
        columns=[
            {
                "id": "lower",
                "name": "Lower limit",
                "editable": True,
                "type": "numeric",
            },
            {
                "id": "upper",
                "name": "Upper limit",
                "editable": True,
                "type": "numeric",
            },
            {
                "id": "BG range",
                "name": "BG range",
                "editable": False,
            },
            {
                "id": "percent",
                "name": "Percent",
                "type": "numeric",
                "editable": False,
                "format": dash_table.FormatTemplate.percentage(1),
            },
        ],
        data=pd.DataFrame(
            data={
                "lower": [None, 54, 63, 130],
                "upper": [54, 63, 130, None],
            }
        ).to_dict(orient="records"),
    ),
    dbc.Button(
        "Add row",
        id="add-row-button",
        outline=True,
        color="primary",
        className="me-1",
    ),
]


@callback(
    output={
        "data": Output("distribution-summary-table", "data"),
        "summary_text": Output("distribution-summary-text", "children"),
    },
    inputs={
        "bg_data": Input("subset-bg-data", "data"),
        "table_data": State("distribution-summary-table", "data"),
        "table_update": Input("distribution-summary-table", "data_timestamp"),
        "row_button_clicks": Input("add-row-button", "n_clicks"),
        "columns": State("distribution-summary-table", "columns"),
    },
)
def update_table(bg_data, table_data, table_update, row_button_clicks, columns):

    bg_data = pd.read_json(bg_data, orient="split")
    bg = bg_data.loc[bg_data["eventType"] == "sgv", "bg"]
    n_records = len(bg)

    if ctx.triggered_id == "add-row-button":
        table_data.append({c["id"]: "" for c in columns})
    else:
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
