from app.weather import get_weather_forecast

try:
    result = get_weather_forecast("Sylhet", 7)

    print("TripMate Weather Tool: SUCCESS")
    print("Location:", result["location"], result["country"])
    print("Forecast days:", result["forecast_days"])

    print("\nWeather forecast:")

    for day in result["forecast"]:
        print(
            day["date"],
            "|", day["condition"],
            "| Max:", day["temperature_max_c"], "C",
            "| Min:", day["temperature_min_c"], "C",
            "| Rain:", day["rain_probability_percent"], "%"
        )

    print("\nSource:", result["source_url"])

except Exception as error:
    print("Weather tool failed:", error)
