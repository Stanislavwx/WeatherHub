import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "weatherhub"),
    "user": os.getenv("POSTGRES_USER", "weatherhub"),
    "password": os.getenv("POSTGRES_PASSWORD", "weatherhub"),
}

app = FastAPI(title="WeatherHub History Service")

pool: Optional[asyncpg.Pool] = None


async def init_db():
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_requests (
                id SERIAL PRIMARY KEY,
                city TEXT NOT NULL,
                condition TEXT NOT NULL,
                temp_c INT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                city TEXT NOT NULL,
                condition TEXT NOT NULL,
                activities JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(**DB_CONFIG, timeout=5)
    await init_db()


class WeatherIn(BaseModel):
    city: str
    condition: str
    temp_c: int


class PlanIn(BaseModel):
    city: str
    condition: str
    activities: List[str] = Field(default_factory=list)


class RecordIn(BaseModel):
    city: str
    weather: Dict[str, Any]
    plan: Optional[Dict[str, Any]] = None


async def insert_weather(rec: WeatherIn) -> Dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO weather_requests (city, condition, temp_c) VALUES ($1, $2, $3) RETURNING id, created_at;",
            rec.city,
            rec.condition,
            rec.temp_c,
        )
        return {"id": row["id"], "created_at": row["created_at"].isoformat()}


async def insert_plan(rec: PlanIn) -> Dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO plans (city, condition, activities) VALUES ($1, $2, $3::jsonb) RETURNING id, created_at;",
            rec.city,
            rec.condition,
            json.dumps(rec.activities),
        )
        return {"id": row["id"], "created_at": row["created_at"].isoformat()}


@app.get("/health")
async def health():
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1;")
        return {"status": "ok", "db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/history/weather")
async def create_weather(rec: WeatherIn):
    return await insert_weather(rec)


@app.get("/history/weather")
async def list_weather(limit: int = Query(20, ge=1, le=100)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, city, condition, temp_c, created_at FROM weather_requests ORDER BY created_at DESC LIMIT $1;",
            limit,
        )
    return [dict(r) for r in rows]


@app.post("/history/plans")
async def create_plan(rec: PlanIn):
    return await insert_plan(rec)


@app.get("/history/plans")
async def list_plans(limit: int = Query(20, ge=1, le=100)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, city, condition, activities, created_at FROM plans ORDER BY created_at DESC LIMIT $1;",
            limit,
        )
    result = []
    for r in rows:
        item = dict(r)
        activities = item.get("activities")
        if isinstance(activities, str):
            try:
                item["activities"] = json.loads(activities)
            except json.JSONDecodeError:
                item["activities"] = activities
        result.append(item)
    return result


@app.post("/records")
async def create_records(rec: RecordIn):
    # Backward-compatible endpoint used by gateway; stores into new tables.
    weather = rec.weather or {}
    plan = rec.plan or {}
    weather_payload = WeatherIn(
        city=weather.get("city", rec.city),
        condition=weather.get("condition") or "Unknown",
        temp_c=int(weather.get("temp_c") or 0),
    )
    weather_res = await insert_weather(weather_payload)

    plan_res = None
    if plan:
        plan_payload = PlanIn(
            city=plan.get("city", rec.city),
            condition=plan.get("condition") or weather_payload.condition,
            activities=plan.get("activities") or [],
        )
        plan_res = await insert_plan(plan_payload)

    response: Dict[str, Any] = {"weather_id": weather_res["id"], "weather_created_at": weather_res["created_at"]}
    if plan_res:
        response["plan_id"] = plan_res["id"]
        response["plan_created_at"] = plan_res["created_at"]
    return response


@app.get("/records")
async def list_records(limit: int = Query(20, ge=1, le=100)):
    # Returns combined view of latest weather + plan entries (separate).
    weather = await list_weather(limit)
    plans = await list_plans(limit)
    return {"weather": weather, "plans": plans, "generated_at": datetime.now(timezone.utc).isoformat()}
