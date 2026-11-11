import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base
from app.models import *  # Import all models to ensure metadata is populated
from app.routers import auth, workspaces, guidelines, rules, reviews, approvals, dashboard, health, compat


def ensure_schema_upgrades():
    """
    Lightweight schema synchronization for local development.
    In production environments (e.g. PostgreSQL), migrations are managed by Alembic.
    """
    if engine.dialect.name != "sqlite":
        return

    try:
        from sqlalchemy import inspect, text
        with engine.connect() as conn:
            inspector = inspect(conn)
            if "content_reviews" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("content_reviews")]
                if "audit_status" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN audit_status VARCHAR(50) DEFAULT 'unverified' NOT NULL"))
                if "audited_content_hash" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN audited_content_hash VARCHAR(64)"))
                if "audited_at" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN audited_at TIMESTAMP"))
                if "findings_count" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN findings_count INTEGER DEFAULT 0 NOT NULL"))
                if "rule_set_version" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN rule_set_version VARCHAR(100)"))
                # Ensure legacy records without an audited content hash are never marked verified
                conn.execute(text("UPDATE content_reviews SET audit_status = 'unverified' WHERE audited_content_hash IS NULL"))
                conn.commit()
    except Exception as exc:
        print(f"Schema upgrade notice: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists (supports local dev or mounted Persistent Disk)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Automatically create tables if using SQLite or initial bootstrap
    Base.metadata.create_all(bind=engine)
    ensure_schema_upgrades()
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
