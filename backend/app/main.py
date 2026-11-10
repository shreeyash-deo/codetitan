import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base
from app.models import *  # Import all models to ensure metadata is populated
from app.routers import auth, workspaces, guidelines, rules, reviews, approvals, dashboard, health, compat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Automatically create tables if using SQLite or initial bootstrap
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="BrandShield AI - Enterprise Brand Governance & Content Compliance API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Health Probe
app.include_router(health.router)

# Core API Endpoints under /api
app.include_router(compat.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(guidelines.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# Also mount under /api/v1 for frontend client compatibility
app.include_router(compat.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(guidelines.router, prefix="/api/v1")
app.include_router(rules.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to BrandShield Governance API",
        "documentation": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
