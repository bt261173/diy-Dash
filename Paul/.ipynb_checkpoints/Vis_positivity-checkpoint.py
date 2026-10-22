 #Part 2 (influenza positivity): load influenza_positivity.json saved by part1_influenza_positivity.py,
# turn it into a weekly pandas DataFrame, plot it, and save it for Part 3.
#
# Based on "2-Visualising_the_Data.ipynb" by Fabrizio Smeraldi
# (C) 2020, 2024, released under the GNU GPLv3.0 or later.
#
# Needs in the same folder: influenza_positivity.json
# Creates: influenza_positivity.pkl (for Part 3) and influenza_positivity.png (the chart)
 
import json
 
import matplotlib.pyplot as plt
import pandas as pd
 
# make figures larger
plt.rcParams['figure.dpi'] = 100
 
 
def parse_date(datestring):
    """Convert a date string such as '2024-01-08' into a pandas date."""
    return pd.to_datetime(datestring, format="%Y-%m-%d")
 
 
# Load the data saved by Part 1
with open("influenza_positivity.json", "rt") as INFILE:
    influenza = json.load(INFILE)
print("Rows loaded:", len(influenza))
 
# Some metrics have one row per age group for each week. If so, keep only
# the rows for all ages together, so there is one value per week.
ages = []
for entry in influenza:
    age = entry.get('age')
    if age not in ages:
        ages.append(age)
print("Age groups in the data:", ages)
if 'all' in ages:
    influenza = [entry for entry in influenza if entry.get('age') == 'all']
    print("Keeping only age 'all':", len(influenza), "rows")
 
# Wrangle into a dictionary: {date: value}
data = {}
for entry in influenza:
    date = entry['date']
    value = entry['metric_value']
    data[date] = value
 
# Sort the dates (year-first dates sort correctly as text)
dates = list(data.keys())
dates.sort()
startdate = parse_date(dates[0])
enddate = parse_date(dates[-1])
print("Influenza data runs from", startdate.date(), "to", enddate.date())
 
# Empty DataFrame: one row per week, one column for influenza.
# The weekly dates follow the same day of the week as the first date.
index = pd.date_range(startdate, enddate, freq='7D')
influenzadf = pd.DataFrame(index=index, columns=['influenza'])
 
# Fill in the DataFrame
for date, value in data.items():
    pd_date = parse_date(date)
    influenzadf.loc[pd_date, 'influenza'] = value
 
# Make the column numeric. Weeks with no data stay empty (NaN), NOT 0,
# because in summer UKHSA reports less often: a gap means "no data",
# not "no positive tests". The chart will show these as breaks in the line.
influenzadf = influenzadf.astype(float)
# Store the column names as plain Python text, so the .pkl file can also be
# read by older versions of pandas (e.g. the one Jupyter uses)
influenzadf.columns = pd.Index([str(c) for c in influenzadf.columns], dtype=object)
print(influenzadf.tail())
print("Weeks with no data:", influenzadf['influenza'].isna().sum())
 
# Plot
ax = influenzadf.plot(legend=False, figsize=(9, 4.5))
ax.set_title(f'Influenza test positivity, England, {startdate.year} to {enddate.year}')
ax.set_ylabel('% of influenza PCR tests that were positive\n(positive tests ÷ all tests × 100), weekly')
ax.set_xlabel('Date (each point = one week)')
# gaps in the line mean no data was reported that week
plt.figtext(0.01, -0.12, "Positivity = share of flu tests that were positive, not share of the population.\n"
            "Gaps in the line = no data reported that week. "
            "Source: UKHSA data dashboard API.", fontsize=9, color="dimgrey")
plt.savefig("influenza_positivity.png", bbox_inches="tight")
 
# Save the DataFrame for Part 3, then check it by loading it back
influenzadf.to_pickle("influenza_positivity.pkl")
check = pd.read_pickle("influenza_positivity.pkl")
if check.equals(influenzadf):
    print("Saved and checked influenza_positivity.pkl")
else:
    print("WARNING: influenza_positivity.pkl doesn't match the DataFrame. Try running again.")
 
# Show the chart on screen (in a notebook it appears automatically)
plt.show()
 