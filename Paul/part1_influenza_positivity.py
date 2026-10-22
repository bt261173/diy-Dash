# Part 1 (influenza positivity): download the weekly percentage of influenza
# PCR tests that were positive in England, keep 2018 to 2024, and save as JSON.
#
# Metric: influenza_testing_positivityByWeek
# = % of influenza PCR tests in the 7 days up to each date that were positive.
#
# Based on "1-Accessing_UKHSA_Data.ipynb" by Fabrizio Smeraldi
# (C) 2020, 2024, released under the GNU GPLv3.0 or later.
#
# Running this creates: influenza_positivity.json
 
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
    print(f"{name}: expected {api.count}, retrieved {len(data)}")
    if api.count == 0:
        print(f"  WARNING: no data for {name}. Check the structure and metric names.")
    elif api.count != len(data):
        print(f"  WARNING: {name} download is incomplete. Try running the script again.")
 
 
# The "address" of the data: influenza in England
structure = {"theme": "infectious_disease",
             "sub_theme": "respiratory",
             "topic": "Influenza",
             "geography_type": "Nation",
             "geography": "England",
             "metric": "influenza_testing_positivityByWeek"}
 
# Download everything available for this metric
api = APIwrapper(**structure)
positivity = api.get_all_pages()
check_download("influenza positivity", api, positivity)
 
# Show the full date range UKHSA actually has, before filtering
all_dates = [entry['date'] for entry in positivity]
if len(all_dates) > 0:
    print("Data available from", min(all_dates), "to", max(all_dates))
 
# Keep only 2018 to 2024. Dates are written year first ("2019-01-07"),
# so comparing them as text puts them in the right order.
positivity = [entry for entry in positivity
              if "2018-01-01" <= entry['date'] <= "2024-12-31"]
print("Rows kept for 2018 to 2024:", len(positivity))
if len(positivity) > 0:
    kept_dates = [entry['date'] for entry in positivity]
    print("Kept data runs from", min(kept_dates), "to", max(kept_dates))
 
# Save as JSON for Part 2
with open("influenza_positivity.json", "wt") as OUTF:
    json.dump(positivity, OUTF)
print("Saved influenza_positivity.json")