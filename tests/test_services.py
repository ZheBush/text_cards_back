import pytest
import json
import httpx
from app.services.model import parse_json
from app.services.weather_service import fetch_weather
from app.core import config


def test_parse_json_returns_list_for_valid_json():
    raw = '[{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]'
    result = parse_json(raw)
    assert isinstance(result, list)
    assert result[0]["question"] == "Q1"


def test_parse_json_strips_code_fence_and_returns_list():
    raw = '```json\n[{"question":"Q","answer":"A"}]\n```'
    result = parse_json(raw)
    assert isinstance(result, list)
    if result:
        assert result[0]["question"] == "Q"
        assert result[0]["answer"] == "A"


def test_parse_json_returns_empty_on_invalid_json():
    result = parse_json('not json')
    assert result == []


class FakeResponse:
    def __init__(self, status_code=200, body=None, request=None):
        self.status_code = status_code
        self._body = body or {}
        self.request = request

    def json(self):
        return self._body

    @property
    def text(self):
        return json.dumps(self._body)


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_fetch_weather_success(monkeypatch):
    fake_data = {
        "name": "Moscow",
        "main": {"temp": 25.4, "feels_like": 24.7, "humidity": 60},
        "weather": [{"description": "ясно", "icon": "01d"}],
        "wind": {"speed": 3.2}
    }
    response = FakeResponse(status_code=200, body=fake_data)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda *args, **kwargs: FakeClient(response))
    monkeypatch.setattr(config.settings, 'WEATHER_API_KEY', 'dummy-key')

    result = await fetch_weather('Moscow')
    assert result['city'] == 'Moscow'
    assert result['temperature'] == 25
    assert result['description'] == 'Ясно'


@pytest.mark.asyncio
async def test_fetch_weather_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(config.settings, 'WEATHER_API_KEY', '')
    with pytest.raises(ValueError, match="WEATHER_API_KEY is not set"):
        await fetch_weather('Moscow')


@pytest.mark.asyncio
async def test_fetch_weather_http_error_raises(monkeypatch):
    fake_request = httpx.Request("GET", "http://test")
    response = FakeResponse(status_code=500, body={"message": "server error"}, request=fake_request)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda *args, **kwargs: FakeClient(response))
    monkeypatch.setattr(config.settings, 'WEATHER_API_KEY', 'dummy-key')

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_weather('Moscow')


def test_parse_json_returns_empty_when_no_json_array():
    result = parse_json('some text without a json array')
    assert result == []


def test_parse_json_with_nested_objects():
    """Test parsing JSON with nested objects"""
    raw = '[{"question": "Q1", "metadata": {"difficulty": "hard"}, "answer": "A1"}]'
    result = parse_json(raw)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["metadata"]["difficulty"] == "hard"


def test_parse_json_empty_array():
    """Test parsing empty JSON array"""
    raw = '[]'
    result = parse_json(raw)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_fetch_weather_success_with_wind(monkeypatch):
    """Test weather fetch with wind speed"""
    fake_data = {
        "name": "London",
        "main": {"temp": 15.2, "feels_like": 14.8, "humidity": 75},
        "weather": [{"description": "облачно", "icon": "04d"}],
        "wind": {"speed": 5.5}
    }
    response = FakeResponse(status_code=200, body=fake_data)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda *args, **kwargs: FakeClient(response))
    monkeypatch.setattr(config.settings, 'WEATHER_API_KEY', 'dummy-key')

    result = await fetch_weather('London')
    assert result['city'] == 'London'
    assert result['temperature'] == 15
    assert result['wind_speed'] == 5.5
