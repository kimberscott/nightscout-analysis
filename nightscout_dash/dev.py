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
import numpy as np

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

#%% Distinct lows

# Working definition:
# Interval with >1 data point <=70 followed by >=5 total (not necessarily consecutive) data points >80
low_threshold = 70
recovered_threshold = 80
n_recovered_pts_between_lows = 5

cgm_data = all_bg_data.loc[all_bg_data["eventType"] == "sgv"]

cgm_data["recovered_point_count"] = (cgm_data["bg"] > recovered_threshold).cumsum()
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

# Get number per day
cgm_by_date = cgm_data.groupby("date")
summary = pd.DataFrame({"distinct_lows": cgm_by_date["is_distinct_low"].sum()})
summary.reset_index(inplace=True)  # so we have date column

#%%

fig = px.line(
    summary,
    x="date",
    y="distinct_lows",
    labels={
        "distinct_lows": "# separate lows",
        "date": "Date",
    },
    line_shape="spline",
    markers=True,
)
fig.update_layout(
    margin=dict(l=40, r=40, t=40, b=40),
    height=400,
)
add_light_style(fig)

fig.show()

#%%

fig = px.area(
    summary_long,
    x="date",
    y="fraction",
    color="range",
    labels={"range": "Range", "date": "Date", "fraction": "Fraction of day"},
    line_shape="spline",
)
fig.update_layout(
    margin=dict(l=40, r=40, t=40, b=40),
    height=400,
)
if not summary_long.empty:
    fig.update_yaxes(range=[0, summary_long.groupby("date")["fraction"].sum().max()])
add_light_style(fig)

fig.show()
