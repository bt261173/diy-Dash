import requests
import time
import json
import pandas as pd
import matplotlib.pyplot as plt


class APIwrapper:
    # class variables shared among all instances
    _access_point="https://api.ukhsa-dashboard.data.gov.uk"
    _last_access=0.0 # time of last api access

    def __init__(self, theme, sub_theme, topic, geography_type, geography, metric):
        """ Init the APIwrapper object, constructing the endpoint from the structure
        parameters """
        # build the path with all the required structure parameters. You do not need to edit this line,
        # parameters will be replaced by the actual values when you instantiate an object of the class!
        url_path=(f"/themes/{theme}/sub_themes/{sub_theme}/topics/{topic}/geography_types/" +
                  f"{geography_type}/geographies/{geography}/metrics/{metric}")
        # our starting API endpoint
        self._start_url=APIwrapper._access_point+url_path
        self._filters=None
        self._page_size=-1
        # will contain the number of items
        self.count=None

    def get_page(self, filters={}, page_size=5):
        """ Access the API and download the next page of data. Sets the count
        attribute to the total number of items available for this query. Changing
        filters or page_size will cause get_page to restart from page 1. Rate
        limited to three request per second. The page_size parameter sets the number
        of data points in one response page (maximum 365); use the default value
        for debugging your structure and filters. """
        # Check page size is within range
        if page_size>365:
            raise ValueError("Max supported page size is 365")
        # restart from first page if page or filters have changed
        if filters!=self._filters or page_size!=self._page_size:
            self._filters=filters
            self._page_size=page_size
            self._next_url=self._start_url
        # signal the end of data condition
        if self._next_url==None:
            return [] # we already fetched the last page
        # simple rate limiting to avoid bans
        curr_time=time.time() # Unix time: number of seconds since the Epoch
        deltat=curr_time-APIwrapper._last_access
        if deltat<0.33: # max 3 requests/second
            time.sleep(0.33-deltat)
        APIwrapper._last_access=curr_time
        # build parameter dictionary by removing all the None
        # values from filters and adding page_size
        parameters={x: y for x, y in filters.items() if y!=None}
        parameters['page_size']=page_size
        # the page parameter is already included in _next_url.
        # This is the API access. Response is a dictionary with various keys.
        # the .json() method decodes the response into Python object (dictionaries,
        # lists; 'null' values are translated as None).
        response = requests.get(self._next_url, params=parameters).json()
        # update url so we'll fetch the next page
        self._next_url=response['next']
        self.count=response['count']
        # data are in the nested 'results' list
        return response['results']

    def get_all_pages(self, filters={}, page_size=365):
        """ Access the API and download all available data pages of data. Sets the count
        attribute to the total number of items available for this query. API access rate
        limited to three request per second. The page_size parameter sets the number
        of data points in one response page (maximum 365), and controls the trade-off
        between time to load a page and number of pages; the default should work well
        in most cases. The number of items returned should in any case be equal to
        the count attribute. """
        data=[] # build up all data here
        while True:
            # use get_page to do the job, including the pacing
            next_page=self.get_page(filters, page_size)
            if next_page==[]:
                break # we are done
            data.extend(next_page)
        return data


# Graph 1: hospital admissions rate per week 2018-2024 England

# download
structure = {"theme": "infectious_disease",
             "sub_theme": "respiratory",
             "topic": "Influenza",
             "geography_type": "Nation",
             "geography": "England",
             "metric": "influenza_healthcare_hospitalAdmissionRateByWeek"}

api = APIwrapper(**structure)
flu_admissions = api.get_all_pages()

with open("flu_admissions.json", "wt") as OUTF:
    json.dump(flu_admissions, OUTF)


def parse_date(datestring):
    return pd.to_datetime(datestring, format="%Y-%m-%d")

# date
data = {}
for entry in flu_admissions:
    if entry["age"] == "all":
        data[entry["date"]] = entry["metric_value"]

dates = sorted(data.keys())
startdate = parse_date(dates[0])
enddate = parse_date(dates[-1])

# weekly index on the same weekday as the data
weekday = startdate.day_name()[:3].upper()
index = pd.date_range(startdate, enddate, freq="W-" + weekday)
flu_df = pd.DataFrame(index=index, columns=["admission_rate"])

# fill in values
for date, value in data.items():
    flu_df.loc[parse_date(date), "admission_rate"] = value

flu_df = flu_df.astype(float)

# plot
flu_period = flu_df.loc["2018-01-01":"2024-12-31"]

ax = flu_period.plot(legend=False)
ax.set_title("Influenza hospital admissions, England")
ax.set_ylabel("Admissions per 100,000 (weekly)")
ax.set_xlabel("")


# Graph 2: peak weekly rate per region in the 2022/23 season 

# download
regions = ["London", "North West", "East of England", "Yorkshire and Humber", "South East",
           "West Midlands", "South West", "East Midlands", "North East"]

region_admissions = {}          # region name -> list of entries
for region in regions:
    structure = {"theme": "infectious_disease",
                 "sub_theme": "respiratory",
                 "topic": "Influenza",
                 "geography_type": "UKHSA Region",
                 "geography": region,
                 "metric": "influenza_healthcare_hospitalAdmissionRateByWeek"}
    api = APIwrapper(**structure)
    region_admissions[region] = api.get_all_pages()

with open("flu_admissions_regions.json", "wt") as OUTF:
    json.dump(region_admissions, OUTF)

# peak region and amount of weeks data
peaks = {}
weeks_with_data = {}
for region, entries in region_admissions.items():
    for e in entries:
        if "2022-09-01" <= e["date"] <= "2023-08-31" and e["age"] == "all":
            weeks_with_data[region] = weeks_with_data.get(region, 0) + 1
            if region not in peaks or e["metric_value"] > peaks[region][0]:
                peaks[region] = (e["metric_value"], e["date"])

# fix order and highlight low data regions
order = [r for r in regions if r in peaks]
values = [peaks[r][0] for r in order]
weeks = [pd.to_datetime(peaks[r][1]).strftime("%d %b %Y") for r in order]
colours = ["#c0392b" if weeks_with_data[r] >= 50 else "grey" for r in order]

# chart
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(order, values, color=colours)
ax.invert_yaxis()                                   # first region in the list at the top
for i, (v, w) in enumerate(zip(values, weeks)):
    ax.text(v + max(values) * 0.01, i, f"{v:.1f}  (week of {w})", va="center", fontsize=9)
ax.set_xlim(0, max(values) * 1.4)
ax.set_title("Peak weekly influenza hospital admission rate by region, England, 2022/23 season")
ax.set_xlabel("Highest weekly admissions per 100,000 people")
ax.set_ylabel("UKHSA region")
fig.text(0.1, -0.1, "Rate = confirmed influenza hospital admissions per 100,000 population.\n"
         "Grey bars = incomplete data for this season, so the true peak may be higher.\n"
         "Source: UKHSA data dashboard API.", fontsize=9, color="grey")
plt.show()