import numpy as np
from dash import Input, Output, State, callback, ctx, dash_table, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

from nightscout_dash.data_utils import bg_data_json_to_df
from nightscout_dash.plot_utils import add_light_style

distribution_table_column_contents = [
    html.H3(children="CGM distribution summary"),
    dbc.Spinner(html.Div(id="distribution-summary-text", children="")),
    dbc.Spinner(
        [
            dash_table.DataTable(
                id="distribution-summary-table",
                row_deletable=True,
                columns=[
                    {
                        "id": "label",
                        "name": "Label",
                        "editable": True,
                    },
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
                        "lower": [None, 55, 70, 180, 300],
                        "upper": [55, 70, 180, 300, None],
                        "label": [
                            "Very low",
                            "Low",
                            "In range",
                            "High",
                            "Very high",
                        ],
                    }
                ).to_dict(orient="records"),
            ),
            html.Br(),
            dbc.Button(
                "Add row",
                id="add-row-button",
                outline=True,
                color="primary",
                className="me-1",
            ),
        ]
    ),
]


@callback(
    output={
        "data": Output("distribution-summary-table", "data"),
        "summary_text": Output("distribution-summary-text", "children"),
        "graph": Output("range-fraction-by-day-graph", "figure"),
    },
    inputs={
        "bg_data": Input("subset-bg-data", "data"),
        "table_data": State("distribution-summary-table", "data"),
        "table_update": Input("distribution-summary-table", "data_timestamp"),
        "row_button_clicks": Input("add-row-button", "n_clicks"),
        "columns": State("distribution-summary-table", "columns"),
        "timezone_name": State(
            component_id="timezone-name", component_property="value"
        ),
    },
)
def update_table(
    bg_data, table_data, table_update, row_button_clicks, columns, timezone_name
):

    bg_data = bg_data_json_to_df(bg_data, timezone_name)
    cgm_data = bg_data.loc[bg_data["eventType"] == "sgv"]
    bg = cgm_data["bg"]
    n_records = len(cgm_data)
    existing_labels = []

    if ctx.triggered_id == "add-row-button":
        table_data.append({c["id"]: "" for c in columns})
    else:
        for row in table_data:
            try:
                lower = float(row["lower"] or 0)
                upper = float(row["upper"] or np.inf)
                row["BG range"] = f"[{lower:.0f}, {upper:.0f})"
                row["percent"] = sum((bg >= lower) & (bg < upper)) / n_records

                # Enforce uniqueness of labels
                label = row["label"]
                while label in existing_labels:
                    label = label + "_1"
                row["label"] = label
                existing_labels.append(label)

            except ValueError:
                row["BG range"] = "N/A"
                row["percent"] = np.nan

    cgm_by_date = cgm_data[["bg", "date"]].groupby("date")
    summary = pd.DataFrame(
        {
            row["label"]: cgm_by_date["bg"].aggregate(
                lambda x: sum(
                    (x <= float(row["upper"] or np.inf))
                    & (x > float(row["lower"] or 0))
                )
                / len(x)
            )
            for row in table_data
        }
    )
    # Make a column with the date instead of using as index, before melting to long format
    summary.reset_index(inplace=True)
    summary_long = pd.melt(
        summary,
        id_vars="date",
        var_name="range",
        value_name="fraction",
    )
    fig = px.area(
        summary_long,
        x="date",
        y="fraction",
        color="range",
        labels={"range": "Range", "date": "Date", "fraction": "Fraction of day"},
        line_shape="spline",
        pattern_shape="range",
    )
    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),
        height=400,
    )
    if not summary_long.empty:
        fig.update_yaxes(
            range=[0, summary_long.groupby("date")["fraction"].sum().max()]
        )
    add_light_style(fig)

    return {
        "data": table_data,
        "summary_text": f"{n_records} readings over {bg_data['date'].nunique()} days. Mean {bg.mean():.0f} (+/- {bg.std():.1f})",
        "graph": fig,
    }
