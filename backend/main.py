"""Backend API entrypoint (Cloud Run target - PLAN.md section 6 step 6).

Exposes read-only district risk data (backend/routers/districts.py) and the
three ADK agents as chat endpoints (backend/routers/chat.py) to the not-yet-built
admin console and farmer chat frontends.

Local dev: uvicorn backend.main:app --reload --port 8080
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import districts, chat

app = FastAPI(
    title="El Nino 2026 Decision Copilot API",
    description="District risk data + agent chat endpoints for the admin console and farmer advisory frontends.",
)

# Frontend origins: Firebase Hosting (prod) + Vite local dev (any port —
# Vite auto-increments past 5173 when it's already taken by another instance).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://climate-resilience-in.web.app",
        "https://climate-resilience-in.firebaseapp.com",
    ],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(districts.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok", "model": "gemini-2.5-flash"}
