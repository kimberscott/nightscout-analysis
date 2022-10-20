import pandas as pd
from nightscout_loader import (
    fetch_nightscout_data,
    fetch_profile_data,
)
from nightscout_dash.plot_utils import add_light_style

from datetime import date
import tzlocal

import os
import plotly.express as px

#%%
import plotly.io as pio

pio.renderers.default = "browser"

start_date = date.fromisoformat("2022-06-01")
end_date = date.fromisoformat("2022-09-30")
local_timezone_name = tzlocal.get_localzone_name()

from dotenv import load_dotenv

load_dotenv()
nightscout_url = os.getenv("NIGHTSCOUT_URL")


#%% Fetch data

all_bg_data = fetch_nightscout_data(
    nightscout_url, start_date, end_date, local_timezone_name
)
profiles = fetch_profile_data(nightscout_url, local_timezone_name)

site_changes = all_bg_data.loc[
    all_bg_data["eventType"] == "Site Change", ["datetime"]
].rename(columns={"datetime": "site_change_datetime"})
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

#%% Plot mean over entire course of site (~3 days on x axis)

bin_hours = 12

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
    site_change_summary["n"] > site_change_summary["n"].median() / 10
]

fig = px.line(
    site_change_summary,
    y="mean_bg",
    markers=True,
    error_y="std_bg",
)
fig.update_traces(
    line=dict(width=2),
    marker_size=site_change_summary["n"] / site_change_summary["n"].max() * 20,
    line_shape="spline",
)
fig.update_layout(
    margin=dict(l=40, r=40, t=40, b=40),
    height=400,
    title="BG over course of one site",
    xaxis_title="Hours since site change",
    yaxis_title="Mean +/- std BG (mg/dL)",
)
fig.update_xaxes(
    dtick=bin_hours,
    tickformat="%I%p",
    ticklabelmode="period",
)
add_light_style(fig)

fig.show()

#%% Plot vs time of day, with one trace per day past site change

bin_hours = 6

all_bg_data["hour_of_day"] = all_bg_data["datetime"].dt.hour
all_bg_data["binned_hour_of_day"] = (
    all_bg_data["hour_of_day"] // bin_hours
) * bin_hours + bin_hours / 2
all_bg_data["site_change_day"] = all_bg_data["time_since_site_change"].dt.days.astype(
    pd.Int64Dtype()
)
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
    site_change_summary_by_time["n"] > site_change_summary_by_time["n"].median() / 10
]

all_bg_data["site_change_number"] = (all_bg_data["eventType"] == "Site Change").cumsum()

site_change_summary_by_time["binned_hour_label"] = pd.to_datetime(
    pd.to_datetime(0)
    + pd.to_timedelta(site_change_summary_by_time["binned_hour_of_day"], unit="hours")
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
    margin=dict(l=40, r=40, t=40, b=40),
    height=400,
    width=800,
    title="BG on each day past site change",
    xaxis_title="Hour of day",
    yaxis_title="Mean BG (mg/dL)",
    legend=dict(
        yanchor="top", y=0.99, xanchor="left", x=0.02, bgcolor="rgb(255,255,255)"
    ),
)
fig.update_traces(
    line=dict(width=2),
    marker_size=6,
    line_shape="spline",
)
fig.update_xaxes(
    tickformat="%-I%p",
)
add_light_style(fig)
fig.show()
