from dash import Input, Output, State, callback, html, dcc
import dash_bootstrap_components as dbc

import pandas as pd

from nightscout_dash.data_utils import bg_data_json_to_df, AnalysisComponent
from nightscout_dash.plot_utils import add_light_style

import plotly.express as px
import plotly.graph_objects as go


class SiteChangePlot(AnalysisComponent):
    @property
    def layout_contents(self):
        return [
            html.H3(children="Site change impact"),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Hours to bin together: "),
                    dbc.Input(
                        type="number",
                        min=1,
                        max=24,
                        step=1,
                        value=6,
                        id="site-change-graph-bin-hours",
                    ),
                ],
            ),
            dbc.RadioItems(
                options=[
                    {
                        "label": "Plot over entire site change",
                        "value": 1,
                    },
                    {"label": "Plot over time of day", "value": 2},
                ],
                value=1,
                id="site-change-graph-style",
                inline=True,
            ),
            dbc.Spinner(
                dcc.Graph(
                    id="site-change-graph",
                )
            ),
        ]

    @staticmethod
    def register_callbacks():
        @callback(
            output={
                "graph": Output("site-change-graph", "figure"),
            },
            inputs={
                "bg_json": Input(
                    component_id="subset-bg-data",
                    component_property="data",
                ),
                "timezone_name": State(
                    component_id="timezone-name",
                    component_property="value",
                ),
                "graph_style": Input(
                    component_id="site-change-graph-style",
                    component_property="value",
                ),
                "bin_hours": Input(
                    component_id="site-change-graph-bin-hours",
                    component_property="value",
                ),
            },
            prevent_initial_call=True,
        )
        def update_figure(
            bg_json,
            timezone_name: str,
            graph_style: int,
            bin_hours: float,
        ):

            # Restore timezone data from stored JSON
            all_bg_data = bg_data_json_to_df(bg_json, timezone_name)

            # Get basic info about how long since last site change for each data point
            site_changes = all_bg_data.loc[
                all_bg_data["eventType"] == "Site Change", ["datetime"]
            ].rename(columns={"datetime": "site_change_datetime"})

            if site_changes.empty:
                fig = go.Figure()
                fig.update_layout(
                    title="No recorded site changes",
                )

            else:
                # Could also make a column for site changes only, then use fillna - probably similar implementation?
                all_bg_data = pd.merge_asof(
                    left=all_bg_data,
                    right=site_changes,
                    left_on="datetime",
                    right_on="site_change_datetime",
                )
                all_bg_data["time_since_site_change"] = (
                    all_bg_data["datetime"] - all_bg_data["site_change_datetime"]
                )
                all_bg_data["hours_since_site_change"] = (
                    all_bg_data["time_since_site_change"].dt.days * 24
                    + all_bg_data["time_since_site_change"].dt.seconds / 3600
                )

                if graph_style == 1:

                    # Plot mean over entire course of site (~3 days on x axis)

                    all_bg_data["binned_hours_since_site_change"] = (
                        all_bg_data["hours_since_site_change"] // bin_hours
                    ) * bin_hours + bin_hours / 2

                    grouped_by_time_since_site_change = all_bg_data.loc[
                        all_bg_data["eventType"] == "sgv"
                    ].groupby("binned_hours_since_site_change")
                    site_change_summary = pd.DataFrame(
                        {
                            "mean_bg": grouped_by_time_since_site_change["bg"].mean(),
                            "std_bg": grouped_by_time_since_site_change["bg"].std(),
                            "n": grouped_by_time_since_site_change["bg"].count(),
                        }
                    )
                    # Don't plot points where we have much less data than usual (e.g. after 3 days)
                    site_change_summary = site_change_summary.loc[
                        site_change_summary["n"]
                        > site_change_summary["n"].median() / 10
                    ]
                    fig = px.line(
                        site_change_summary,
                        y="mean_bg",
                        markers=True,
                        error_y="std_bg",
                    )
                    fig.update_layout(
                        xaxis_title="Hours since site change",
                        yaxis_title="Mean +/- std BG (mg/dL)",
                    )
                    fig.update_xaxes(
                        dtick=bin_hours,
                        tickformat="%I%p",
                        ticklabelmode="period",
                    )

                else:

                    # Plot vs time of day, with one trace per day past site change

                    all_bg_data["hour_of_day"] = all_bg_data["datetime"].dt.hour
                    all_bg_data["binned_hour_of_day"] = (
                        all_bg_data["hour_of_day"] // bin_hours
                    ) * bin_hours + bin_hours / 2
                    all_bg_data["site_change_day"] = all_bg_data[
                        "time_since_site_change"
                    ].dt.days.astype(pd.Int64Dtype())
                    grouped_by_time_and_site_change_day = all_bg_data.loc[
                        all_bg_data["eventType"] == "sgv"
                    ].groupby(["binned_hour_of_day", "site_change_day"])
                    site_change_summary_by_time = pd.DataFrame(
                        {
                            "mean_bg": grouped_by_time_and_site_change_day["bg"].mean(),
                            "std_bg": grouped_by_time_and_site_change_day["bg"].std(),
                            "n": grouped_by_time_and_site_change_day["bg"].count(),
                        }
                    ).reset_index()
                    # Don't plot average values where we have very little data
                    site_change_summary_by_time = site_change_summary_by_time.loc[
                        site_change_summary_by_time["n"]
                        > site_change_summary_by_time["n"].median() / 10
                    ]

                    all_bg_data["site_change_number"] = (
                        all_bg_data["eventType"] == "Site Change"
                    ).cumsum()

                    site_change_summary_by_time["binned_hour_label"] = pd.to_datetime(
                        pd.to_datetime(0)
                        + pd.to_timedelta(
                            site_change_summary_by_time["binned_hour_of_day"],
                            unit="hours",
                        )
                        # Add a small offset if showing error bars to make more readable
                        # + pd.to_timedelta(
                        #     (
                        #         site_change_summary_by_time["site_change_day"]
                        #         - site_change_summary_by_time["site_change_day"].median()
                        #     ).astype(float) * 10,
                        #     unit="minutes",
                        # )
                    )

                    fig = px.line(
                        site_change_summary_by_time,
                        x="binned_hour_label",
                        y="mean_bg",
                        color="site_change_day",
                        symbol="site_change_day",
                        line_dash="site_change_day",
                        markers=True,
                        labels={"site_change_day": "Days since<br>site change"},
                        # error_y="std_bg",
                    )
                    fig.update_layout(
                        xaxis_title="Hour of day",
                        yaxis_title="Mean BG (mg/dL)",
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.02,
                            bgcolor="rgb(255,255,255)",
                        ),
                    )
                    fig.update_xaxes(
                        tickformat="%-I%p",
                    )

            fig.update_traces(
                line=dict(width=2),
                marker_size=6,
                line_shape="spline",
            )
            fig.update_layout(
                margin=dict(l=40, r=40, t=40, b=40),
                height=400,
            )
            add_light_style(fig)
            return {
                "graph": fig,
            }
