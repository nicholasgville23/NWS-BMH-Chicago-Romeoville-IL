"""
BMH Broadcast Message Handler - Product Registry
Registers available AWIPS products for the BMH Menu.
"""

from enum import Enum

class BMHProduct(Enum):
    # Format: ID = (Name, Description, Priority)
    SPS = ("Special Weather Statement", "Local weather updates and alerts", 3)
    SVR = ("Severe Thunderstorm Warning", "Immediate severe threat notification", 1)
    TOR = ("Tornado Warning", "Immediate tornado threat notification", 1)
    FFW = ("Flash Flood Warning", "Immediate flood threat notification", 1)
    HWO = ("Hazardous Weather Outlook", "Long-range weather outlook", 5)
    NOW = ("Nowcast", "Short-term weather conditions", 4)
    PNS = ("Public Information Statement", "General information", 6)

def get_product_metadata(product_id):
    """Retrieve metadata for a specific product ID."""
    return BMHProduct[product_id].value if product_id in BMHProduct.__members__ else None

def list_all_products():
    """Return list of all registered product IDs."""
    return [p.name for p in BMHProduct]
