from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

WEATHER_URL = "http://weather-service:8000/weather"
WEATHER_TIMEOUT = 5.0

app = FastAPI(title="WeatherHub Planner Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WeatherPayload(BaseModel):
    city: Optional[str] = None
    condition: Optional[str] = None
    temp_c: Optional[float] = None
    source: Optional[str] = None


async def fetch_weather(city: str) -> WeatherPayload:
    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT) as client:
            resp = await client.get(WEATHER_URL, params={"city": city})
            resp.raise_for_status()
            data = resp.json()
            return WeatherPayload(
                city=data.get("city") or city,
                condition=data.get("condition"),
                temp_c=data.get("temp_c"),
                source=data.get("source"),
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"weather-service error: {exc}") from exc


def build_activities(condition: str) -> List[str]:
    cond = (condition or "").strip().lower()
    if cond == "sunny":
        return ["Walk", "Picnic"]
    if cond == "cloudy":
        return ["Museum", "Coffee"]
    if cond == "rainy":
        return ["Cinema", "Board games"]
    if cond == "snowy":
        return ["Ski", "Hot chocolate"]
    return ["Weather looks calm — schedule your plans as usual."]


def build_response(weather: WeatherPayload) -> Dict[str, Any]:
    if weather.condition is None or weather.temp_c is None:
        raise HTTPException(status_code=502, detail="planner requires condition and temp_c")
    return {
        "city": weather.city,
        "condition": weather.condition,
        "temp_c": weather.temp_c,
        "weather_source": weather.source,
        "activities": build_activities(weather.condition),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/plan")
async def plan_get(city: str = Query(..., min_length=1)):
    weather = await fetch_weather(city)
    return build_response(weather)


@app.post("/plan")
async def plan_post(payload: WeatherPayload):
    # Support existing gateway contract: if condition/temp missing, fetch by city
    if payload.condition is None or payload.temp_c is None:
        if not payload.city:
            raise HTTPException(status_code=400, detail="city is required when condition/temp_c absent")
        payload = await fetch_weather(payload.city)
    return build_response(payload)
