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

#%%

table_data = [
    {"lower": None, "upper": 70, "label": "low"},
    {"lower": 70, "upper": 180, "label": "in range"},
    {"lower": 180, "upper": None, "label": "high"},
]

cgm_data = all_bg_data.loc[all_bg_data["eventType"] == "sgv"]
cgm_by_date = cgm_data[["bg", "date"]].groupby("date")

for row in table_data:
    row["lower"] = float(row["lower"] or 0)
    row["upper"] = float(row["upper"] or np.inf)

summary = pd.DataFrame(
    {
        row["label"]: cgm_by_date["bg"].aggregate(
            lambda x: sum((x <= row["upper"]) & (x > row["lower"])) / len(x)
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
