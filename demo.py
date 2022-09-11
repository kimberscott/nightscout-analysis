import requests
from dotenv import load_dotenv
import os
import pandas as pd
import datetime
import tzlocal # $ pip install tzlocal
import math

load_dotenv()



NIGHTSCOUT_URL = os.getenv('NIGHTSCOUT_URL')
ENTRIES_ENDPOINT = NIGHTSCOUT_URL + 'entries.json'
TREATMENTS_ENDPOINT = NIGHTSCOUT_URL + 'treatments.json'


def add_time_identifiers(df: pd.DataFrame, datetime_col_name: str) -> None:
    df['date'] = df[datetime_col_name].apply(lambda dt: dt.date())
    df['weekday'] = df[datetime_col_name].apply(lambda dt: dt.strftime('%A'))
    df['weekday_number'] = df[datetime_col_name].apply(lambda dt: dt.weekday())
    df['time'] = df[datetime_col_name].apply(lambda dt: dt.time())
    df['time_str'] = df[datetime_col_name].apply(lambda dt: dt.time().strftime('%H:%M'))

def fetch_nightscout_data(start_date: datetime.datetime = None, end_date: datetime.datetime = None) -> (pd.DataFrame, pd.DataFrame):

    date_strs = (start_date.strftime('%Y-%m-%d') if start_date else None, end_date.strftime('%Y-%m-%d') if end_date else None)

    bg_param_names = ('find[dateString][$gte]', 'find[dateString][$lte]')
    treatment_param_names = ('find[created_at][$gte]', 'find[created_at][$lte]')

    # Fetch blood glucose entries
    bg_params = {param: date for param, date in zip(bg_param_names, date_strs) if date is not None}
    bg_params['count'] = 12 * 24 * dt.days
    bg_list = requests.get(
        ENTRIES_ENDPOINT,
        params=bg_params,
        headers={'accept': 'application/json'}
    ).json()
    bg = pd.DataFrame.from_records(bg_list)
    bg['datetime'] = pd.to_datetime(bg['date'], unit='ms', utc=True)
    bg['datetime'] = bg['datetime'].apply(lambda dt: dt.astimezone(tzlocal.get_localzone()))
    # Limit columns
    # TODO: factor out into helper
    bg_cols = ['datetime', 'sgv', 'mbg', 'type']
    bg = bg[[col for col in bg_cols if col in bg]]
    for col in bg_cols:
        if col not in bg:
            bg[col] = None
    add_time_identifiers(bg, 'datetime')

    # Fetch treatment entries
    treatment_params = {param: date for param, date in zip(treatment_param_names, date_strs) if date is not None}
    treatment_params['count'] = 50 * dt.days
    treatments_list = requests.get(
        TREATMENTS_ENDPOINT,
        params=treatment_params,
        headers={'accept': 'application/json'}
    ).json()
    treatments = pd.DataFrame.from_records(treatments_list)
    treatments['datetime'] = pd.to_datetime(treatments['created_at'])
    treatments['datetime'] = treatments['datetime'].apply(lambda dt: dt.astimezone(tzlocal.get_localzone()))
    # Limit columns
    treatment_cols = ['datetime', 'carbs', 'insulin', 'eventType']
    treatments = treatments[[col for col in treatment_cols if col in treatments]]
    for col in treatment_cols:
        if col not in treatments:
            treatments[col] = None
    add_time_identifiers(treatments, 'datetime')

    return bg, treatments


dt = datetime.timedelta(days=13)
now = datetime.datetime.now()
bg, treatments = fetch_nightscout_data(now - dt)

# Display likely fasting blood sugar measurements

fasting_smbg = bg.loc[
    (bg['type'] == 'mbg') & (datetime.time(hour=6) < bg['time']) & (bg['time'] < datetime.time(hour=12))
]
print('Fasting blood sugar measurements')
print(fasting_smbg[['date', 'time_str', 'mbg']].reset_index(drop=True))

# Display mean and standard deviation
n_bg = sum(bg['sgv'] > 0)
print(f'CGM summary data ({n_bg} measurements):')
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
    target_str = f'   (target: {target})' if target else ''
    print(f'\t[{lo} - {hi}): {(sum((bg["sgv"] >= lo) & (bg["sgv"] < hi)) / n_bg * 100):.1f}%{target_str}')

# TODO: plot overall distribution

# TODO: make a table of treatments, ratios, and "outcomes" grouped by likely meal

# TODO: make a table of TDD

# TODO: make heatmap or other stacked plot of day x hour

# TODO: make annotated daily plot

# TODO: align on doses, look at meal trajectories?

# TODO: use annotations on nightscout to discount pressure lows etc

# TODO: put into basic Dash app