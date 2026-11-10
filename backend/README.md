# BrandShield Backend

**BrandShield** is an AI-powered enterprise brand governance and content compliance platform. This backend provides a high-performance, maintainable REST API built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL** (with zero-config SQLite support for development), **Alembic**, and **JWT authentication**.

---

## Technology Stack

- **Python**: 3.11+ (CPython 3.12 verified)
- **Framework**: FastAPI
- **Database**: PostgreSQL (with SQLite compatibility for local testing)
- **ORM**: SQLAlchemy 2.0 (type-annotated models)
- **Migrations**: Alembic
- **Validation & Settings**: Pydantic v2 & `pydantic-settings`
- **Security**: JWT (`pyjwt`) & password hashing (`bcrypt`)
- **Document Processing**: PyMuPDF (`fitz`), `python-docx`
- **AI Providers**: Gemini (`gemini-2.0-flash`), DeepSeek (`deepseek-chat`)
- **Server**: Uvicorn
- **Testing**: Pytest & Starlette/HTTPX TestClient (24 passing tests)

---

## Directory Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings & environment variables
│   │   ├── database.py       # SQLAlchemy engine, session maker, Base declarative
│   │   ├── dependencies.py   # JWT auth, role validation & workspace verification
│   │   └── security.py       # bcrypt hashing and JWT encoding/decoding
│   ├── models/
│   │   ├── user.py           # User accounts & roles
│   │   ├── workspace.py      # Multi-tenant brand workspaces
│   │   ├── workspace_member.py # Workspace membership & permissions
│   │   ├── guideline.py      # Guideline document records & extracted text
│   │   ├── rule.py           # Approved & candidate brand rules
│   │   ├── review.py         # Submitted content reviews & audits
│   │   ├── finding.py        # Compliance violations & suggestions
│   │   ├── approval.py       # Multi-tier approval requests & decisions
│   │   └── activity.py       # Audit trail & timeline events
│   ├── schemas/              # Pydantic request/response models
│   ├── routers/
│   │   ├── auth.py           # /api/auth (register, login, me, logout)
│   │   ├── workspaces.py     # /api/workspaces (CRUD & members)
│   │   ├── guidelines.py     # /api/workspaces/{id}/guidelines (PDF/DOCX/TXT upload)
│   │   ├── rules.py          # /api/workspaces/{id}/rules (CRUD & approve/reject)
│   │   ├── reviews.py        # /api/workspaces/{id}/reviews (Audit, filter, correct)
│   │   ├── approvals.py      # /api/workspaces/{id}/approvals & /api/approvals
│   │   ├── dashboard.py      # /api/workspaces/{id}/dashboard (live metrics)
│   │   ├── compat.py         # Frontend integration bridge (/brands, /guidelines, /reviews/scan, /history)
│   │   └── health.py         # /health system probe
│   ├── services/
│   │   ├── ai/               # AI Provider abstraction (Gemini & DeepSeek)
│   │   ├── compliance/       # Hybrid Compliance Engine (Deterministic + AI contextual checks)
│   │   ├── auth_service.py   # User and credential business logic
│   │   ├── rule_service.py   # Rule approval, deduplication & lifecycle
│   │   ├── review_service.py # Review auditing, finding status, & scoring
│   │   ├── approval_service.py # Workflow routing & role-based approvals
│   │   ├── dashboard_service.py# Live aggregated governance metrics
│   │   └── workspace_service.py# Multi-tenant workspace management
│   ├── utils/
│   │   └── extractor.py      # PyMuPDF, python-docx & text extraction
│   └── main.py               # FastAPI application, CORS & router mounting
├── alembic/                  # Database migration scripts
├── tests/                    # Pytest test suite (24 passing tests)
├── uploads/                  # Uploaded guidelines & documents storage
├── requirements.txt
├── .env.example
├── pytest.ini
└── README.md
```

---

## Quickstart & Setup Commands

### 1. Activate Environment

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```ini
DATABASE_URL=sqlite:///./brandshield.db
SECRET_KEY=brandshield-super-secret-development-jwt-key-2026-secure
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FRONTEND_URL=http://localhost:5173
AI_PROVIDER=gemini
AI_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your_gemini_key_here
```

### 3. Run Migrations

```powershell
alembic upgrade head
```

### 4. Start the FastAPI Server

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive documentation will be available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running the Automated Test Suite

Run all 24 unit and integration tests:

```powershell
python -m pytest backend/tests -v
```
