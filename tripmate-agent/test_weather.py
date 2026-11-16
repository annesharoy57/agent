
import json
import urllib.parse
import urllib.request


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TripMateAI/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


try:
    # Step 1: Find the location coordinates
    location_url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({
            "name": "Sylhet",
            "count": 1,
            "language": "en",
            "format": "json"
        })
    )

    location_data = get_json(location_url)
    results = location_data.get("results", [])

    if not results:
        print("Location not found.")

    else:
        place = results[0]

        latitude = place["latitude"]
        longitude = place["longitude"]

        print("Location:", place["name"], place.get("country", ""))
        print("Coordinates:", latitude, longitude)

        # Step 2: Get the upcoming weather forecast
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
                "forecast_days": 7,
                "timezone": "auto"
            })
        )

        weather_data = get_json(weather_url)
        daily = weather_data["daily"]

        print("\n7-Day Weather Forecast")
        print("-" * 60)

        for i, day in enumerate(daily["time"]):
            print(
                day,
                "| Max:", daily["temperature_2m_max"][i], "C",
                "| Min:", daily["temperature_2m_min"][i], "C",
                "| Rain chance:",
                daily["precipitation_probability_max"][i], "%"
            )

        print("-" * 60)
        print("\nWeather source: Open-Meteo")
        print("https://open-meteo.com/")

except Exception as error:
    print("Weather test failed.")
    print("Error:", error)
