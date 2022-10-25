import numpy as np
from dash import Input, Output, State, callback, ctx, dash_table, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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

range_plot_column_contents = [
    html.H3(children="Time in range per day"),
    dbc.InputGroup(
        [
            dbc.InputGroupText("A distinct low is at least one point <="),
            dbc.Input(
                type="number",
                min=0,
                step=1,
                value=70,
                id="distinct-low-threshold",
            ),
        ],
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupText("followed by at least "),
            dbc.Input(
                type="number",
                min=0,
                step=1,
                value=5,
                id="n-recovered-pts-between-lows",
            ),
            dbc.InputGroupText("points > "),
            dbc.Input(
                type="number",
                min=0,
                step=1,
                value=80,
                id="recovered-threshold",
            ),
            dbc.InputGroupText("(not necessarily consecutive)"),
        ],
    ),
    dbc.Spinner(
        dcc.Graph(
            id="range-fraction-by-day-graph",
        )
    ),
]


def register_callbacks():
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
            "low_threshold": Input(
                component_id="distinct-low-threshold", component_property="value"
            ),
            "recovered_threshold": Input(
                component_id="recovered-threshold", component_property="value"
            ),
            "n_recovered_pts_between_lows": Input(
                component_id="n-recovered-pts-between-lows", component_property="value"
            ),
        },
    )
    def update_table_and_range_plot(
        bg_data,
        table_data,
        table_update,
        row_button_clicks,
        columns,
        timezone_name,
        low_threshold,
        recovered_threshold,
        n_recovered_pts_between_lows,
    ):

        bg_data = bg_data_json_to_df(bg_data, timezone_name)
        cgm_data = bg_data.loc[bg_data["eventType"] == "sgv"]
        bg = cgm_data["bg"]
        n_records = len(cgm_data)
        existing_labels = []

        if ctx.triggered_id == "add-row-button":
            table_data.append({c["id"]: "" for c in columns})
        # Calculate and update stats for the table
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

        # Detect distinct lows
        cgm_data["recovered_point_count"] = (
            cgm_data["bg"] > recovered_threshold
        ).cumsum()
        cgm_data["is_distinct_low"] = False
        n_recovered_points_at_last_low = -n_recovered_pts_between_lows
        for index, row in cgm_data.loc[cgm_data["bg"] <= low_threshold].iterrows():
            is_distinct_low = (
                row["recovered_point_count"]
                >= n_recovered_points_at_last_low + n_recovered_pts_between_lows
            )
            if is_distinct_low:
                n_recovered_points_at_last_low = row["recovered_point_count"]
                cgm_data.loc[index, "is_distinct_low"] = True

        # Summarize time-in-range per day
        cgm_by_date = cgm_data[["bg", "is_distinct_low", "date"]].groupby("date")
        range_summary = pd.DataFrame(
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
        range_summary.reset_index(inplace=True)
        range_summary_long = pd.melt(
            range_summary,
            id_vars="date",
            var_name="range",
            value_name="fraction",
        )

        # Main plot: time in each range per day
        range_fig = px.area(
            range_summary_long,
            x="date",
            y="fraction",
            color="range",
            labels={"range": "Range", "date": "Date", "fraction": "Fraction of day"},
            line_shape="spline",
            pattern_shape="range",
        )

        # Secondary plot: distinct lows per day
        low_summary = pd.DataFrame(
            {"distinct_lows": cgm_by_date["is_distinct_low"].sum()}
        )
        low_summary.reset_index(inplace=True)  # so we have date column
        low_fig = px.line(
            low_summary,
            x="date",
            y="distinct_lows",
            labels={
                "distinct_lows": "# separate lows",
                "date": "Date",
            },
            line_shape="hvh",
            markers=True,
        )
        low_fig.update_traces(
            yaxis="y2",
            line_color="rgb(0,0,0)",
            name="Distinct lows",
            showlegend=True,
        )
        # Combine the two figures to have a secondary y-axis while still using plotly express.
        # See https://stackoverflow.com/a/62853540
        combined_fig = make_subplots(specs=[[{"secondary_y": True}]])
        combined_fig.add_traces(range_fig.data + low_fig.data)
        combined_fig.layout.yaxis.title = "Fraction of day"
        combined_fig.layout.yaxis2.title = "# events per day"

        add_light_style(combined_fig)
        combined_fig.update_layout(
            margin=dict(l=40, r=40, t=40, b=40),
            height=400,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        if not range_summary_long.empty:
            combined_fig.update_yaxes(
                range=[0, range_summary_long.groupby("date")["fraction"].sum().max()],
                secondary_y=False,
            )
        combined_fig.update_xaxes(
            range=[range_summary_long["date"].min(), range_summary_long["date"].max()]
        )
        combined_fig.update_yaxes(
            dtick=1,
            secondary_y=True,
        )

        return {
            "data": table_data,
            "summary_text": f"{n_records} readings over {bg_data['date'].nunique()} days. Mean {bg.mean():.0f} (+/- {bg.std():.1f})",
            "graph": combined_fig,
        }
