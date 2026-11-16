
from datetime import date, timedelta
import json
import urllib.parse
import urllib.request

from app.research import fetch_json


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TripMateAI/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_weather_forecast(location, days=7):
    """
    Get a weather forecast for a destination.

    Open-Meteo provides forecasts for up to 16 days.
    No API key is required for this test.
    """

    days = max(1, min(int(days), 16))

    # Find the destination's coordinates
    location_url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        })
    )

    location_data = get_json(location_url)
    results = location_data.get("results", [])

    if not results:
        raise ValueError(f"Location not found: {location}")

    place = results[0]

    latitude = place["latitude"]
    longitude = place["longitude"]

    # Request the daily weather forecast
    weather_url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "forecast_days": days,
            "timezone": "auto"
        })
    )

    weather_data = get_json(weather_url)
    daily = weather_data["daily"]

    forecast = []

    for i, day in enumerate(daily["time"]):
        code = daily["weather_code"][i]

        forecast.append({
            "date": day,
            "weather_code": code,
            "condition": WEATHER_CODES.get(code, "Unknown weather"),
            "temperature_max_c": daily["temperature_2m_max"][i],
            "temperature_min_c": daily["temperature_2m_min"][i],
            "rain_probability_percent":
                daily["precipitation_probability_max"][i]
        })

    return {
        "location": place["name"],
        "country": place.get("country", ""),
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": len(forecast),
        "forecast": forecast,
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/"
    }


def get_destination_forecast(destination, start, days):
    """Fetch a date-specific forecast for known destination coordinates."""
    latitude = destination.get("lat")
    longitude = destination.get("lon")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return None

    today = date.today()
    if start < today or start > today + timedelta(days=15):
        return None
    end = min(start + timedelta(days=days - 1), today + timedelta(days=15))
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    })
    data = fetch_json(url)
    if not isinstance(data, dict) or not isinstance(data.get("daily"), dict):
        return None
    daily = data["daily"]
    return {
        "source": "Open-Meteo",
        "forecast_days": daily.get("time", []),
        "max_temp_c": daily.get("temperature_2m_max", []),
        "min_temp_c": daily.get("temperature_2m_min", []),
        "precipitation_probability_percent": daily.get("precipitation_probability_max", []),
        "note": "Forecast is only available for dates within the provider's forecast window and can change.",
    }
