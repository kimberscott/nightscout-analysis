import numpy as np
import requests

import pandas as pd
import datetime
from urllib.parse import urljoin


def get_entries_endpoint(nightscout_url):
    return urljoin(nightscout_url, "api/v1/entries.json")


def get_treatments_endpoint(nightscout_url):
    return urljoin(nightscout_url, "api/v1/treatments.json")


def get_profile_endpoint(nightscout_url):
    return urljoin(nightscout_url, "api/v1/profile.json")


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
    nightscout_url: str,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    local_timezone_name: str = "UTC",
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
        get_entries_endpoint(nightscout_url),
        params=bg_params,
        headers={"accept": "application/json"},
    ).json()
    bg = pd.DataFrame.from_records(bg_list)
    bg["datetime"] = pd.to_datetime(bg["date"], unit="ms", utc=True).dt.tz_convert(
        local_timezone_name
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
    treatment_params["count"] = 300 * days_in_range
    treatments_list = requests.get(
        get_treatments_endpoint(nightscout_url),
        params=treatment_params,
        headers={"accept": "application/json"},
    ).json()
    treatments = pd.DataFrame.from_records(treatments_list)
    if "created_at" in treatments.columns:
        treatments["datetime"] = pd.to_datetime(treatments["created_at"]).dt.tz_convert(
            local_timezone_name
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
        "duration",
        "absolute",
        "reason",
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


def fetch_profile_data(nightscout_url: str, local_timezone_name: str) -> pd.DataFrame:
    """
    Retrieves ALL profiles stored in Nightscout.

    :param nightscout_url: Base URL of Nightscout site
    :param local_timezone_name: Timezone name e.g. 'America/New_York'

    :return: Pandas DataFrame with one row per basal rate, and columns:
       * name (name of the profile, not necessarily unique)
       * profile_id (unique ID of profile)
       * profile_start_datetime (when profile took effect)
       * basal_start_time_seconds (time in seconds since midnight when THIS basal rate for this profile takes effect)
       * units_per_hour_scheduled (basal rate)
       Rows are sorted by profile_start_datetime, then basal_start_time_seconds.

    """
    profile_list = requests.get(
        get_profile_endpoint(nightscout_url),
        params={},
        headers={"accept": "application/json"},
    ).json()
    basal_list = [
        profile | basal_rates
        for profile in profile_list
        for basal_rates in profile["store"][profile["defaultProfile"]]["basal"]
    ]
    basals = pd.DataFrame.from_records(basal_list)[
        ["defaultProfile", "startDate", "value", "timeAsSeconds", "_id"]
    ]
    basals.rename(
        columns={
            "defaultProfile": "name",
            "_id": "profile_id",
            "startDate": "profile_start_datetime",
            "timeAsSeconds": "basal_start_time_seconds",
            "value": "units_per_hour_scheduled",
        },
        inplace=True,
    )
    # Profile start times are in UTC; convert to timezone-aware datetimes in local timezone.
    basals["profile_start_datetime"] = pd.to_datetime(
        basals["profile_start_datetime"], utc=True
    ).dt.tz_convert(local_timezone_name)
    return basals.sort_values(by=["profile_start_datetime", "basal_start_time_seconds"])


def get_scheduled_basal(profiles: pd.DataFrame, timestamp: pd.Timestamp) -> float:
    """
    Given a dataframe of scheduled basal rates from multiple profiles, find the rate that was active at a given time
    based on (a) when each profile took effect and (b) when the scheduled basal rates change.

    :param profiles: Pandas dataframe as returned by fetch_profile_date, with at least columns profile_start_datetime
        and basal_start_time_seconds
    :param timestamp: Timestamp or other type that can be converted by pd.to_datetime. This will be compared directly
        to the profile_start_datetime values, so should be tz-aware.

    :return: Basal rate scheduled at timestamp according to profiles, in u/hr
    """

    # We want the last *profile* before this timestamp, and
    # from that one, we want the last *time interval* before this timestamp
    # We assume the profiles are sorted by effective date, then time in seconds.
    timestamp = pd.to_datetime(timestamp)
    applicable_profile_rows = profiles.loc[
        (profiles["profile_start_datetime"] <= timestamp)
        & (
            profiles["basal_start_time_seconds"]
            <= timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second
        )
    ]
    return applicable_profile_rows.iloc[-1]["units_per_hour_scheduled"]


def get_basal_per_hour(
    all_bg_data: pd.DataFrame,
    profiles: pd.DataFrame,
    start_date,
    end_date,
    timezone_name,
) -> pd.DataFrame:
    """

    :param all_bg_data: DataFrame with temp basal and bolus data for time period of interest. Should have columns:
        * duration (float, in minutes - relevant for temp basals)
        * datetime (time of event)
        * absolute (actual basal rate for temp basals)
        * reason (reason for temp basal)
    :param profiles: Pandas dataframe as returned by fetch_profile_date, with at least columns profile_start_datetime,
        profile_id, and basal_start_time_seconds
    :return:
    """

    start_datetime = pd.to_datetime(start_date, utc=False).tz_localize(timezone_name)
    end_datetime = pd.to_datetime(
        end_date + datetime.timedelta(days=1), utc=False
    ).tz_localize(timezone_name)

    # First find all times a temp basal was set, and add a column to show when that temp basal ended
    temp_basal_rates = all_bg_data.loc[
        (~pd.isna(all_bg_data["duration"])) & (~pd.isna(all_bg_data["absolute"])),
        [
            "datetime",
            "duration",
            "absolute",
            "reason",
        ],
    ].sort_values(by="datetime")
    temp_basal_rates["expiration"] = temp_basal_rates["datetime"] + temp_basal_rates[
        "duration"
    ].apply(lambda x: datetime.timedelta(minutes=x))

    # Find the cases where the expiration is before the next entry, and insert profile values at the expiration time
    temp_basal_expirations = [start_datetime]
    if len(temp_basal_rates):
        temp_basal_expirations += list(
            temp_basal_rates["expiration"].iloc[
                list(
                    np.flatnonzero(
                        temp_basal_rates["expiration"].iloc[:-1].values
                        < temp_basal_rates["datetime"].iloc[1:].values
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

    # Find all the times when the regularly-scheduled basal profile would *change* during this interval

    # For each profile, get the datetime where the *next* profile will take effect (to aid in removing entries that
    # are superceded by that next profile!
    profiles["profile_number"] = profiles.groupby("profile_id").ngroup()
    profiles["next_profile_number"] = profiles["profile_number"] + 1
    profile_start_times = profiles[
        ["profile_number", "profile_start_datetime"]
    ].drop_duplicates()
    profiles = pd.merge(
        left=profiles,
        right=profile_start_times,
        how="left",
        left_on="next_profile_number",
        right_on="profile_number",
        suffixes=[None, "_next"],
    )

    # Make a dataframe that has start datetimes of each basal rate, rather than start datetime for the profile plus
    # start *time*s of each rate. E.g. expand "1u from 0-3 and 2u from 3-24, starting 9/1/2022" to "1u from 0-3
    # 9/1/2022, 2u from 3-24 9/1/2022, 1u from 0-3 9/2/2022, ..."
    profile_repeats = []
    for profile_num in profiles["profile_number"].unique():
        this_profile = profiles.loc[profiles["profile_number"] == profile_num]
        range_start = this_profile.iloc[0]["profile_start_datetime"].date()
        range_end = (
            end_date
            if pd.isna(this_profile.iloc[0]["profile_number_next"])
            else this_profile.iloc[0]["profile_start_datetime_next"].date()
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
    basal_change_times["datetime"] = (
        basal_change_times["date"]
        + pd.to_timedelta(basal_change_times["basal_start_time_seconds"], unit="s")
    ).dt.tz_localize(tz=timezone_name, ambiguous="NaT", nonexistent="shift_forward")

    # Filter out rows from before the current profile actually took effect & after the next one did
    basal_change_times = basal_change_times.loc[
        (basal_change_times["datetime"] >= basal_change_times["profile_start_datetime"])
        & (
            (
                basal_change_times["datetime"]
                < basal_change_times["profile_start_datetime_next"]
            )
            | pd.isnull(basal_change_times["profile_start_datetime_next"])
        )
        & (basal_change_times["datetime"].dt.date <= end_date)
    ]

    # Also throw in a row any time the profile itself changed during the interval, and a row
    # at the end of the interval to make sure we sample all the way to the end
    profile_change_times = pd.Series(profiles["profile_start_datetime"].unique())
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
            basal_change_times[["datetime", "units_per_hour_scheduled"]],
            pd.DataFrame(
                {
                    "datetime": profile_change_times,
                    "units_per_hour_scheduled": profile_change_times.apply(
                        lambda x: get_scheduled_basal(profiles, x)
                    ),
                }
            ),
        ]
    ).sort_values(["datetime"])
    # Merge with temp basals to check for any cases where the temp basal would supercede the change. (Note we've already
    # covered the case where the temp basal expires and reverts back to the regularly-scheduled basal.)
    basal_change_times_outside_of_temps = pd.merge_asof(
        left=basal_change_times,
        right=temp_basal_rates,
        left_on="datetime",
        right_on="datetime",
    )
    basal_change_times_outside_of_temps = basal_change_times_outside_of_temps.loc[
        ~(
            basal_change_times_outside_of_temps["datetime"]
            < basal_change_times_outside_of_temps["expiration"]
        ),
        ["datetime", "units_per_hour_scheduled"],
    ].rename(columns={"units_per_hour_scheduled": "absolute"})

    all_basal_rates = pd.concat(
        [
            basal_change_times_outside_of_temps,
            temp_basal_rates,
            regularly_scheduled_at_expiration,
        ]
    )[["datetime", "absolute"]].sort_values(by="datetime")
    all_basal_rates = pd.merge_asof(
        left=all_basal_rates,
        right=basal_change_times,
        left_on="datetime",
        right_on="datetime",
    ).rename(columns={"units_per_hour_scheduled": "scheduled"})

    # Make sure to drop duplicates while datetime is still part of the row!
    all_basal_rates.drop_duplicates(subset=["datetime"], inplace=True)
    all_basal_rates.set_index("datetime", drop=True, inplace=True)

    # Sample in time domain instead of storing only change points
    basals_per_min = all_basal_rates.asfreq("min", method="ffill")
    basals_per_min = basals_per_min.loc[
        (basals_per_min.index >= start_datetime)
        & (basals_per_min.index <= end_datetime)
    ]
    basals_per_min["index"] = basals_per_min.index
    # Add in auto-boluses to basal rates
    auto_boluses = all_bg_data.loc[
        (~pd.isna(all_bg_data["insulin"]))
        & (all_bg_data["notes"] == "Automatic Bolus/Correction")
        & (all_bg_data["datetime"] <= end_datetime)
        & (all_bg_data["datetime"] >= start_datetime)
    ][["datetime", "insulin"]]
    auto_boluses = pd.merge_asof(
        left=auto_boluses, right=basals_per_min, left_on="datetime", right_index=True
    )
    basals_per_min.loc[auto_boluses["index"], "absolute"] = (
        basals_per_min.loc[auto_boluses["index"], "absolute"].values
        + auto_boluses["insulin"].values
    )
    basals_per_min["is_adjusted"] = (
        basals_per_min["absolute"] != basals_per_min["scheduled"]
    )

    def get_windowed_series(col: pd.Series, window_size: int) -> np.array:
        """
        Get a running sum of N values in a pandas Series, taken every N values

        :param col: pandas Series of type float
        :param window_size: number of values to group
        :return: numpy array of sum of first window_size values, sum of next window_size values, etc.
        """
        np_col = col.to_numpy(dtype=float)
        cumulative_col = np.cumsum(np_col)
        cumulative_col[window_size:] = (
            cumulative_col[window_size:] - cumulative_col[:-window_size]
        )
        windowed_col = cumulative_col[window_size - 1 :: window_size] / window_size
        return windowed_col

    basals_per_hour = basals_per_min.iloc[59::60]

    basals_per_hour = basals_per_hour.assign(
        avg_basal=get_windowed_series(basals_per_min["absolute"], 60),
        is_adjusted=get_windowed_series(basals_per_min["is_adjusted"], 60) > 0,
        time_label=pd.to_datetime(
            start_datetime
            + (basals_per_hour.index - start_datetime) % datetime.timedelta(days=1)
        ),
        date=basals_per_hour.index.date,
    )
    basals_per_hour.drop(columns=["absolute", "index"], inplace=True)

    return basals_per_hour
