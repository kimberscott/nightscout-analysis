import pandas as pd
from nightscout_loader import (
    fetch_nightscout_data,
    fetch_profile_data,
    get_basal_per_hour,
)

from datetime import date
import datetime
import tzlocal

import plotly.io as pio

pio.renderers.default = "browser"

import string
import random
import math
import plotly.express as px
import plotly.graph_objects as go

start_date = date.fromisoformat("2022-09-01")
end_date = date.fromisoformat("2022-09-30")
local_timezone_name = tzlocal.get_localzone_name()


all_bg_data = fetch_nightscout_data(start_date, end_date, local_timezone_name)
profiles = fetch_profile_data(local_timezone_name)

#%%

site_changes = all_bg_data.loc[
    all_bg_data["eventType"] == "Site Change", ["datetime"]
].rename(columns={"datetime": "site_change_datetime"})

all_bg_data["site_change_number"] = (all_bg_data["eventType"] == "Site Change").cumsum()

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
    all_bg_data["time_since_site_change"] / 12
).dt.floor("H") * 12
all_bg_data["hours_since_site_change"] = (
    all_bg_data["hours_since_site_change"].dt.seconds / 60 / 60
)

grouped_by_time_since_site_change = all_bg_data.loc[
    all_bg_data["eventType"] == "sgv"
].groupby("hours_since_site_change")

site_change_summary = pd.DataFrame(
    {
        "mean_bg": grouped_by_time_since_site_change["bg"].mean(),
        "std_bg": grouped_by_time_since_site_change["bg"].std(),
        "n": grouped_by_time_since_site_change["bg"].count(),
    }
)
# site_change_summary["hours"] = grouped_by_time_since_site_change[]

#%%
fig = px.line(
    site_change_summary,
    # x="time_label",
    y="mean_bg",
    # color="date",
    # symbol="date",
    # line_dash="date",
    markers=True,
)
# fig.update_traces(
#     line=dict(width=1),
#     legendgroup="Individual day basal rates",
#     legendrank=1001,
#     legendgrouptitle_text="Individual date",
#     marker_size=5,
#     line_shape="spline",
# )
#
#
# # Mean actual basal
# fig.add_trace(
#     go.Scatter(
#         x=hourly_summary.index,
#         y=hourly_summary["mean"],
#         mode="lines",
#         name="Mean actual rate",
#         line_color="black",
#         line_shape="hvh",
#         line_width=3,
#     )
# )
#
# fig.update_layout(
#     margin=dict(l=40, r=40, t=40, b=40),
#     height=400,
#     title="Basal rates",
#     xaxis_title="Time of day",
#     yaxis_title="u/hr",
#     legend_title="Summary",
# )
fig.update_xaxes(
    dtick=60 * 60 * 1000000000,
    tickformat="%I%p",
    ticklabelmode="period",
)
# fig.update_yaxes(
#     range=[
#         -0.05,
#         math.ceil(basals_per_hour["avg_basal"].max() * 2) / 2.0,
#     ],
# )
fig.show()
