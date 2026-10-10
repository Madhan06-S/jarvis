"""
JARVIS Weather Skill — Open-Meteo Integration
"""
import re
import httpx
from typing import Dict, Any, Optional

NAME = "Weather"
DESCRIPTION = "Live weather forecast & temperature using Open-Meteo (No API key required)"
TRIGGERS = ["weather", "temperature", "forecast", "is it raining", "how hot", "how cold", "climate"]

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
}

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()
    
    # Extract city name from query
    city = "Mumbai" # Default location
    city_match = re.search(r"(?:in|for|at|around)\s+([a-zA-Z\s]+)", t)
    if city_match:
        extracted = city_match.group(1).strip()
        if not any(w in extracted for w in ["today", "tomorrow", "now", "this week"]):
            city = extracted

    lat, lon, display_name = 19.0760, 72.8777, city.capitalize() # Default Mumbai
    
    # Geocode city
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            geo_res = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json")
            if geo_res.status_code == 200:
                geo_data = geo_res.json()
                if geo_data.get("results"):
                    res = geo_data["results"][0]
                    lat = res["latitude"]
                    lon = res["longitude"]
                    display_name = f"{res['name']}, {res.get('country_code', '').upper()}"
    except Exception as e:
        print(f"[Weather Skill] Geocode error: {e}")

    # Fetch weather details
    temp, humidity, condition, forecast = 24.0, 65, "Clear sky", []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            w_res = await client.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
            )
            if w_res.status_code == 200:
                w_data = w_res.json()
                current = w_data.get("current", {})
                temp = current.get("temperature_2m", 24.0)
                humidity = current.get("relative_humidity_2m", 65)
                w_code = current.get("weather_code", 0)
                condition = WEATHER_CODES.get(w_code, "Partly cloudy")
                
                daily = w_data.get("daily", {})
                dates = daily.get("time", [])[:3]
                maxs = daily.get("temperature_2m_max", [])[:3]
                mins = daily.get("temperature_2m_min", [])[:3]
                codes = daily.get("weather_code", [])[:3]
                
                for i in range(len(dates)):
                    forecast.append({
                        "date": dates[i],
                        "max_temp": maxs[i] if i < len(maxs) else temp,
                        "min_temp": mins[i] if i < len(mins) else temp - 5,
                        "condition": WEATHER_CODES.get(codes[i] if i < len(codes) else 0, "Clear")
                    })
    except Exception as e:
        print(f"[Weather Skill] Weather API error: {e}")

    spoken = f"Currently in {display_name}, it is {temp:.0f}°C with {condition.lower()} and {humidity}% humidity."
    
    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "weather",
            "title": f"WEATHER — {display_name.upper()}",
            "data": {
                "city": display_name,
                "temp": f"{temp:.0f}°C",
                "condition": condition,
                "humidity": f"{humidity}%",
                "forecast": forecast
            }
        },
        "action": None
    }
