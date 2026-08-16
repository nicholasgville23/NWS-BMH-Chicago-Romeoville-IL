"""Temporary import-chain verification for the WNG689 BMH launcher."""
import sys

sys.path.insert(0, r"NWS-BMH-Chicago-Romeoville-IL-main/data/resources/runtime/WNG689")

from bmh.runtime_dispatch import invoke as _bmh_invoke
from bmh.implementation_registry import IMPLEMETATIONS as _BMH_IMPLEMENTATIONS

from bmh.station import (
    FREQUENCY,
    LISTENING_COUNTIES,
    STATION_CODE,
    STATION_ID,
    STATION_LOCATION,
    STATION_REGION,
)
from bmh.audio.silence_detector import SafeSilenceDetector
from bmh.ui.character_generator import CharacterGenerator, get_secondary_monitor_geometry
from bmh.alerts.product_ids import (
    assign_segmented_product_id,
    build_bmh_product_id,
    normalize_product_originator,
)
from bmh.state import BMHState

print("invoke OK")
print("zones:", _bmh_invoke(_BMH_IMPLEMENTATIONS["poll_zones"], globals()))
print("station:", STATION_ID, STATION_CODE, FREQUENCY, STATION_LOCATION, STATION_REGION)
print("counties:", len(LISTENING_COUNTIES))
print("state:", BMHState().snapshot())
print("silence:", SafeSilenceDetector())
print("char_gen:", CharacterGenerator().render("TORNADO WARNING")[:1])
print("product_id:", build_bmh_product_id(event_code="TOR"))
print("segment:", assign_segmented_product_id(event_code="TOR"))
print("originator:", normalize_product_originator("wfo:KLOT"))
print("ALL IMPORTS OK")
