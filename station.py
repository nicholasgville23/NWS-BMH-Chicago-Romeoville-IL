print("This NWR Station is WNG689 in Hebron, or Valparaiso, IN, or Indiana.")

"""
Station constants for the KLOT_BMH WNG689 NOAA Weather Radio station.

WNG689 serves NW Indiana (Porter, Lake, LaPorte, Jasper) and NE Illinois
from a transmitter near Porter Township / Valparaiso, Indiana. The BMH
broadcast originates from the NWS Forecast Office in Romeoville, IL (KLOT).
"""

STATION_ID = "WNG689"
STATION_CODE = "WNG689"

FREQUENCY = "162.450 MHz"

STATION_LOCATION = "Hebron / Valparaiso, IN"
STATION_REGION = "NE Illinois / NW Indiana"

LISTENING_COUNTIES = (
    "Porter",
    "Lake",
    "LaPorte",
    "Jasper",
    "Newton",
    "Starke",
    "Cook",
    "Will",
    "Kankakee",
)

__all__ = [
    "STATION_ID",
    "STATION_CODE",
    "FREQUENCY",
    "STATION_LOCATION",
    "STATION_REGION",
    "LISTENING_COUNTIES",
]
