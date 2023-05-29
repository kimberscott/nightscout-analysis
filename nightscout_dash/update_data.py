from dash import (
    html,
    dcc,
    Input,
    Output,
    State,
    callback,
    no_update,
)
import dash_bootstrap_components as dbc
import datetime
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os
import requests.exceptions
import tzlocal
import zoneinfo
from urllib.parse import urlparse, urlsplit


from nightscout_dash.data_utils import (
    bg_data_json_to_df,
    profile_json_to_df,
    AnalysisComponent,
)
from nightscout_dash.plot_utils import add_light_style
from nightscout_loader import (
    fetch_nightscout_data,
    fetch_profile_data,
)


class DataUpdater(AnalysisComponent):
    @property
    def layout_contents(self):
        return [
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

    @staticmethod
    def register_callbacks():
        @callback(
            output={
                "bg_data": Output(
                    component_id="all-bg-data", component_property="data"
                ),
                "subset_data": Output(
                    component_id="subset-bg-data", component_property="data"
                ),
                "already_loaded_date_strs": Output(
                    component_id="already-loaded-dates",
                    component_property="data",
                ),
                "profile_data": Output(
                    component_id="profile-data", component_property="data"
                ),
                "loaded_nightscout_url": Output(
                    component_id="loaded-nightscout-url", component_property="data"
                ),
                "nightscout_error_open": Output(
                    component_id="nightscout-error",
                    component_property="is_open",
                ),
            },
            inputs={
                "submit_button": Input(
                    component_id="submit-button", component_property="n_clicks"
                ),
                "start_date_str": State(
                    component_id="data-date-range", component_property="start_date"
                ),
                "end_date_str": State(
                    component_id="data-date-range", component_property="end_date"
                ),
                "already_loaded_date_strs": State(
                    component_id="already-loaded-dates", component_property="data"
                ),
                "bg_data": State(component_id="all-bg-data", component_property="data"),
                "profile_json": State(
                    component_id="profile-data", component_property="data"
                ),
                "timezone_name": State(
                    component_id="timezone-name", component_property="value"
                ),
                "nightscout_url": State(
                    component_id="nightscout-url", component_property="value"
                ),
                "loaded_nightscout_url": State(
                    component_id="loaded-nightscout-url", component_property="data"
                ),
            },
        )
        def load_nightscout_data(
            submit_button,
            start_date_str,
            end_date_str,
            already_loaded_date_strs,
            bg_data,
            profile_json,
            timezone_name: str,
            nightscout_url: str,
            loaded_nightscout_url: str,
        ):
            # TODO: if start date or end date are None, gentle error

            # Ensure that the URL starts with http:// or https://
            parsed_url = urlsplit(nightscout_url)
            if not parsed_url.scheme:
                nightscout_url = "https://" + nightscout_url

            # Extract the root URL and remove any trailing slash so we don't treat it as an actual change if a
            # trailing slash is added/removed
            parsed_url = urlparse(nightscout_url)
            nightscout_url = f"{parsed_url.scheme}://{parsed_url.netloc}".rstrip("/")

            # First find out what range of data we actually need to fetch from the server, if any
            requested_dates = pd.date_range(
                start=datetime.date.fromisoformat(start_date_str),
                end=datetime.date.fromisoformat(end_date_str),
            )

            # If we don't already have data loaded, just load this start-end date
            if (already_loaded_date_strs is None) or (
                loaded_nightscout_url != nightscout_url
            ):

                try:
                    all_bg_data = fetch_nightscout_data(
                        nightscout_url,
                        datetime.date.fromisoformat(start_date_str),
                        datetime.date.fromisoformat(end_date_str)
                        + datetime.timedelta(days=1),
                        local_timezone_name=timezone_name,
                    )
                    profiles = fetch_profile_data(nightscout_url, timezone_name)
                except requests.exceptions.JSONDecodeError:
                    return {
                        "bg_data": no_update,
                        "subset_data": no_update,
                        "already_loaded_date_strs": no_update,
                        "profile_data": no_update,
                        "loaded_nightscout_url": no_update,
                        "nightscout_error_open": True,
                    }
                already_loaded_dates = requested_dates
                updated_bg_data = all_bg_data.to_json(orient="split", date_unit="ns")

            else:
                all_bg_data = bg_data_json_to_df(bg_data, timezone_name)
                profiles = profile_json_to_df(profile_json, timezone_name)

                # Check what dates we have already
                already_loaded_dates = pd.read_json(
                    already_loaded_date_strs, typ="series"
                )
                # See which requested dates are new
                new_dates = set(requested_dates) - set(already_loaded_dates)
                # TODO: If today is requested, always load it again.

                if len(new_dates):
                    # Break into contiguous segments
                    new_dates = sorted(list(new_dates))
                    jump_start_indices = (
                        np.flatnonzero(
                            (np.array(new_dates[1:]) - np.array(new_dates[0:-1]))
                            > datetime.timedelta(days=1)
                        )
                        + 1
                    )
                    segment_start_indices = np.insert(jump_start_indices, 0, 0)
                    segment_end_indices = np.append(
                        jump_start_indices - 1, [len(new_dates) - 1]
                    )

                    new_bg_dataframes = [all_bg_data]
                    try:
                        for (i_start, i_end) in zip(
                            segment_start_indices, segment_end_indices
                        ):
                            new_bg_dataframes.append(
                                fetch_nightscout_data(
                                    nightscout_url,
                                    new_dates[i_start],
                                    new_dates[i_end] + datetime.timedelta(days=1),
                                    local_timezone_name=timezone_name,
                                )
                            )
                    except requests.exceptions.JSONDecodeError:
                        return {
                            "bg_data": no_update,
                            "subset_data": no_update,
                            "already_loaded_date_strs": no_update,
                            "profile_data": no_update,
                            "loaded_nightscout_url": no_update,
                            "nightscout_error_open": True,
                        }
                    all_bg_data = pd.concat(new_bg_dataframes)
                    all_bg_data.sort_values(by="datetime", inplace=True)
                    updated_bg_data = all_bg_data.to_json(
                        orient="split", date_unit="ns"
                    )

                    already_loaded_dates = pd.concat(
                        [already_loaded_dates, pd.Series(new_dates)]
                    )
                else:
                    updated_bg_data = no_update

            all_bg_data["date"] = pd.to_datetime(all_bg_data["date"]).dt.date
            subset_data = all_bg_data[
                (all_bg_data["date"] >= datetime.date.fromisoformat(start_date_str))
                & (all_bg_data["date"] <= datetime.date.fromisoformat(end_date_str))
            ]

            return {
                "bg_data": updated_bg_data,
                "subset_data": subset_data.to_json(orient="split", date_unit="ns"),
                "already_loaded_date_strs": json.dumps(
                    already_loaded_dates.astype("string").to_list()
                ),
                "profile_data": profiles.to_json(orient="split", date_unit="ns"),
                "loaded_nightscout_url": nightscout_url,
                "nightscout_error_open": False,
            }

        @callback(
            output={
                "graph": Output("loaded-data-graph", "figure"),
            },
            inputs={
                "bg_data": Input("all-bg-data", "data"),
                "timezone_name": State(
                    component_id="timezone-name", component_property="value"
                ),
            },
        )
        def update_graph(bg_data, timezone_name):
            if not bg_data:
                figure = go.Figure()
            else:
                df = bg_data_json_to_df(bg_data, timezone_name)

                # Downsample sgv events
                df = df.loc[
                    (df["eventType"] == "mbg")
                    | ((df["eventType"] == "sgv") & (df.index % 10 == 0))
                ]

                cgm_vs_mbg = (df["eventType"] == "sgv") * 0 + (
                    df["eventType"] == "mbg"
                ) * 1

                figure = go.Figure(
                    data=go.Scatter(
                        x=df["datetime"],
                        y=df["bg"],
                        mode="markers",
                        marker=dict(
                            size=2 + (cgm_vs_mbg * 10),
                            color=df["datetime"].dt.hour,
                            line_color=df["datetime"].dt.hour,
                            colorscale="hsv",
                            showscale=True,
                            # circle and cross
                            symbol=cgm_vs_mbg
                            * 4,  # df["eventType"].astype("category").cat.codes,
                            colorbar=dict(title="Hour"),
                            line_width=0,
                        ),
                    ),
                )
            figure.update_layout(
                margin=dict(l=40, r=40, t=80, b=40),
                height=240,
                title="All loaded data<br><sub>To confirm availability of data (not intended for direct use in analysis)</sub>",
                xaxis_title="Date",
                yaxis_title="mg/dL",
            )
            add_light_style(figure)
            return {
                "graph": figure,
            }

        @callback(
            output={
                "title": Output("subset-data-header", "children"),
            },
            inputs={
                "submit_button": Input(
                    component_id="submit-button", component_property="n_clicks"
                ),
                "start_date_str": State(
                    component_id="data-date-range", component_property="start_date"
                ),
                "end_date_str": State(
                    component_id="data-date-range", component_property="end_date"
                ),
            },
        )
        def update_header(submit_button, start_date_str, end_date_str):

            # TODO: store info in URL query params
            # import urllib.parse

            # parsed_url = urllib.parse.urlparse(flask.request.referrer)
            # parsed_query = urllib.parse.parse_qs(parsed_url.query)

            start_date = datetime.date.fromisoformat(start_date_str)
            end_date = datetime.date.fromisoformat(end_date_str)
            if start_date.year == end_date.year:
                date_description = (
                    f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
                )
            else:
                date_description = f"{start_date.strftime('%b %d %y')} - {end_date.strftime('%b %d %y')}"

            n_days = (end_date - start_date).days + 1  # inclusive of endpoints
            header_str = f"{date_description} ({n_days} days)"
            return {
                "title": header_str,
            }
