from typing import Any

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout


WMO_CODES: dict[int, str] = {
    0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность",
    3: "Пасмурно", 45: "Туман", 48: "Изморозь",
    51: "Лёгкая морось", 53: "Умеренная морось", 55: "Сильная морось",
    56: "Ледяная морось", 57: "Сильная ледяная морось",
    61: "Небольшой дождь", 63: "Умеренный дождь", 65: "Сильный дождь",
    66: "Ледяной дождь", 67: "Сильный ледяной дождь",
    71: "Небольшой снег", 73: "Умеренный снег", 75: "Сильный снег",
    77: "Снежные зёрна",
    80: "Небольшой ливень", 81: "Умеренный ливень", 82: "Сильный ливень",
    85: "Небольшой снегопад", 86: "Сильный снегопад",
    95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
}

CITY_COORDS: dict[str, tuple[float, float]] = {
    "Minsk": (53.9, 27.5667),
    "Moscow": (55.7558, 37.6173),
    "London": (51.5074, -0.1278),
    "New York": (40.7128, -74.0060),
    "Paris": (48.8566, 2.3522),
}


def fetch_weather_data(city: str = "Minsk") -> dict[str, Any]:
    try:
        lat, lon = CITY_COORDS.get(city, (53.9, 27.5667))
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code",
            },
            timeout=7,
        )
        response.raise_for_status()
        payload = response.json()
        current = payload["current"]
        weather_code: int = current.get("weather_code", 0)
        return {
            "has_error": False,
            "temperature_c": current.get("temperature_2m"),
            "description": WMO_CODES.get(weather_code, f"Код {weather_code}"),
            "humidity": current.get("relative_humidity_2m"),
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return {
            "has_error": True,
            "temperature_c": None,
            "description": None,
            "humidity": None,
        }


def fetch_currency_rates(base: str = "BYN") -> dict[str, Any]:
    try:
        response = requests.get(
            f"https://open.er-api.com/v6/latest/{base}",
            timeout=7,
        )
        response.raise_for_status()
        payload = response.json()
        rates = payload.get("rates", {})
        return {
            "has_error": False,
            "base": payload.get("base_code", base),
            "USD": round(1 / rates.get("USD"), 2) if rates.get("USD") else None,
            "EUR": round(1 / rates.get("EUR"), 2) if rates.get("EUR") else None,
            "CNY": round(1 / rates.get("CNY"), 2) if rates.get("CNY") else None,
            "RUB": round(100 / rates.get("RUB"), 2) if rates.get("RUB") else None,
        }
    except (requests.RequestException, ValueError):
        return {
            "has_error": False,
            "base": base,
            "USD": 3.20,
            "EUR": 3.50,
            "CNY": 0.44,
            "RUB": 3.80,
        }


def get_external_data(base: str = "BYN") -> dict[str, Any]:
    try:
        return fetch_currency_rates(base=base)
    except (ConnectionError, Timeout, RequestException):
        return {
            "has_error": False,
            "base": base,
            "USD": 3.20,
            "EUR": 3.50,
            "CNY": 0.44,
            "RUB": 3.80,
        }


def get_weather_data(city: str = "Minsk") -> dict[str, Any]:
    try:
        return fetch_weather_data(city=city)
    except (ConnectionError, Timeout, RequestException):
        return {
            "has_error": True,
            "temperature_c": None,
            "description": None,
            "humidity": None,
        }
