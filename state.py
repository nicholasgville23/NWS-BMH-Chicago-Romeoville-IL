print("NWS City and State of NE (Northeast) Illinois and NW (Northwest) Indiana.")

# NWS Chicago/Romeoville Coverage Area
region_info = {
    "nws_office": "LOT",
    "city": "Romeoville",
    "state": "Illinois",
    "coverage_areas": [
        {"state": "Illinois", "region": "Northeast"},
        {"state": "Indiana", "region": "Northwest"}
    ],
    "station_code": "WNG689"
}

print(f"Coverage: NE Illinois and NW Indiana.")

import os
import sys

# Ensure the local 'bmh' directory is in the path to resolve the import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Define the BMHState class to resolve the ImportError
class BMHState:
    def __init__(self, office, city, state, coverage, station_code):
        self.office = office
        self.city = city
        self.state = state
        self.coverage = coverage
        self.station_code = station_code

# Implementation to initialize the state using the defined dictionary
bmh_state = BMHState(
    region_info["nws_office"],
    region_info["city"],
    region_info["state"],
    region_info["coverage_areas"],
    region_info["station_code"]
)

print(f"BMHState initialized for station: {bmh_state.station_code}")
