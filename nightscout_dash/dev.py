# Load the data

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
from demo import fetch_nightscout_data, fetch_profile_data

from datetime import date
import datetime
import tzlocal


import requests
from demo import PROFILE_ENDPOINT


def fetch_profile_data() -> pd.DataFrame:
    profile_list = requests.get(
        PROFILE_ENDPOINT, params={}, headers={"accept": "application/json"}
    ).json()

    basal_list = [
        profile | basal
        for profile in profile_list
        for basal in profile["store"][profile["defaultProfile"]]["basal"]
    ]
    basals = pd.DataFrame.from_records(basal_list)[
        ["defaultProfile", "startDate", "time", "value", "timeAsSeconds", "_id"]
    ]
    basals.rename(columns={"defaultProfile": "name", "_id": "profile_id"}, inplace=True)

    basals["startDate"] = pd.to_datetime(basals["startDate"], utc=True).dt.tz_convert(
        tzlocal.get_localzone_name()
    )

    return basals.sort_values(by=["startDate", "timeAsSeconds"])


def get_scheduled_basal(profiles, timestamp):
    # We want the last *profile* before this timestamp, and
    # from that one, we want the last *time interval* before this timestamp
    # We assume the profiles are sorted by effective date, then time in seconds.
    timestamp = pd.to_datetime(timestamp)
    applicable_profile_rows = profiles.loc[
        (profiles["startDate"] <= timestamp)
        & (
            profiles["timeAsSeconds"]
            <= timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second
        )
    ]
    return applicable_profile_rows.iloc[-1]["value"]


#%%

start_date = date.fromisoformat("2022-09-01")
end_date = date.fromisoformat("2022-09-07")
start_datetime = pd.to_datetime(start_date, utc=False).tz_localize(
    tzlocal.get_localzone_name()
)
end_datetime = pd.to_datetime(
    end_date + datetime.timedelta(days=1), utc=False
).tz_localize(tzlocal.get_localzone_name())

all_bg_data = fetch_nightscout_data(start_date, end_date)

profiles = fetch_profile_data()

basal_rates = all_bg_data.loc[
    ~pd.isna(all_bg_data["duration"]),
    [
        "datetime",
        "duration",
        "absolute",
        "reason",
    ],
].sort_values(by="datetime")
basal_rates["expiration"] = basal_rates["datetime"] + basal_rates["duration"].apply(
    lambda x: datetime.timedelta(minutes=x)
)
# Find the cases where the expiration is before the next entry, and insert profile values at the expiration time
temp_basal_expirations = [start_datetime] + list(
    basal_rates["expiration"].iloc[
        list(
            np.flatnonzero(
                basal_rates["expiration"].iloc[:-1].values
                < basal_rates["datetime"].iloc[1:].values
            )
        )
        + [-1]
    ]
)
regularly_scheduled_at_expiration = pd.DataFrame(
    data={
        "datetime": temp_basal_expirations,
        "absolute": [
            get_scheduled_basal(profiles, dts) for dts in temp_basal_expirations
        ],
    }
)


#%%

# Find all the times where the regularly-scheduled basal profile would *change* during this interval
profiles["profile_number"] = profiles.groupby("profile_id").ngroup()
profiles["next_profile_number"] = profiles["profile_number"] + 1
profile_start_times = profiles[["profile_number", "startDate"]].drop_duplicates()

profiles = pd.merge(
    left=profiles,
    right=profile_start_times,
    how="left",
    left_on="next_profile_number",
    right_on="profile_number",
    suffixes=[None, "_next"],
)

profile_repeats = []
for profile_num in profiles["profile_number"].unique():
    print(profile_num)
    this_profile = profiles.loc[profiles["profile_number"] == profile_num]
    range_start = this_profile.iloc[0]["startDate"].date()
    range_end = (
        end_date
        if pd.isna(this_profile.iloc[0]["profile_number_next"])
        else this_profile.iloc[0]["startDate_next"].date()
    )
    date_range = pd.date_range(
        start=max([range_start, start_date]),
        end=range_end,
    )
    profile_repeats.append(
        pd.merge(
            left=this_profile,
            right=pd.DataFrame(data={"date": date_range}),
            how="cross",
        )
    )
basal_change_times = pd.concat(profile_repeats)
# Filter out rows from before the current profile actually took effect & after the next one did

basal_change_times["datetime"] = (
    basal_change_times["date"] + pd.to_timedelta(basal_change_times["time"] + ":00")
).dt.tz_localize(
    tz=tzlocal.get_localzone_name(), ambiguous="NaT", nonexistent="shift_forward"
)
basal_change_times = basal_change_times.loc[
    (basal_change_times["datetime"] >= basal_change_times["startDate"])
    & (
        (basal_change_times["datetime"] < basal_change_times["startDate_next"])
        | pd.isnull(basal_change_times["startDate_next"])
    )
    & (basal_change_times["datetime"].dt.date <= end_date)
]
# Also throw in a row any time the profile itself changed during the interval, and a row
# at the end of the interval to make sure we sample all the way to the end
profile_change_times = pd.Series(profiles["startDate"].unique())
profile_change_times = profile_change_times.loc[
    (profile_change_times.dt.date >= start_date)
    & (profile_change_times.dt.date <= end_date)
]
profile_change_times = pd.concat(
    [
        profile_change_times,
        pd.Series([end_datetime]),
    ]
)
basal_change_times = pd.concat(
    [
        basal_change_times[["datetime", "value"]],
        pd.DataFrame(
            {
                "datetime": profile_change_times,
                "value": profile_change_times.apply(
                    lambda x: get_scheduled_basal(profiles, x)
                ),
            }
        ),
    ]
).sort_values(["datetime"])

# Note: would potentially be easier just to sample every 5 min during periods where we
# dont have temp basals.

basal_change_times = pd.merge_asof(
    left=basal_change_times,
    right=basal_rates,
    left_on="datetime",
    right_on="datetime",
)
basal_change_times = basal_change_times.loc[
    ~(basal_change_times["datetime"] < basal_change_times["expiration"]),
    ["datetime", "value"],
].rename(columns={"value": "absolute"})
#%%
all_basal_rates = pd.concat(
    [
        basal_change_times,
        basal_rates,
        regularly_scheduled_at_expiration,
    ]
)[["datetime", "absolute"]].sort_values(by="datetime")

all_basal_rates["scheduled"] = list(
    all_basal_rates["datetime"].apply(lambda x: get_scheduled_basal(profiles, x))
)
all_basal_rates.drop_duplicates(inplace=True)
all_basal_rates.set_index("datetime", drop=True, inplace=True)


#%%

basals_per_min = all_basal_rates.asfreq("min", method="ffill")
basals_per_min = basals_per_min.loc[
    (basals_per_min.index >= start_datetime) & (basals_per_min.index <= end_datetime)
]

basals_np = basals_per_min["absolute"].to_numpy(dtype=float)
cum_basal = np.cumsum(basals_np)
cum_basal[60:] = cum_basal[60:] - cum_basal[:-60]
hourly_basals = cum_basal[59::60] / 60

basals_per_hour = basals_per_min.iloc[30:-30:60]
basals_per_hour["avg"] = hourly_basals

basals_per_hour["time_label"] = pd.to_datetime(
    start_datetime
    + (basals_per_hour.index - start_datetime) % datetime.timedelta(days=1)
)
basals_per_hour['date'] = basals_per_hour.index.date
#%%

import plotly.io as pio

pio.renderers.default = "browser"

import plotly.express as px

figure = px.line(
    basals_per_hour,
    x="time_label",
    y="avg",
    color="date",
    markers=True,
)
figure.update_layout(
    margin=dict(l=40, r=40, t=40, b=40),
    height=400,
    title="Basal rates",
    xaxis_title="Time",
    yaxis_title="u/hr",
)

figure.update_xaxes(
    dtick=60 * 60 * 1000,
    tickformat="%I%p",
    ticklabelmode="period",
    range=[
        basals_per_hour["time_label"].min() - datetime.timedelta(minutes=5),
        basals_per_hour["time_label"].max() + datetime.timedelta(minutes=5),
    ],
)
figure.update_traces(line=dict(width=3))
figure.show()
