import requests

BASE_URL = "https://api.weather.gov"

HEADERS = {
    "User-Agent": "KLOT-Chicago-Romeoville-IL/1.0 (contact@example.com)",
    "Accept": "application/geo+json",
}


def get(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def get_point(latitude, longitude):
    return get(
        f"{BASE_URL}/points/{latitude},{longitude}"
    )


def get_active_alerts():
    return get(
        f"{BASE_URL}/alerts/active?area=IL"
    )


def get_forecast(latitude, longitude):
    point = get_point(latitude, longitude)

    forecast_url = point["properties"]["forecast"]

    return get(forecast_url)


def get_hourly_forecast(latitude, longitude):
    point = get_point(latitude, longitude)

    forecast_url = point["properties"]["forecastHourly"]

    return get(forecast_url)

LOCATIONS = {
    "chicago": {
        "name": "Chicago",
        "latitude": 41.8781,
        "longitude": -87.6298,
    },

    "romeoville": {
        "name": "Romeoville",
        "latitude": 41.6475,
        "longitude": -88.0895,
    },

    "valparaiso": {
        "name": "Valparaiso",
        "latitude": 41.4731,
        "longitude": -87.0611,
    },

    "gary": {
        "name": "Gary",
        "latitude": 41.5934,
        "longitude": -87.3464,
    },
}