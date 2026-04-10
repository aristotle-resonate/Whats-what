from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router

app = FastAPI(title="Whats-What API", version="0.1.0")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(onboarding_router)
