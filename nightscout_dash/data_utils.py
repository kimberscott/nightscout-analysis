from typing import List

import pandas as pd
import abc


def bg_data_json_to_df(bg_json: str, timezone_name: str) -> pd.DataFrame:
    """
    Wrapper to convert from the BG JSON stored in the dcc.Store element back to a dataframe,
    including tz-aware datetime values.

    :param bg_json: JSON representation of bg data from Nightscout
    :param timezone_name: string representing timezone to convert times to (times are stored in UTC in JSON)
    :return: Pandas dataframe with tz-aware datetime column
    """
    all_bg_data = pd.read_json(bg_json, orient="split")
    all_bg_data["datetime"] = pd.to_datetime(
        all_bg_data["datetime"], utc=True
    ).dt.tz_convert(timezone_name)
    return all_bg_data


def profile_json_to_df(profile_json: str, timezone_name: str) -> pd.DataFrame:
    """
    Wrapper to convert from the profile JSON stored in the dcc.Store element back to a dataframe,
    including tz-aware datetime values.

    :param profile_json: JSON representation of profile data from Nightscout
    :param timezone_name: string representing timezone to convert times to (times are stored in UTC in JSON)
    :return: Pandas dataframe with tz-aware profile_start_datetime column
    """
    profiles = pd.read_json(profile_json, orient="split")
    profiles["profile_start_datetime"] = pd.to_datetime(
        profiles["profile_start_datetime"], utc=True
    ).dt.tz_convert(timezone_name)
    return profiles


class AnalysisComponent(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def register_callbacks() -> None:
        """
        Register any callbacks necessary for this component.
        """
        pass

    @property
    @abc.abstractmethod
    def layout_contents(self) -> List:
        """
        :return:
        """
        pass
