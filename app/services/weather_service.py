import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

DEFAULT_CITY = "Moscow"
TIMEOUT = 5.0


def is_retryable_exception(exception):
    return isinstance(exception, (httpx.TimeoutException, httpx.ConnectError))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5),
       retry=retry_if_exception_type(httpx.TimeoutException))
async def fetch_weather(city: str = DEFAULT_CITY) -> dict:
    if not settings.WEATHER_API_KEY:
        raise ValueError("WEATHER_API_KEY is not set")

    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(settings.WEATHER_API_URL, params=params)

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", "Unknown error")
            except:
                error_msg = response.text
            raise httpx.HTTPStatusError(
                f"Weather API error: {error_msg} (status {response.status_code})",
                request=response.request,
                response=response
            )

        data = response.json()
        required_keys = ["main", "weather", "wind", "name"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Weather API response missing '{key}' field")

        return {
            "city": data["name"],
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"].capitalize(),
            "icon": data["weather"][0]["icon"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
        }