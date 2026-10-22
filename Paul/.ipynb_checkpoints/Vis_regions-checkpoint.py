# Part 2 (influenza by region): load influenza_regions.json saved by
# part1_influenza_regions.py, build one weekly DataFrame per measure with
# one column per region, draw a bar chart of each region's peak week in the
# 2022/23 season, and save for the dashboard.
#
# Based on "2-Visualising_the_Data.ipynb" by Fabrizio Smeraldi
# (C) 2020, 2024, released under the GNU GPLv3.0 or later.
#
# Needs in the same folder: influenza_regions.json
# Creates (for each measure that has data):
#   influenza_admissions_regions.pkl / .png
#   influenza_positivity_regions.pkl / .png

import json

import matplotlib.pyplot as plt
import pandas as pd

# make figures larger
plt.rcParams['figure.dpi'] = 100


def parse_date(datestring):
    """Convert a date string such as '2023-01-02' into a pandas date."""
    return pd.to_datetime(datestring, format="%Y-%m-%d")


# Load the data saved by Part 1
with open("influenza_regions.json", "rt") as INFILE:
    rows = json.load(INFILE)
print("Rows loaded:", len(rows))

# If the data has one row per age group, keep only all ages together
ages = []
for row in rows:
    if row.get('age') not in ages:
        ages.append(row.get('age'))
print("Age groups in the data:", ages)
if 'all' in ages:
    rows = [row for row in rows if row.get('age') == 'all']

# The two measures, with their metric names, file names and chart labels
measures = {
    "admissions": {"metric": "influenza_healthcare_hospitalAdmissionRateByWeek",
                   "file": "influenza_admissions_regions",
                   "peak_title": "Peak weekly influenza hospital admissions by region",
                   "peak_label": "Highest weekly hospital admissions per 100,000 people living in the region",
                   "note": "Rate = people admitted to hospital with flu in one week, per 100,000 people living in the region."},
    "positivity": {"metric": "influenza_testing_positivityByWeek",
                   "file": "influenza_positivity_regions",
                   "peak_title": "Peak weekly influenza PCR test positivity by region",
                   "peak_label": "Highest weekly % of influenza PCR tests that were positive (positive tests ÷ all tests × 100)",
                   "note": "Positivity = share of flu tests that were positive, not share of the population."},
}

for short_name, info in measures.items():
    # keep only the rows for this measure
    measure_rows = [row for row in rows if row['metric'] == info['metric']]
    print(f"\n{short_name}: {len(measure_rows)} rows")
    if len(measure_rows) == 0:
        print(f"  No regional data for {short_name}, skipping.")
        continue

    # Wrangle into {date: {region: value, ...}, ...}
    data = {}
    for row in measure_rows:
        date = row['date']
        region = row['geography']
        if date not in data:
            data[date] = {}
        data[date][region] = row['metric_value']

    # Sorted dates and the list of regions
    dates = list(data.keys())
    dates.sort()
    startdate = parse_date(dates[0])
    enddate = parse_date(dates[-1])
    regions = []
    for values in data.values():
        for region in values.keys():
            if region not in regions:
                regions.append(region)
    regions.sort()
    print("  Runs from", startdate.date(), "to", enddate.date())
    print("  Regions:", regions)

    # Empty DataFrame: one row per week, one column per region
    index = pd.date_range(startdate, enddate, freq='7D')
    df = pd.DataFrame(index=index, columns=regions)

    # Fill in the DataFrame
    for date, values in data.items():
        pd_date = parse_date(date)
        for region, value in values.items():
            df.loc[pd_date, region] = value

    # Make numeric. Missing weeks stay empty (NaN), not 0: no report is not no flu.
    df = df.astype(float)
    # Store the column names as plain Python text, so the .pkl file can also be
    # read by older versions of pandas (e.g. the one Jupyter uses)
    df.columns = pd.Index([str(c) for c in df.columns], dtype=object)

    # Save for the dashboard, then check by loading back
    df.to_pickle(info['file'] + ".pkl")
    if pd.read_pickle(info['file'] + ".pkl").equals(df):
        print(f"  Saved and checked {info['file']}.pkl")
    else:
        print(f"  WARNING: {info['file']}.pkl doesn't match. Try running again.")

    # Chart: peak week of the 2022/23 season, one bar per region
    season = df.loc["2022-09-01":"2023-05-31"]
    weeks_in_season = len(season)
    if not season.notna().any().any():
        print("  No data for the 2022/23 season, so no chart drawn.")
        continue

    # For each region: highest weekly value, the week it happened,
    # and how many weeks had data
    peaks = []
    for region in season.columns:
        values = season[region]
        weeks_with_data = values.notna().sum()
        if weeks_with_data == 0:
            continue  # no data at all for this region this season
        peaks.append({"region": region,
                      "peak": values.max(),
                      "week": values.idxmax(),
                      "weeks": weeks_with_data,
                      # a region needs data for at least half the weeks to count as complete
                      "complete": weeks_with_data >= weeks_in_season / 2})
    # sort lowest first, so the highest bar ends up at the top of the chart
    peaks.sort(key=lambda row: row["peak"])

    # complete regions in red, incomplete ones in grey
    colours = ["#c0392b" if row["complete"] else "lightgrey" for row in peaks]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh([row["region"] for row in peaks], [row["peak"] for row in peaks], color=colours)

    # write the value and the week of the peak beside each bar
    biggest = max(row["peak"] for row in peaks)
    for i, row in enumerate(peaks):
        label = f"{row['peak']:.1f}  (week of {row['week'].strftime('%d %b %Y')})"
        if not row["complete"]:
            label += f"  incomplete data: {row['weeks']} of {weeks_in_season} weeks"
        ax.text(row["peak"] + biggest * 0.01, i, label, va="center", fontsize=9)
    ax.set_xlim(0, biggest * 1.6)  # leave room for the labels

    ax.set_title(f"{info['peak_title']}, England, 2022/23 season")
    ax.set_xlabel(info['peak_label'])
    ax.set_ylabel("UKHSA region")
    plt.figtext(0.01, -0.08, info['note'] + "\nGrey bars = incomplete data, so the true peak may be higher. "
                "Source: UKHSA data dashboard API.", fontsize=9, color="dimgrey")
    plt.savefig(info['file'] + ".png", bbox_inches="tight")

# Show the charts on screen (in a notebook they appear automatically)
plt.show()