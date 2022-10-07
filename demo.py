from dotenv import load_dotenv
import os
import datetime
import math
import tzlocal

from nightscout_loader import (
    fetch_nightscout_data,
)

load_dotenv()

NIGHTSCOUT_URL = os.getenv("NIGHTSCOUT_URL")
ENTRIES_ENDPOINT = NIGHTSCOUT_URL + "entries.json"
TREATMENTS_ENDPOINT = NIGHTSCOUT_URL + "treatments.json"
PROFILE_ENDPOINT = NIGHTSCOUT_URL + "profile.json"


if __name__ == "__main__":

    dt = datetime.timedelta(days=13)
    now = datetime.datetime.now()
    bg = fetch_nightscout_data(
        start_date=now - dt, local_timezone_name=tzlocal.get_localzone_name()
    )

    # Display likely fasting blood sugar measurements

    fasting_smbg = bg.loc[
        (bg["eventType"] == "mbg")
        & (datetime.time(hour=6) < bg["time"])
        & (bg["time"] < datetime.time(hour=12))
    ]
    print("Fasting blood sugar measurements")
    print(fasting_smbg[["date", "time_str", "bg"]].reset_index(drop=True))

    # Display mean and standard deviation
    sgv = bg.loc[(bg["bg"] > 0) & (bg["eventType"] == "sgv")]
    n_bg = len(sgv)
    print(f"CGM summary data ({n_bg} measurements):")
    print(f'\tMean: {sgv["bg"].mean():.1f} mg/dL')
    print(f'\tStd: {sgv["bg"].std():.1f} mg/dL')

    # Display what percentage of values are in various ranges
    categories = [
        (0, 54, "< 1%"),
        (0, 63, "< 4%"),
        (63, 130, ""),
        (63, 140, "> 70%"),
        (130, math.inf, ""),
        (140, math.inf, "< 25%"),
    ]
    for (lo, hi, target) in categories:
        target_str = f"   (target: {target})" if target else ""
        print(
            f'\t[{lo} - {hi}): {(sum((sgv["bg"] >= lo) & (sgv["bg"] < hi)) / n_bg * 100):.1f}%{target_str}'
        )

    # TODO: plot overall distribution

    # TODO: make a table of treatments, ratios, and "outcomes" grouped by likely meal

    # TODO: make a table of TDD

    # TODO: make heatmap or other stacked plot of day x hour

    # TODO: make annotated daily plot

    # TODO: align on doses, look at meal trajectories?

    # TODO: use annotations on nightscout to discount pressure lows etc
