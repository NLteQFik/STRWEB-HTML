from unittest.mock import Mock, patch

import pytest
import requests

from requests.exceptions import ConnectionError, Timeout

from hotel.services import (
    fetch_currency_rates,
    fetch_weather_data,
    get_external_data,
    get_weather_data,
)


def test_get_weather_data_success():
    mocked_response = Mock()
    mocked_response.raise_for_status.return_value = None
    mocked_response.json.return_value = {
        "current": {"temperature_2m": 12.5, "relative_humidity_2m": 50, "weather_code": 0}
    }

    with patch("hotel.services.requests.get", return_value=mocked_response):
        data = get_weather_data(city="Minsk")

    assert data["has_error"] is False
    assert data["temperature_c"] == 12.5
    assert data["description"] == "Ясно"
    assert data["humidity"] == 50


def test_get_weather_data_connection_error_returns_stub():
    with patch("hotel.services.requests.get", side_effect=requests.exceptions.ConnectionError):
        data = get_weather_data(city="Minsk")
    assert data["has_error"] is True


def test_get_external_data_timeout_returns_stub():
    with patch("hotel.services.requests.get", side_effect=requests.exceptions.Timeout):
        data = get_external_data(base="BYN")
    assert data["has_error"] is False
    assert data["USD"] == 3.20


def test_get_external_data_success():
    mocked = Mock()
    mocked.raise_for_status.return_value = None
    mocked.json.return_value = {
        "base_code": "BYN",
        "rates": {"USD": 0.31, "EUR": 0.29, "CNY": 2.25, "RUB": 23.5},
    }
    with patch("hotel.services.requests.get", return_value=mocked):
        data = get_external_data(base="BYN")
    assert data["has_error"] is False
    assert data["USD"] == 3.23


def test_get_weather_data_outer_except():
    with patch("hotel.services.fetch_weather_data", side_effect=ConnectionError):
        data = get_weather_data(city="Minsk")
    assert data["has_error"] is True


def test_get_external_data_outer_except():
    with patch("hotel.services.fetch_currency_rates", side_effect=Timeout):
        data = get_external_data(base="BYN")
    assert data["has_error"] is False
    assert data["USD"] == 3.20


def test_fetch_currency_rates_success():
    mocked = Mock()
    mocked.raise_for_status.return_value = None
    mocked.json.return_value = {
        "base_code": "BYN",
        "rates": {"USD": 0.31, "EUR": 0.29, "CNY": 2.25, "RUB": 23.5},
    }
    with patch("hotel.services.requests.get", return_value=mocked):
        data = fetch_currency_rates(base="BYN")
    assert data["has_error"] is False
    assert data["base"] == "BYN"
    assert data["USD"] == 3.23
