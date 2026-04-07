import httpx
from fastapi import APIRouter, HTTPException, Query
from app.services.weather_service import fetch_weather

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("")
async def get_weather(city: str = Query("Moscow", description="City name")):
    try:
        weather = await fetch_weather(city)
        return weather
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Weather service timeout")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="City not found")
        raise HTTPException(status_code=502, detail="Weather service error")
    except Exception as e:
        print(f"Weather error: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=503, detail=f"Weather service unavailable: {str(e)}")