import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WeatherHub Cloudflare API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://weather-service:8000")
PLANNER_SERVICE_URL = os.getenv("PLANNER_SERVICE_URL", "http://planner-service:8000")
HISTORY_SERVICE_URL = os.getenv("HISTORY_SERVICE_URL", "http://history-service:8000")


async def _ping(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(url)
        return "ok" if resp.status_code == 200 else f"bad:{resp.status_code}"
    except Exception as exc:  # pragma: no cover - runtime health helper
        return f"fail:{exc.__class__.__name__}"


async def _post_history_weather(client: httpx.AsyncClient, payload: Dict[str, Any]) -> None:
    try:
        await client.post(f"{HISTORY_SERVICE_URL}/history/weather", json=payload, timeout=5)
    except Exception:
        # Do not block main flow on history failures
        pass


async def _post_history_plan(client: httpx.AsyncClient, payload: Dict[str, Any]) -> None:
    try:
        await client.post(f"{HISTORY_SERVICE_URL}/history/plans", json=payload, timeout=5)
    except Exception:
        pass


@app.get("/health")
async def health() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=3) as client:
        return {
            "status": "ok",
            "weather": await _ping(client, f"{WEATHER_SERVICE_URL}/health"),
            "planner": await _ping(client, f"{PLANNER_SERVICE_URL}/health"),
            "history": await _ping(client, f"{HISTORY_SERVICE_URL}/health"),
        }


@app.get("/api/weather")
async def api_weather(city: str = Query(..., min_length=1)) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{WEATHER_SERVICE_URL}/weather", params={"city": city})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"weather-service error: {exc}") from exc

        weather_payload = {
            "city": data.get("city") or city,
            "condition": data.get("condition") or "",
            "temp_c": int(data.get("temp_c") or 0),
        }
        await _post_history_weather(client, weather_payload)
        return data


@app.get("/api/plan")
async def api_plan(city: str = Query(..., min_length=1)) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{PLANNER_SERVICE_URL}/plan", params={"city": city})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"planner-service error: {exc}") from exc

        plan_payload = {
            "city": data.get("city") or city,
            "condition": data.get("condition") or "",
            "activities": data.get("activities") or [],
        }
        await _post_history_plan(client, plan_payload)
        return data


@app.get("/api/history/weather")
async def api_history_weather(limit: int = Query(10, ge=1, le=100)):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{HISTORY_SERVICE_URL}/history/weather", params={"limit": limit})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"history-service error: {exc}") from exc


@app.get("/api/history/plans")
async def api_history_plans(limit: int = Query(10, ge=1, le=100)):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{HISTORY_SERVICE_URL}/history/plans", params={"limit": limit})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"history-service error: {exc}") from exc
