import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WeatherHub Weather Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONDITIONS = ["Sunny", "Cloudy", "Rainy", "Snowy"]

PROVIDER = os.getenv("WEATHER_PROVIDER", "open-meteo").lower()
TIMEOUT_SEC = float(os.getenv("WEATHER_TIMEOUT_SEC", "3"))
FALLBACK_TO_MOCK = os.getenv("WEATHER_FALLBACK_TO_MOCK", "true").lower() in {"1", "true", "yes"}

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 60  # seconds


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _condition_from_code(code: int) -> str:
    if code == 0:
        return "Sunny"
    if code in {1, 2, 3, 45, 48}:
        return "Cloudy"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "Rainy"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "Snowy"
    return "Cloudy"


def _mock_weather(city: str) -> Dict[str, Any]:
    digest = hashlib.sha256(city.encode("utf-8")).digest()
    cond = CONDITIONS[digest[0] % len(CONDITIONS)]
    temp_c = 10 + (digest[1] % 21)  # 10..30 inclusive
    return {
        "city": city.title(),
        "condition": cond,
        "temp_c": temp_c,
        "source": "mock",
        "updated_at": _now_iso(),
    }


async def _fetch_open_meteo(city: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_resp = await client.get(geo_url)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        results = geo_data.get("results") or []
        if not results:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        res0 = results[0]
        lat = res0["latitude"]
        lon = res0["longitude"]
        city_name = res0.get("name", city).title()

        wx_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        )
        wx_resp = await client.get(wx_url)
        wx_resp.raise_for_status()
        current = wx_resp.json().get("current") or {}
        temperature = current.get("temperature_2m")
        code = current.get("weather_code", -1)

    condition = _condition_from_code(int(code))
    temp_value = float(temperature) if temperature is not None else None
    if temp_value is None:
        raise HTTPException(status_code=502, detail="Open-Meteo returned no temperature")

    return {
        "city": city_name,
        "condition": condition,
        "temp_c": temp_value,
        "source": "open-meteo",
        "updated_at": _now_iso(),
    }


async def _get_weather(city: str) -> Dict[str, Any]:
    key = city.strip().lower()
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    if PROVIDER == "mock":
        data = _mock_weather(city)
    else:
        try:
            data = await _fetch_open_meteo(city)
        except HTTPException:
            raise
        except Exception as exc:
            if FALLBACK_TO_MOCK:
                data = _mock_weather(city)
                data["source"] = "mock"
            else:
                raise HTTPException(status_code=502, detail=f"weather provider error: {exc}") from exc

    _CACHE[key] = (now, data)
    return data


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/provider")
async def provider():
    return {"provider": PROVIDER, "fallback_to_mock": FALLBACK_TO_MOCK, "timeout_sec": TIMEOUT_SEC}


@app.get("/weather")
async def weather(city: str = Query(..., min_length=1)):
    return await _get_weather(city)
