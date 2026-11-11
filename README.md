# BrandShield (CodeTitan)

**BrandShield** is an AI-powered enterprise brand governance and content compliance platform. It ensures that marketing copy, advertising materials, and external communications adhere strictly to authoritative brand guidelines, regulatory disclaimers, terminology rules, and tone-of-voice standards before publication.

---

## Key Features & Architecture

- **Automated Compliance Engine**: Hybrid compliance validation combining deterministic regex matching and contextual LLM analysis (powered by Google Gemini) to identify prohibited claims, tone inconsistencies, and missing disclaimers.
- **Brand Knowledge Base**: Extraction pipeline for guideline documents (PDF, DOCX, TXT) that parses candidate brand rules for administrative review and approval.
- **Multi-Tier Human Governance**: Structured approval workflow with role-based sign-offs, change requests, and threaded feedback comments.
- **Role-Based Workspaces (RBAC)**:
  - **Admin**: Full workspace governance, document ingestion, candidate rule approval, member management, and organization telemetry.
  - **Reviewer**: Inspects submissions, reviews AI findings, requests revisions, and issues authoritative publishing approvals.
  - **Employee**: Content creation studio, live copy scanning, remediation recommendations, and personal submission tracking.
- **Immutable Audit Ledger**: Comprehensive historical record of all evaluated assets, compliance scores, reviewer actions, and version revisions.

---

## Technology Stack

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with custom design tokens
- **Routing**: React Router DOM (v7)
- **Animation**: Framer Motion
- **Icons**: Lucide React

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM & Database**: SQLAlchemy 2.0 with Alembic migrations; SQLite (development) and PostgreSQL (production) compatible
- **Authentication**: JWT (`pyjwt`) with `bcrypt` password hashing
- **Document Processing**: PyMuPDF (`fitz`), `python-docx`
- **AI Integration**: Google Gemini API (`gemini-2.0-flash` / `gemini-1.5-flash`) via structured JSON schema enforcement
- **Testing**: Pytest with HTTPX / Starlette TestClient (173 passing automated tests)

---

## Project Structure

```
codetitan/
├── backend/
│   ├── alembic/              # Database migration scripts and versions
│   ├── app/
│   │   ├── core/             # Configuration, database session, JWT security, RBAC dependencies
│   │   ├── models/           # SQLAlchemy 2.0 ORM data models
│   │   ├── routers/          # FastAPI REST endpoints (auth, workspaces, guidelines, rules, reviews, approvals, dashboard)
│   │   ├── schemas/          # Pydantic v2 request/response schemas
│   │   ├── services/         # Business logic, AI providers, and compliance evaluation engine
│   │   └── utils/            # Document text extractors (PDF, DOCX, TXT)
│   ├── tests/                # Automated pytest test suites
│   ├── .env.example          # Backend environment template (placeholders only)
│   ├── alembic.ini           # Alembic migration configuration
│   └── requirements.txt      # Python dependencies
├── src/
│   ├── components/           # Reusable UI, dashboard, studio, and layout components
│   ├── context/              # React context providers (Auth, Governance, Toast)
│   ├── data/                 # Navigation configuration and mock presets
│   ├── hooks/                # Custom React hooks (useWorkspace, useSidebar)
│   ├── pages/                # Page components (Overview, ContentReview, BrandGuidelines, ReviewHistory, TeamApprovals, Settings)
│   ├── services/             # API client services connecting to FastAPI backend
│   └── types/                # TypeScript interface definitions
├── .env.example              # Frontend environment template (placeholders only)
├── package.json              # Frontend dependencies and build scripts
├── vite.config.ts            # Vite bundler configuration
└── README.md
```

---

## Environment Configuration

### Frontend Configuration (`.env`)
Create a `.env` file in the root directory based on `.env.example`:

```ini
# Backend API Base URL
VITE_API_BASE_URL=http://localhost:8000

# Set to 'false' to communicate with the live FastAPI backend
VITE_USE_MOCK_DATA=false
```

### Backend Configuration (`backend/.env`)
Create a `.env` file in the `backend/` directory based on `backend/.env.example`:

```ini
# Database (SQLite for local development, PostgreSQL for production)
DATABASE_URL=sqlite:///./brandshield.db

# Authentication Security (Generate a secure 32+ character key for production)
SECRET_KEY=change-this-to-a-super-secret-random-key-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS & Frontend Origin
FRONTEND_URL=http://localhost:5173

# Application Settings
ENVIRONMENT=development
PROJECT_NAME="BrandShield API"
UPLOAD_DIR=./uploads

# AI Provider Configuration
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
AI_TEMPERATURE=0.2
AI_TIMEOUT=45
AI_MAX_RETRIES=2
```

---

## Getting Started (Local Development)

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Git

### 1. Backend Setup

1. Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the backend development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The interactive Swagger documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup

1. From the project root directory, install dependencies:
   ```bash
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173`.

---

## Validation & Testing

### Running Frontend Production Build
```bash
npm run build
```

### Running Backend Test Suite
```bash
cd backend
python -m pytest
```

---

## License

Proprietary — Developed for Enterprise Brand Governance and Content Compliance.
