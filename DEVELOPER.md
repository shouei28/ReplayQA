# Developer Guide for ReplayQA

This guide covers everything you need to obtain the source, build, test, and release the software.

---

## Table of Contents

1. [Obtaining the Source Code](#obtaining-the-source-code)
2. [Directory Structure](#directory-structure)
3. [Architecture Overview](#architecture-overview)
4. [Building the Software](#building-the-software)
5. [Running the Software](#running-the-software)
6. [API Endpoints](#api-endpoints)
7. [Database Management](#database-management)
8. [Testing the Software](#testing-the-software)
9. [Adding New Tests](#adding-new-tests)
10. [Building a Release](#building-a-release)
11. [Git Workflow & Pull Requests](#git-workflow--pull-requests)
12. [Code Style](#code-style)
13. [Troubleshooting](#troubleshooting)

---

## Obtaining the Source Code

ReplayQA is a single repository project containing both the backend and frontend.

```bash
# Clone the repository
git clone https://github.com/Jovewinston/ReplayQA.git
cd ReplayQA
```

To work on a specific release, checkout the corresponding tag:

```bash
git tag -l                    # List all tags
git checkout beta-release     # Checkout the beta release
```

---

## Directory Structure

```
ReplayQA/
├── backend/                          # Django REST API (Python)
│   ├── api/                          # Presentation / API layer
│   │   ├── views/                    # Views organized by domain
│   │   │   ├── pipeline.py           #   Test execution & live view endpoints
│   │   │   ├── recorder.py           #   Browser recorder session endpoints
│   │   │   ├── test_history.py       #   Test history CRUD
│   │   │   ├── saved_tests.py        #   Saved test definitions CRUD
│   │   │   ├── auth.py               #   Authentication & user profile
│   │   │   ├── admin.py              #   Admin management
│   │   │   └── misc.py               #   Health check, screenshots
│   │   └── urls.py                   # URL routing
│   ├── core/                         # Data layer
│   │   ├── models.py                 #   User, Test, TestExecution, TestResult
│   │   ├── serializers.py            #   DRF serializers
│   │   └── migrations/               #   Database migrations
│   ├── services/                     # Business logic layer
│   │   ├── browser_slot_manager.py   #   Browserbase concurrency management
│   │   ├── recorder/                 #   Recording service
│   │   │   ├── session_service.py    #     Browserbase session lifecycle
│   │   │   ├── recording_service.py  #     DOM listener injection & action capture
│   │   │   ├── summarize_steps.py    #     AI step summarization
│   │   │   └── state.py              #     In-memory session state
│   │   └── runner/                   #   Test execution service
│   │       ├── runner_service.py     #     Core test execution pipeline
│   │       ├── gemini_cua_service.py #     Gemini Computer-Use Agent integration
│   │       ├── evaluator_service.py  #     AI-powered pass/fail evaluation
│   │       ├── action_executor.py    #     Playwright action execution
│   │       ├── storage_service.py    #     Screenshot upload (Supabase)
│   │       └── tasks.py              #     Celery async task definitions
│   ├── replayqa/                     # Django project configuration
│   │   ├── settings.py               #   Main settings
│   │   ├── celery.py                 #   Celery app configuration
│   │   └── urls.py                   #   Root URL config
│   ├── tests/                        # Backend test suite
│   │   ├── conftest.py               #   Shared pytest fixtures
│   │   ├── test_models.py            #   Model unit tests
│   │   ├── test_views.py             #   API view tests
│   │   └── test_recorder.py          #   Recorder integration tests
│   ├── requirements.txt              # Python dependencies
│   ├── pytest.ini                    # Pytest configuration
│   └── manage.py                     # Django management script
│
├── frontend/                         # Next.js App Router (React + TypeScript)
│   ├── app/                          # App Router pages
│   │   ├── layout.tsx                #   Root layout
│   │   ├── page.tsx                  #   Landing page
│   │   ├── login/page.tsx            #   Login page
│   │   └── dashboard/               #   Dashboard section
│   │       ├── layout.tsx            #     Dashboard layout with sidebar
│   │       ├── overview/page.tsx     #     Overview / home
│   │       ├── tests/               #     Test management pages
│   │       ├── recorder/page.tsx     #     Browser recorder
│   │       ├── activity/page.tsx     #     Activity log
│   │       ├── scheduled/page.tsx    #     Scheduled tests
│   │       └── settings/page.tsx     #     User settings
│   ├── components/                   # Reusable React components
│   │   ├── dashboard/                #   Dashboard-specific components
│   │   ├── ui/                       #   Shadcn/UI primitives
│   │   └── recorder.tsx              #   Recorder component
│   ├── lib/                          # Shared utilities
│   │   ├── api.ts                    #   API client functions
│   │   ├── types.ts                  #   TypeScript type definitions
│   │   └── utils.ts                  #   Helper utilities
│   ├── tests/                        # Frontend test suite
│   ├── package.json                  # Node dependencies & scripts
│   ├── jest.config.js                # Jest test configuration
│   └── tsconfig.json                 # TypeScript configuration
│
├── .github/workflows/ci.yml         # CI/CD pipeline (GitHub Actions)
├── DEVELOPER.md                    # Developer guide
└── USER.md                         # User guide
```

---

## Architecture Overview

### System Architecture

```
┌─────────────┐
│   Client    │ (Next.js / React)
│  (Browser)  │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────┐
│      Django Backend             │
│  ┌──────────────────────────┐  │
│  │  Presentation/API Layer  │  │
│  │  (api/views/)            │  │
│  └───────────┬──────────────┘  │
│              ▼                  │
│  ┌──────────────────────────┐  │
│  │   Core Services Layer    │  │
│  │  • RecordingService      │  │
│  │  • RunnerService         │  │
│  │  • EvaluatorService      │  │
│  │  • SessionService        │  │
│  │  • BrowserSlotManager    │  │
│  └───────────┬──────────────┘  │
│              ▼                  │
│  ┌──────────────────────────┐  │
│  │   Data Access Layer      │  │
│  │  (core/models.py)        │  │
│  └───────────┬──────────────┘  │
└──────────────┼──────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌──────────────┐  ┌────────────┐
│  PostgreSQL  │  │   Redis    │
│   (Supabase) │  │  (Celery)  │
└──────────────┘  └────────────┘

External Services:
┌──────────────┐  ┌──────────────┐
│ Browserbase  │  │   Gemini     │
│  (Browser)   │  │  (AI Agent)  │
└──────────────┘  └──────────────┘
```

### Request Flows

**Recording a Test:**
```
1. User enters URL             → POST /api/v1/recorder/start
2. SessionService creates Browserbase session
3. RecordingService injects DOM listeners into the page
4. User interacts with the page (clicks, types, navigates)
5. Actions captured & summarized by AI  → GET /api/v1/recorder/<id>/recorded-actions
6. User saves test              → POST /api/saved-tests
7. Return test_id to client
```

**Running a Test:**
```
1. User clicks "Run"           → POST /api/run-pipeline
2. API creates TestExecution, dispatches Celery task, returns immediately
3. Celery worker picks up task
4. RunnerService creates Browserbase session + fetches live view URL
5. Gemini CUA agent executes steps in the browser
6. Screenshots captured after each agent turn (→ Supabase storage)
7. EvaluatorService analyzes results with Gemini
8. TestResult saved to database
9. Frontend polls GET /api/status/<id> every 3s for progress
10. Frontend fetches GET /api/results/<id> on completion
```

---

## Building the Software

ReplayQA does not have a compiled build step for development. The backend runs directly via Django's development server and the frontend uses Next.js's dev server with hot reload.

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.9+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| PostgreSQL | 14+ | Database (or use Supabase) |
| Redis | 6+ | Celery task queue broker |
| Git | any | Version control |

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env            # Then edit .env with your credentials
# Required keys: DATABASE_URL, SECRET_KEY, BROWSERBASE_API_KEY,
#                BROWSERBASE_PROJECT_ID, GEMINI_API_KEY

# Apply database migrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
# Create .env with:
#   NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Production Build (Frontend)

```bash
cd frontend
npm run build     # Creates optimized production bundle in .next/
npm run start     # Serves the production build
```

---

## Running the Software

### Quick Start (All Services)

Use the provided startup script to launch everything at once:

```bash
chmod +x start.sh
./start.sh
```

This starts Django, Celery worker, and Next.js dev server in parallel.

### Manual Start (Individual Services)

You need **four terminals** for full functionality:

```bash
# Terminal 1 — Redis (if not running as a system service)
redis-server
# you should install redis if command not found error

# Terminal 2 — Django backend
cd backend && source venv/bin/activate
python manage.py runserver          # → http://localhost:8000

# Terminal 3 — Celery worker (required for test execution)
cd backend && source venv/bin/activate
celery -A replayqa worker --loglevel=info

# Terminal 4 — Next.js frontend
cd frontend
npm run dev                         # → http://localhost:3000
```

> **Note:** Redis + Celery are required for test execution. Without them, tests will be queued but never processed.

### Celery Beat (Scheduled / Periodic Tasks)

If you need periodic task scheduling (e.g., scheduled test runs):

```bash
# Start Celery Beat alongside the worker (separate terminal)
celery -A replayqa beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Or combine worker + beat in one process (development only)
celery -A replayqa worker --beat --scheduler django --loglevel=info
```

**Creating periodic tasks:**
- **Management command:** `python manage.py create_test_periodic_task`
- **Django Admin:** Go to http://localhost:8000/admin/ → Periodic Tasks → Add
- **Programmatically:**
  ```python
  from django_celery_beat.models import PeriodicTask, IntervalSchedule

  schedule, _ = IntervalSchedule.objects.get_or_create(
      every=10, period=IntervalSchedule.SECONDS,
  )
  PeriodicTask.objects.create(
      interval=schedule, name='My Task',
      task='core.tasks.test_task', enabled=True,
  )
  ```

---

## API Endpoints

Views are organized by domain in `api/views/`. The API is mounted at `/api/`

### Pipeline Execution
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/run-pipeline` | Start a new test execution (returns immediately, runs async via Celery) |
| GET | `/api/status/<test_execution_id>` | Poll job status, progress, and messages |
| GET | `/api/results/<test_execution_id>` | Get full test results with step analysis |
| GET | `/api/live-view/<test_execution_id>/` | Get Browserbase live view URL for a running test |

### Test History
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tests` | List all executed tests for the current user |
| DELETE | `/api/<test_result_id>` | Delete a test execution and its results |

### Saved Tests
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/saved-tests` | Save a new test definition |
| GET | `/api/saved-tests` | Get all saved tests |
| GET | `/api/saved-tests/<test_id>` | Get a single saved test |
| PUT | `/api/saved-tests/<test_id>` | Update a saved test |
| DELETE | `/api/saved-tests/<test_id>` | Delete a saved test |

### Recorder
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/recorder/start` | Start a recorder session (returns `session_id`, `connect_url`, `live_view_url`) |
| GET | `/api/v1/recorder/<session_id>/live-view` | Get live view URL for a recorder session |
| POST | `/api/v1/recorder/<session_id>/start-recording` | Begin recording DOM actions |
| GET | `/api/v1/recorder/<session_id>/recorded-actions` | Get and clear the recorded actions queue |
| POST | `/api/v1/recorder/<session_id>/toggle-recording` | Toggle recording on/off |
| POST | `/api/v1/recorder/<session_id>/end` | End the recorder session |

### Other
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/me` | Get current user profile |
| POST | `/api/auth/logout` | Logout |
| GET/POST | `/api/admin` | Admin user management |
| GET | `/api/screenshot/<test_result_id>/<step>` | Serve a screenshot image |
| GET | `/api/health` | Health check |

---

## Database Management

### Creating & Applying Migrations

```bash
cd backend && source venv/bin/activate

# After modifying models.py
python manage.py makemigrations
python manage.py migrate

# View the SQL a migration will run
python manage.py sqlmigrate core 0001

# Rollback to a specific migration
python manage.py migrate core 0002
```

### Seeding Test Data

```bash
python manage.py seed_data
```

---

## Testing the Software

### Backend Tests (Pytest)

The backend uses **pytest** with **pytest-django**. Tests live in `backend/tests/`.

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage report (configured by default in pytest.ini)
pytest --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_models.py

# Run a single test function
pytest tests/test_models.py::test_create_user

# Skip slow integration tests (if marked)
pytest -m "not integration"
```

Coverage reports are generated automatically:
- **Terminal:** summary printed to stdout
- **HTML:** `backend/htmlcov/index.html`
- **XML:** `backend/coverage.xml` (used by CI)

### Frontend Tests (Jest)

The frontend uses **Jest** with **React Testing Library**. Tests live in `frontend/tests/`.

```bash
cd frontend

# Run all tests
npm test

# Run tests in CI mode (no watch, with coverage)
npm test -- --ci --watchAll=false --coverage

# Run a specific test file
npm test -- recorder.integration.test.tsx

# Watch mode (re-runs on file changes)
npm test -- --watch
```

### Linting

```bash
# Backend — flake8 + black + isort
cd backend
flake8 .
black --check .
isort --check-only .

# Frontend — ESLint
cd frontend
npm run lint
```

### CI/CD Pipeline

All tests run automatically on every **push** and **pull request** to `dev` and `main` via GitHub Actions (`.github/workflows/ci.yml`). The pipeline has three jobs:

| Job | What it does |
|-----|-------------|
| `test` | Runs backend pytest against a PostgreSQL + Redis service container |
| `frontend-test` | Runs frontend Jest tests |
| `lint` | Runs flake8, black, and isort checks |

---

## Adding New Tests

### Backend Test Conventions

| Convention | Rule |
|-----------|------|
| **Location** | `backend/tests/` directory |
| **File naming** | Prefix with `test_` (e.g., `test_pipeline.py`) |
| **Function naming** | Prefix with `test_` (e.g., `test_run_pipeline_returns_201`) |
| **Class naming** | Prefix with `Test` (e.g., `TestPipelineView`) |
| **Framework** | pytest + pytest-django |
| **Database access** | Decorate with `@pytest.mark.django_db` |
| **Fixtures** | Add shared fixtures to `tests/conftest.py` |

**Example — adding a new backend test:**

```python
# backend/tests/test_evaluator.py

import pytest
from services.runner.evaluator_service import _determine_success, _count_passed_steps


def test_determine_success_pass():
    assert _determine_success("RESULT: PASS\nStep 1: Passed") is True


def test_determine_success_fail():
    assert _determine_success("RESULT: FAIL\nStep 1: Failed") is False


@pytest.mark.django_db
def test_evaluate_with_database(user_factory):
    """Tests that require database access must use this decorator."""
    # ...
```

### Frontend Test Conventions

| Convention | Rule |
|-----------|------|
| **Location** | `frontend/tests/` or co-located next to source files |
| **File naming** | Suffix with `.test.tsx` or `.test.ts` (e.g., `recorder.integration.test.tsx`) |
| **Framework** | Jest + React Testing Library |
| **Environment** | jsdom (configured in `jest.config.js`) |

**Example — adding a new frontend test:**

```tsx
// frontend/tests/login.test.tsx

import { render, screen } from "@testing-library/react";
import LoginPage from "../app/login/page";

test("renders login form", () => {
  render(<LoginPage />);
  expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
});
```

---

## Building a Release

### Pre-Release Checklist

1. **Update version numbers:**
   - `frontend/package.json` → `"version"` field
   - Consider adding a `__version__` to `backend/replayqa/__init__.py`

2. **Run the full test suite locally:**
   ```bash
   # Backend
   cd backend && source venv/bin/activate && pytest

   # Frontend
   cd frontend && npm test -- --ci --watchAll=false
   ```

3. **Run linters:**
   ```bash
   cd backend && flake8 . && black --check . && isort --check-only .
   cd frontend && npm run lint
   ```

4. **Apply and commit any pending migrations:**
   ```bash
   cd backend
   python manage.py makemigrations
   python manage.py migrate
   # Commit the new migration files
   ```

5. **Build the frontend production bundle:**
   ```bash
   cd frontend && npm run build
   ```
   Verify no build errors. The production bundle is created in `frontend/.next/`.

### Creating the Release

```bash
# Merge to main
git checkout main
git merge dev

# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0: description of release"
git push origin main --tags
```

### Post-Release Sanity Checks

- [ ] CI pipeline passes on the `main` branch
- [ ] `git tag -l` shows the new tag
- [ ] Fresh clone + setup works: `git clone ... && cd ReplayQA`
- [ ] Run a test recording and execution end-to-end
- [ ] Check that database migrations apply cleanly on a fresh database
- [ ] Verify environment variable documentation is up to date

### Automated Steps (via CI)

The following are handled automatically by GitHub Actions on every push to `main`:
- Backend tests (pytest with PostgreSQL + Redis)
- Frontend tests (Jest)
- Linting (flake8, black, isort)

### Manual Steps (not automated)

- Version number updates in `package.json`
- Database migration generation (`makemigrations`)
- Git tagging and release notes

---

## Git Workflow & Pull Requests

### Branch Strategy

- `main` — stable release branch
- `dev` — integration branch for active development
- Feature branches — created from `dev`, named descriptively (e.g., `Owen-LiveView`, `feature/scheduled-tests`)

### Commit Messages

Use conventional commit prefixes:

```
feat: Add live browser view during test execution
fix: Correct step count discrepancy in evaluator
docs: Update developer guidelines
refactor: Extract session service from recorder
test: Add unit tests for evaluator service
```

### Pull Request Checklist

Before submitting a PR, verify:

- [ ] All tests pass locally (`pytest` and `npm test`)
- [ ] Linting passes (`flake8`, `black`, `npm run lint`)
- [ ] New database migrations are committed (if models changed)
- [ ] No secrets, API keys, or `.env` files are committed
- [ ] Documentation is updated if behavior changed
- [ ] PR description explains *what* and *why*

---

## Code Style

### Python (Backend)

- **Formatter:** [Black](https://black.readthedocs.io/) (line length: 127)
- **Import sorting:** [isort](https://pycqa.github.io/isort/)
- **Linting:** [flake8](https://flake8.pycqa.org/) (config in `.flake8`)
- **Style:** PEP 8, type hints, docstrings on public functions

### TypeScript (Frontend)

- **Linting:** ESLint with `eslint-config-next`
- **Style:** 2-space indentation, strict TypeScript, prefer `const`/`let` over `var`

---

## Troubleshooting

### Database connection error
```
Error: could not connect to server: Connection refused
```
**Solution:**
- Check PostgreSQL is running: `pg_ctl status` or `brew services list`
- Verify `DATABASE_URL` in `.env` (host, port, credentials)
- If using Supabase, check your connection string in Supabase dashboard → Settings → Database

### Redis connection error
```
Error: Error 61 connecting to localhost:6379. Connection refused.
```
**Solution:**
- Start Redis: `redis-server` or `brew services start redis`
- Verify it's running: `redis-cli ping` (should return `PONG`)

### Celery tasks not executing
**Solution:**
- Confirm the Celery worker is running: `celery -A replayqa worker --loglevel=info`
- Verify `CELERY_BROKER_URL` in `.env` points to a running Redis instance
- Check Celery worker terminal for error messages
- Ensure `services.runner` is included in `autodiscover_tasks()` in `replayqa/celery.py`

### Browserbase 402 Payment Required
```
Free plan browser minutes limit reached.
```
**Solution:**
- The Browserbase free tier has a monthly limit on browser minutes. Upgrade your plan at https://browserbase.com/plans or wait for the limit to reset.
