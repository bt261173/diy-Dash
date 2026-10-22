# Part 1 (influenza by region): download weekly influenza data for each of the
# 9 UKHSA Regions in England, keep 2018 to 2024, and save as one JSON file.
#
# Downloads:
#   - hospital admission rate per 100,000 (influenza_healthcare_hospitalAdmissionRateByWeek)
#   - test positivity, % of PCR tests positive (influenza_testing_positivityByWeek),
#     if UKHSA publishes it by region (the script tells you if not)
#
# The 9 UKHSA Regions cover seasons up to September 2024. From 30 September 2024
# UKHSA reports admissions by 4 Super-Regions instead, so this stays with the
# 9 Regions to keep the 2018 to 2024 series unbroken.
#
# Based on "1-Accessing_UKHSA_Data.ipynb" by Fabrizio Smeraldi
# (C) 2020, 2024, released under the GNU GPLv3.0 or later.
#
# Running this creates: influenza_regions.json

import json
import time

import requests


class APIwrapper:
    # class variables shared among all instances
    _access_point = "https://api.ukhsa-dashboard.data.gov.uk"
    _last_access = 0.0  # time of last API access

    def __init__(self, theme, sub_theme, topic, geography_type, geography, metric):
        """Build the endpoint URL from the structure parameters."""
        url_path = (f"/themes/{theme}/sub_themes/{sub_theme}/topics/{topic}/geography_types/" +
                    f"{geography_type}/geographies/{geography}/metrics/{metric}")
        self._start_url = APIwrapper._access_point + url_path
        self._filters = None
        self._page_size = -1
        # will contain the number of items
        self.count = None

    def get_page(self, filters={}, page_size=5):
        """Download the next page of data. Returns [] when there is no more data.
        Rate limited to three requests per second. Maximum page size is 365."""
        if page_size > 365:
            raise ValueError("Max supported page size is 365")
        # restart from the first page if filters or page size have changed
        if filters != self._filters or page_size != self._page_size:
            self._filters = filters
            self._page_size = page_size
            self._next_url = self._start_url
        # end of data
        if self._next_url == None:
            return []
        # simple rate limiting to avoid being banned
        curr_time = time.time()
        deltat = curr_time - APIwrapper._last_access
        if deltat < 0.33:  # max 3 requests per second
            time.sleep(0.33 - deltat)
        APIwrapper._last_access = curr_time
        # remove None values from the filters and add the page size
        parameters = {x: y for x, y in filters.items() if y != None}
        parameters['page_size'] = page_size
        # access the API; .json() turns the reply into Python dictionaries and lists
        response = requests.get(self._next_url, params=parameters).json()
        # remember where the next page is, and how many items exist in total
        self._next_url = response['next']
        self.count = response['count']
        # the actual data are in the 'results' list
        return response['results']

    def get_all_pages(self, filters={}, page_size=365):
        """Download all pages of data and return them as one list."""
        data = []  # build up all data here
        while True:
            next_page = self.get_page(filters, page_size)
            if next_page == []:
                break  # we are done
            data.extend(next_page)
        return data


def check_download(name, api, data):
    """Print how many data points were expected and retrieved, with a warning
    if the query returned nothing or the download is incomplete."""
    print(f"  {name}: expected {api.count}, retrieved {len(data)}")
    if api.count == 0:
        print(f"    WARNING: no data for {name}.")
    elif api.count != len(data):
        print(f"    WARNING: {name} download is incomplete. Try running the script again.")


# ---------------------------------------------------------------
# Step 1: ask the API for the names of the regions
# ---------------------------------------------------------------

geography_type = "UKHSA Region"
regions_url = ("https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease"
               "/sub_themes/respiratory/topics/Influenza"
               f"/geography_types/{geography_type}/geographies")
reply = requests.get(regions_url).json()
# the reply is a list of {"name": ..., "link": ...}, like the geography types list
if isinstance(reply, dict) and 'results' in reply:
    reply = reply['results']
regions = [item['name'] for item in reply]
print(f"{len(regions)} regions found:", regions)

# ---------------------------------------------------------------
# Step 2: download each metric for each region
# ---------------------------------------------------------------

metrics = {"admissions": "influenza_healthcare_hospitalAdmissionRateByWeek",
           "positivity": "influenza_testing_positivityByWeek"}

all_rows = []  # every row from every region and metric goes in here
for short_name, metric in metrics.items():
    print(f"\nDownloading {short_name} ({metric})")
    found_any = False
    for region in regions:
        structure = {"theme": "infectious_disease",
                     "sub_theme": "respiratory",
                     "topic": "Influenza",
                     "geography_type": geography_type,
                     "geography": region,
                     "metric": metric}
        api = APIwrapper(**structure)
        rows = api.get_all_pages()
        check_download(region, api, rows)
        if len(rows) > 0:
            found_any = True
        all_rows.extend(rows)
    if not found_any:
        print(f"  -> No regional data for {short_name}. It may only be published for England.")

# ---------------------------------------------------------------
# Step 3: keep 2018 to 2024 and save
# ---------------------------------------------------------------

# Dates are written year first ("2019-01-07"), so comparing them as text works
all_rows = [row for row in all_rows if "2018-01-01" <= row['date'] <= "2024-12-31"]
print("\nRows kept for 2018 to 2024:", len(all_rows))
if len(all_rows) > 0:
    kept_dates = [row['date'] for row in all_rows]
    print("Kept data runs from", min(kept_dates), "to", max(kept_dates))

with open("influenza_regions.json", "wt") as OUTF:
    json.dump(all_rows, OUTF)
print("Saved influenza_regions.json")