import requests
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("Weather")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def _geocode(location: str) -> dict | str:
    """Resolve location name to lat/lon."""
    try:
        r = requests.get(GEOCODING_URL, params={"name": location, "count": 1, "language": "en", "format": "json"}, timeout=10)
        data = r.json()
        if not data.get("results"):
            return f"Error: Could not find location '{location}'."
        result = data["results"][0]
        return {
            "name": result.get("name", location),
            "country": result.get("country", ""),
            "lat": result["latitude"],
            "lon": result["longitude"],
            "timezone": result.get("timezone", "UTC"),
        }
    except Exception as e:
        return f"Error: Geocoding failed — {e}"


@mcp.tool()
def get_current_weather(location: str) -> str:
    """
    Get the current weather for any city or location worldwide.
    Provides temperature, humidity, wind speed, and conditions.
    Example: get_current_weather("Mumbai")
    """
    geo = _geocode(location)
    if isinstance(geo, str):
        return geo

    params = {
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "current": [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m",
            "surface_pressure", "cloud_cover", "visibility",
        ],
        "timezone": geo["timezone"],
        "wind_speed_unit": "kmh",
    }

    try:
        r = requests.get(WEATHER_URL, params=params, timeout=10)
        data = r.json()
        c = data["current"]

        condition = WMO_CODES.get(c["weather_code"], "Unknown")

        wind_dir = c["wind_direction_10m"]
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        wind_label = directions[round(wind_dir / 45) % 8]

        return (
            f"📍 {geo['name']}, {geo['country']}\n"
            f"🌡️  Temperature: {c['temperature_2m']}°C (Feels like {c['apparent_temperature']}°C)\n"
            f"☁️  Condition: {condition}\n"
            f"💧 Humidity: {c['relative_humidity_2m']}%\n"
            f"🌧️  Precipitation: {c['precipitation']} mm\n"
            f"💨 Wind: {c['wind_speed_10m']} km/h {wind_label}\n"
            f"🔵 Pressure: {c['surface_pressure']} hPa\n"
            f"☁️  Cloud Cover: {c['cloud_cover']}%\n"
            f"👁️  Visibility: {c.get('visibility', 'N/A')} m\n"
            f"🕐 Time: {c['time']}"
        )
    except Exception as e:
        return f"Error: Failed to fetch weather — {e}"


@mcp.tool()
def get_weather_forecast(location: str, days: int = 7) -> str:
    """
    Get a multi-day weather forecast for any location.
    days: number of forecast days (1–14, default 7)
    Example: get_weather_forecast("London", 5)
    """
    days = max(1, min(14, days))
    geo = _geocode(location)
    if isinstance(geo, str):
        return geo

    params = {
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "daily": [
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "wind_speed_10m_max", "sunrise", "sunset",
        ],
        "timezone": geo["timezone"],
        "forecast_days": days,
        "wind_speed_unit": "kmh",
    }

    try:
        r = requests.get(WEATHER_URL, params=params, timeout=10)
        data = r.json()
        d = data["daily"]

        lines = [f"📍 {days}-Day Forecast — {geo['name']}, {geo['country']}\n"]
        for i in range(len(d["time"])):
            date = d["time"][i]
            code = d["weather_code"][i]
            condition = WMO_CODES.get(code, "Unknown")
            tmax = d["temperature_2m_max"][i]
            tmin = d["temperature_2m_min"][i]
            precip = d["precipitation_sum"][i]
            wind = d["wind_speed_10m_max"][i]
            sunrise = d["sunrise"][i].split("T")[-1] if d.get("sunrise") else "N/A"
            sunset = d["sunset"][i].split("T")[-1] if d.get("sunset") else "N/A"

            day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
            lines.append(
                f"📅 {day_name} ({date})\n"
                f"   🌡️  {tmin}°C – {tmax}°C | {condition}\n"
                f"   🌧️  Rain: {precip}mm | 💨 Wind: {wind} km/h\n"
                f"   🌅 {sunrise} ↑  🌇 {sunset} ↓"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Error: Failed to fetch forecast — {e}"


@mcp.tool()
def get_hourly_weather(location: str, hours: int = 24) -> str:
    """
    Get hourly weather data for a location.
    hours: number of hours ahead to show (1–48, default 24)
    Example: get_hourly_weather("Tokyo", 12)
    """
    hours = max(1, min(48, hours))
    geo = _geocode(location)
    if isinstance(geo, str):
        return geo

    params = {
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "hourly": [
            "temperature_2m", "precipitation_probability",
            "weather_code", "wind_speed_10m",
        ],
        "timezone": geo["timezone"],
        "forecast_days": 2,
        "wind_speed_unit": "kmh",
    }

    try:
        r = requests.get(WEATHER_URL, params=params, timeout=10)
        data = r.json()
        h = data["hourly"]

        lines = [f"📍 Hourly Forecast — {geo['name']}, {geo['country']} (next {hours}h)\n"]
        for i in range(min(hours, len(h["time"]))):
            time_str = h["time"][i].replace("T", " ")
            temp = h["temperature_2m"][i]
            precip_prob = h["precipitation_probability"][i]
            code = h["weather_code"][i]
            wind = h["wind_speed_10m"][i]
            condition = WMO_CODES.get(code, "Unknown")
            lines.append(f"  {time_str}  {temp}°C  {condition}  🌧{precip_prob}%  💨{wind}km/h")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: Failed to fetch hourly data — {e}"


@mcp.tool()
def compare_weather(location1: str, location2: str) -> str:
    """
    Compare current weather between two locations.
    Example: compare_weather("New York", "London")
    """
    w1 = get_current_weather(location1)
    w2 = get_current_weather(location2)
    return f"--- {location1} ---\n{w1}\n\n--- {location2} ---\n{w2}"


if __name__ == "__main__":
    mcp.run(transport="stdio")