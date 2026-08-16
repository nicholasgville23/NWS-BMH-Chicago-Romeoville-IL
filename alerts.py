from nws_api import get

ALERTS_URL = "https://api.weather.gov/alerts/active"

import os
import json

OUTPUT_DIRS = [
    r"C:\Users\nicho\Downloads\NWS-BMH-Chicago-Romeoville-IL-main\NWS-BMH-Chicago-Romeoville-IL-main\data\resources\runtime\WNG689",
    r"C:\Users\nicho\Downloads\NWS-BMH-Chicago-Romeoville-IL-main\NWS-BMH-Chicago-Romeoville-IL-main\data\resources\runtime\WNG689\alerts.py"
]

def save_alerts(data):
    for path in OUTPUT_DIRS:
        if not path.endswith('.py'):
            os.makedirs(path, exist_ok=True)
            file_path = os.path.join(path, "alerts.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

def get_klot_alerts():
    data = get(
        f"{ALERTS_URL}?area=IN"
    )

    return data.get("features", [])