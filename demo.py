import requests
from dotenv import load_dotenv
import os
import pandas as pd
import datetime
import tzlocal
import math

load_dotenv()

NIGHTSCOUT_URL = os.getenv("NIGHTSCOUT_URL")
ENTRIES_ENDPOINT = NIGHTSCOUT_URL + "entries.json"
TREATMENTS_ENDPOINT = NIGHTSCOUT_URL + "treatments.json"


def add_time_identifiers(df: pd.DataFrame, datetime_col_name: str) -> None:
    df["date"] = df[datetime_col_name].apply(
        lambda dt: None if dt is None else dt.date()
    )
    df["weekday"] = df[datetime_col_name].apply(
        lambda dt: None if dt is None else dt.strftime("%A")
    )
    df["weekday_number"] = df[datetime_col_name].apply(
        lambda dt: None if dt is None else dt.weekday()
    )
    df["time"] = df[datetime_col_name].apply(
        lambda dt: None if dt is None else dt.time()
    )
    df["time_str"] = df[datetime_col_name].apply(
        lambda dt: None if dt is None else dt.time().strftime("%H:%M")
    )


def fetch_nightscout_data(
    start_date: datetime.datetime = None, end_date: datetime.datetime = None
) -> pd.DataFrame:

    date_strs = (
        start_date.strftime("%Y-%m-%d") if start_date else None,
        end_date.strftime("%Y-%m-%d") if end_date else None,
    )

    bg_param_names = ("find[dateString][$gte]", "find[dateString][$lte]")
    treatment_param_names = ("find[created_at][$gte]", "find[created_at][$lte]")
    days_in_range = (end_date - start_date).days if None not in date_strs else 14

    # Fetch blood glucose entries
    bg_params = {
        param: date
        for param, date in zip(bg_param_names, date_strs)
        if date is not None
    }
    bg_params["count"] = 12 * 24 * days_in_range
    bg_list = requests.get(
        ENTRIES_ENDPOINT, params=bg_params, headers={"accept": "application/json"}
    ).json()
    bg = pd.DataFrame.from_records(bg_list)
    bg["datetime"] = pd.to_datetime(bg["date"], unit="ms", utc=True).dt.tz_convert(
        tzlocal.get_localzone_name()
    )
    # Limit columns

    bg_cols = ["datetime", "sgv", "mbg", "type"]

    # TODO: factor out into helper
    bg = bg[[col for col in bg_cols if col in bg]]
    for col in bg_cols:
        if col not in bg:
            bg[col] = None
    # Combine bg values into a single column - we already have provenance in type column
    bg["bg"] = bg["sgv"].fillna(bg["mbg"])
    bg.drop(columns=["sgv", "mbg"], inplace=True)

    # Fetch treatment entries
    treatment_params = {
        param: date
        for param, date in zip(treatment_param_names, date_strs)
        if date is not None
    }
    treatment_params["count"] = 50 * days_in_range
    treatments_list = requests.get(
        TREATMENTS_ENDPOINT,
        params=treatment_params,
        headers={"accept": "application/json"},
    ).json()
    treatments = pd.DataFrame.from_records(treatments_list)
    if "created_at" in treatments.columns:
        treatments["datetime"] = pd.to_datetime(treatments["created_at"]).dt.tz_convert(
            tzlocal.get_localzone_name()
        )
    # Limit columns
    treatment_cols = [
        "datetime",
        "carbs",
        "insulin",
        "eventType",
        "enteredBy",
        "notes",
        "entered by",
    ]
    treatments = treatments[[col for col in treatment_cols if col in treatments]]
    for col in treatment_cols:
        if col not in treatments:
            treatments[col] = None
    treatments["enteredBy"] = treatments["enteredBy"].fillna(treatments["entered by"])
    treatments.drop(columns=["entered by"], inplace=True)

    all_data = pd.concat([bg, treatments])
    all_data["eventType"] = all_data["type"].fillna(all_data["eventType"])
    all_data.drop(columns=["type"], inplace=True)
    all_data.sort_values(by="datetime", inplace=True)
    all_data.reset_index(drop=True, inplace=True)
    add_time_identifiers(all_data, "datetime")

    return all_data


if __name__ == "__main__":

    dt = datetime.timedelta(days=13)
    now = datetime.datetime.now()
    bg, treatments = fetch_nightscout_data(now - dt)

    # Display likely fasting blood sugar measurements

    fasting_smbg = bg.loc[
        (bg["type"] == "mbg")
        & (datetime.time(hour=6) < bg["time"])
        & (bg["time"] < datetime.time(hour=12))
    ]
    print("Fasting blood sugar measurements")
    print(fasting_smbg[["date", "time_str", "mbg"]].reset_index(drop=True))

    # Display mean and standard deviation
    n_bg = sum(bg["sgv"] > 0)
    print(f"CGM summary data ({n_bg} measurements):")
    print(f'\tMean: {bg["sgv"].mean():.1f} mg/dL')
    print(f'\tStd: {bg["sgv"].std():.1f} mg/dL')

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
            f'\t[{lo} - {hi}): {(sum((bg["sgv"] >= lo) & (bg["sgv"] < hi)) / n_bg * 100):.1f}%{target_str}'
        )

    # TODO: plot overall distribution

    # TODO: make a table of treatments, ratios, and "outcomes" grouped by likely meal

    # TODO: make a table of TDD

    # TODO: make heatmap or other stacked plot of day x hour

    # TODO: make annotated daily plot

    # TODO: align on doses, look at meal trajectories?

    # TODO: use annotations on nightscout to discount pressure lows etc
