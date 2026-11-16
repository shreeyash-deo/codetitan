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
        import hashlib
        from sqlalchemy import inspect, text
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            if "content_reviews" in tables:
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
                if "current_version_number" not in columns:
                    conn.execute(text("ALTER TABLE content_reviews ADD COLUMN current_version_number INTEGER DEFAULT 1 NOT NULL"))
                # Ensure legacy records without an audited content hash are never marked verified
                conn.execute(text("UPDATE content_reviews SET audit_status = 'unverified' WHERE audited_content_hash IS NULL"))

            if "findings" in tables:
                finding_cols = [c["name"] for c in inspector.get_columns("findings")]
                if "version_id" not in finding_cols:
                    conn.execute(text("ALTER TABLE findings ADD COLUMN version_id INTEGER REFERENCES content_versions(id) ON DELETE CASCADE"))

            if "approvals" in tables:
                approval_cols = [c["name"] for c in inspector.get_columns("approvals")]
                if "version_number" not in approval_cols:
                    conn.execute(text("ALTER TABLE approvals ADD COLUMN version_number INTEGER"))

            if "content_versions" in tables and "content_reviews" in tables:
                # Backfill any legacy reviews missing a baseline ContentVersion
                reviews = conn.execute(text(
                    "SELECT id, content, original_content, compliance_score, status, audit_status, "
                    "audited_content_hash, findings_count, rule_set_version, summary, submitted_by, created_at "
                    "FROM content_reviews"
                )).fetchall()

                for r in reviews:
                    existing = conn.execute(
                        text("SELECT id FROM content_versions WHERE review_id = :rid AND version_number = 1"),
                        {"rid": r[0]}
                    ).fetchone()
                    if not existing:
                        content_str = r[1] or ""
                        orig_str = r[2] or ""
                        exp_hash = hashlib.sha256(content_str.strip().encode("utf-8")).hexdigest()
                        change_desc = "Legacy Snapshot" if (orig_str and orig_str != content_str) else "Initial Submission"
                        actual_audit_status = r[5] if (r[6] and r[6] == exp_hash and r[5] in ("verified", "degraded")) else "unverified"
                        
                        conn.execute(
                            text(
                                "INSERT INTO content_versions (review_id, version_number, content, content_hash, "
                                "compliance_score, status, audit_status, findings_count, rule_set_version, summary, "
                                "change_description, author_id, created_at) "
                                "VALUES (:rid, 1, :content, :hash, :score, :status, :audit_status, :f_count, "
                                ":rule_ver, :summary, :desc, :author, COALESCE(:created_at, CURRENT_TIMESTAMP))"
                            ),
                            {
                                "rid": r[0],
                                "content": content_str,
                                "hash": r[6] or exp_hash,
                                "score": r[3] if r[3] is not None else 100,
                                "status": r[4] or "in_review",
                                "audit_status": actual_audit_status,
                                "f_count": r[7] or 0,
                                "rule_ver": r[8],
                                "summary": r[9],
                                "desc": change_desc,
                                "author": r[10],
                                "created_at": r[11],
                            }
                        )
                        v1 = conn.execute(
                            text("SELECT id FROM content_versions WHERE review_id = :rid AND version_number = 1"),
                            {"rid": r[0]}
                        ).fetchone()
                        if v1:
                            conn.execute(
                                text("UPDATE findings SET version_id = :vid WHERE review_id = :rid AND version_id IS NULL"),
                                {"vid": v1[0], "rid": r[0]}
                            )
                        conn.execute(
                            text("UPDATE approvals SET version_number = 1 WHERE review_id = :rid AND version_number IS NULL"),
                            {"rid": r[0]}
                        )

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
app.include_router(approvals.router, prefix="/api")
app.include_router(compat.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(guidelines.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
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
