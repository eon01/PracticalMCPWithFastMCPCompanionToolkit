# server.py
import httpx
from fastmcp import FastMCP

mcp = FastMCP("Weather & Air Quality")


def _get_coordinates(location: str) -> tuple[float, float]:
    """Resolve a place name to (latitude, longitude) via the Open-Meteo Geocoding API."""
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
    )
    data = response.json()
    if "results" in data and len(data["results"]) > 0:
        latitude = data["results"][0]["latitude"]
        longitude = data["results"][0]["longitude"]
        return latitude, longitude
    else:
        raise ValueError(f"Could not find coordinates for location: {location}")


@mcp.tool()
def get_air_quality(location: str) -> str:
    """Get air quality information based on a location."""
    latitude, longitude = _get_coordinates(location)
    response = httpx.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm10,pm2_5",
            "forecast_days": 1,
        },
    )
    data = response.json()
    if "hourly" in data and "pm10" in data["hourly"] and "pm2_5" in data["hourly"]:
        pm10 = data["hourly"]["pm10"][0]
        pm2_5 = data["hourly"]["pm2_5"][0]
        result = f"PM10: {pm10} μg/m³, PM2.5: {pm2_5} μg/m³"
    else:
        result = "Air quality data not available"
    return f"Air quality in {location}: {result}"


@mcp.tool()
def get_temperature(location: str) -> str:
    """Get the current temperature for a location."""
    latitude, longitude = _get_coordinates(location)
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m",
            "forecast_days": 1,
        },
    )
    data = response.json()
    if "hourly" in data and "temperature_2m" in data["hourly"]:
        temperature = data["hourly"]["temperature_2m"][0]
        result = f"Temperature: {temperature} °C"
    else:
        result = "Temperature data not available"
    return f"Temperature in {location}: {result}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
