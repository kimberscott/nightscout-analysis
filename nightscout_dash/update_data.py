import json

import numpy as np
import pandas as pd
from dash import (
    Dash,
    Input,
    Output,
    State,
    callback,
    no_update,
)
from demo import fetch_nightscout_data

from datetime import date
import datetime


@callback(
    output={
        "bg_data": Output(component_id="all-bg-data", component_property="data"),
        "subset_data": Output(component_id="subset-bg-data", component_property="data"),
        "already_loaded_date_strs": Output(
            component_id="already-loaded-dates",
            component_property="data",
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
    },
)
def load_nightscout_data(
    submit_button,
    start_date_str,
    end_date_str,
    already_loaded_date_strs,
    bg_data,
):
    # TODO: if start date or end date are None, gentle error

    # First find out what range of data we actually need to fetch from the server, if any
    requested_dates = pd.date_range(
        start=date.fromisoformat(start_date_str),
        end=date.fromisoformat(end_date_str),
    )

    # If we don't already have data loaded, just load this start-end date
    if already_loaded_date_strs is None:
        all_bg_data = fetch_nightscout_data(
            date.fromisoformat(start_date_str),
            date.fromisoformat(end_date_str) + datetime.timedelta(days=1),
        )
        already_loaded_dates = requested_dates
        updated_bg_data = all_bg_data.to_json(orient="split")
    else:
        all_bg_data = pd.read_json(bg_data, orient="split")
        # Check what dates we have already
        already_loaded_dates = pd.read_json(already_loaded_date_strs, typ="series")
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
            for (i_start, i_end) in zip(segment_start_indices, segment_end_indices):
                new_bg_dataframes.append(
                    fetch_nightscout_data(
                        new_dates[i_start],
                        new_dates[i_end] + datetime.timedelta(days=1),
                    )
                )
            all_bg_data = pd.concat(new_bg_dataframes)
            updated_bg_data = all_bg_data.to_json(orient="split")

            already_loaded_dates = pd.concat(
                [already_loaded_dates, pd.Series(new_dates)]
            )
        else:
            updated_bg_data = no_update

    all_bg_data["date"] = pd.to_datetime(all_bg_data["date"]).dt.date
    subset_data = all_bg_data[
        (all_bg_data["date"] >= date.fromisoformat(start_date_str))
        & (all_bg_data["date"] <= date.fromisoformat(end_date_str))
    ]

    return {
        "bg_data": updated_bg_data,
        "subset_data": subset_data.to_json(orient="split"),
        "already_loaded_date_strs": json.dumps(
            already_loaded_dates.astype("string").to_list()
        ),
    }
