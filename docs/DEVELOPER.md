# ReplayQA Developer Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Environment Setup](#development-environment-setup)
4. [Architecture Overview](#architecture-overview)
5. [API Endpoints](#api-endpoints)
6. [Testing](#testing)
7. [Code Style Guidelines](#code-style-guidelines)
8. [Contributing](#contributing)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- **Python 3.9+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **PostgreSQL 14+** - Database (or use Supabase)
- **Redis 6+** - Task queue backend
- **Git** - Version control

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Jovewinston/ReplayQA.git
cd ReplayQA

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Frontend setup
cd ../frontend
npm install

# Start development servers
# Terminal 1 - Backend
cd backend
python manage.py runserver

# Terminal 2 - Frontend
cd frontend
npm run dev

# Terminal 3 - Celery worker
cd backend
celery -A replayqa worker -l info

# Terminal 4 - Celery beat (for scheduled tasks)
cd backend
celery -A replayqa beat -l info
```

---

## Project Structure

```
replayqa/
├── backend/
│   ├── api/                      # API views and URL routing (Presentation/API Layer)
│   │   ├── views/               # Organized view files by domain
│   │   │   ├── pipeline.py      # Pipeline execution endpoints
│   │   │   ├── test_history.py  # Test history endpoints
│   │   │   ├── saved_tests.py   # Saved tests endpoints
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── admin.py         # Admin management endpoints
│   │   │   └── misc.py          # Utility endpoints (health, screenshots)
│   │   ├── urls.py              # URL routing configuration
│   │   └── apps.py
│   ├── core/                     # Core models and business logic
│   │   ├── models.py            # Database models (User, Test, TestExecution,TestResult)
│   │   ├── serializers.py       # DRF serializers
│   │   └── admin.py             # Django admin configuration
│   ├── services/                 # Core Services Layer (to be implemented)
│   │   └── __init__.py          # Future: RecordingService, RunnerService, etc.
│   ├── replayqa/                # Django project settings
│   │   ├── settings.py          # Main configuration
│   │   ├── urls.py              # Root URL configuration
│   │   └── celery.py            # Celery configuration
│   ├── manage.py                # Django management script
│   └── requirements.txt         # Python dependencies
├── frontend/                    # Next.js App Router (React + TypeScript)
│   ├── app/                     # App Router pages and layouts
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home page
│   │   ├── globals.css
│   │   ├── admin/page.tsx
│   │   ├── demo/page.tsx
│   │   ├── login/page.tsx
│   │   ├── recorder/page.tsx    # Standalone recorder
│   │   ├── waitlist/page.tsx
│   │   └── dashboard/           # Dashboard section
│   │       ├── layout.tsx
│   │       ├── overview/page.tsx
│   │       ├── activity/page.tsx
│   │       ├── scheduled/page.tsx
│   │       ├── settings/page.tsx
│   │       └── projects/[name]/ # Project detail (dynamic route)
│   │           ├── page.tsx
│   │           └── recorder/page.tsx
│   ├── components/             # React components
│   │   ├── ui/                  # Shadcn/UI primitives (optional)
│   │   ├── dashboard/
│   │   └── recorder.tsx
│   ├── hooks/                   # Custom React hooks
│   ├── lib/                     # Shared utilities
│   │   ├── api.ts               # API client (recorder, auth, etc.)
│   │   ├── types.ts
│   │   └── utils.ts
│   ├── public/assets/
│   ├── package.json
│   ├── next.config.mjs
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── components.json          # Shadcn config (optional)
├── docs/                        # Documentation
│   └── DEVELOPER.md
├── docker-compose.yml
└── README.md
```

---

## Development Environment Setup

### 1. Backend Setup (Django)

**Install dependencies:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configure environment variables:**
Create `.env` file in `backend/`:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/replayqa_dev
# Or use Supabase
# DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Django
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# External Services (recorder needs Browserbase)
BROWSERBASE_API_KEY=bb_your_key_here
BROWSERBASE_PROJECT_ID=your_project_id
STAGEHAND_API_KEY=sh_your_key_here
GEMINI_API_KEY=your_gemini_key_here

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
SUPABASE_BUCKET_NAME=replayqa-screenshots

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**Run migrations:**
```bash
python manage.py migrate
```

**Create superuser:**
```bash
python manage.py createsuperuser
```

**Run development server:**
```bash
python manage.py runserver
```

### 2. Frontend Setup (Next.js + TypeScript)

**Install dependencies:**
```bash
cd frontend
npm install
```

**Configure environment variables:**
Create `.env` file in `frontend/`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Run development server:**
```bash
npm run dev
```
Then open http://localhost:3000.

### 3. Redis Setup

**Using Docker:**
```bash
docker run -d -p 6379:6379 redis:alpine
```

**Or install locally:**
- macOS: `brew install redis && brew services start redis`
- Ubuntu: `sudo apt install redis-server && sudo systemctl start redis`
- Windows: Use Docker or WSL

### 4. Celery Setup

**Start Celery worker:**
```bash
cd backend
celery -A replayqa worker -l info
```

**Start Celery beat (for scheduled tasks):**
```bash
celery -A replayqa beat -l info
```

### 5. Database Setup (PostgreSQL)


**Supabase**:
1. Create project at https://supabase.com
2. Get connection string from Settings > Database
3. Update `DATABASE_URL` in `.env`

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
│  └───────────┬──────────────┘  │
│              ▼                  │
│  ┌──────────────────────────┐  │
│  │  Orchestration Layer     │  │
│  └───────────┬──────────────┘  │
│              ▼                  │
│  ┌──────────────────────────┐  │
│  │   Core Services Layer    │  │
│  │  • RecordingService      │  │
│  │  • RunnerService         │  │
│  │  • EvaluatorService      │  │
│  │  • SessionService        │  │
│  │  • SchedulerService      │  │
│  └───────────┬──────────────┘  │
│              ▼                  │
│  ┌──────────────────────────┐  │
│  │   Data Access Layer      │  │
│  └───────────┬──────────────┘  │
└──────────────┼──────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌──────────────┐  ┌────────────┐
│  PostgreSQL  │  │   Redis    │
│   (Supabase) │  │  (Queue)   │
└──────────────┘  └────────────┘
       │
       ▼
┌──────────────┐
│ Blob Storage │
│ (Screenshots)│
└──────────────┘

External Services:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Browserbase  │  │  Stagehand   │  │   Gemini     │
│  (Browser)   │  │  (Actions)   │  │     (AI)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Request Flow

**Recording a Test:**
```
1. User enters URL → POST /recording/start
2. SessionService creates Browserbase session
3. RecordingService injects DOM listeners
4. User interacts with page
5. Stagehand captures and interprets actions
6. Steps saved to database → POST /saved-tests
7. Return test_id to client
```

**Running a Test:**
```
1. User clicks "Run" → POST /run-pipeline
2. Request queued in Redis (Celery)
3. Background worker picks up task
4. RunnerService loads test and creates browser session
5. Execute each step via Stagehand
6. Capture screenshots (→ Blob Storage)
7. EvaluatorService analyzes results (Gemini AI)
8. Save TestResult to database
9. Client polls GET /status/{id} for updates
10. Client fetches final results GET /results/{id}
```

---

## API Endpoints

All endpoints are currently placeholder implementations. See `api/views/` directory for detailed comments on what each endpoint should do. Views are organized by domain:
- `pipeline.py` - Test execution pipeline endpoints
- `test_history.py` - Test history management
- `saved_tests.py` - Saved test definitions
- `auth.py` - Authentication and user profile
- `admin.py` - Admin user management
- `misc.py` - Utility endpoints (health check, screenshots)

### Pipeline Execution
- `POST /api/run-pipeline` - Start a new test execution
- `GET /api/status/<test_execution_id>` - Poll job status
- `GET /api/results/<test_execution_id>` - Get full test results

### Test History
- `GET /api/tests` - List all executed tests
- `DELETE /api/<test_result_id>` - Delete a test execution

### Saved Tests
- `POST /api/saved-tests` - Save new test definition
- `GET /api/saved-tests` - Get all saved tests
- `GET /api/saved-tests/<test_id>` - Get one saved test
- `PUT /api/saved-tests/<test_id>` - Update saved test
- `DELETE /api/saved-tests/<test_id>` - Delete saved test

### Recorder (Browserbase session + recording)
- `POST /api/v1/recorder/start` - Start a recorder session (returns `session_id`, `connect_url`, `live_view_url`)
- `GET /api/v1/recorder/<session_id>/live-view?browserbase_session_id=...` - Get live view URL
- `POST /api/v1/recorder/<session_id>/start-recording` - Start recording (body: `browserbase_session_id`, optional `connect_url`, `url`)
- `GET /api/v1/recorder/<session_id>/recorded-actions` - Get and clear recorded actions queue
- `POST /api/v1/recorder/<session_id>/toggle-recording` - Toggle recording on/off (body: `enabled`)
- `POST /api/v1/recorder/<session_id>/end` - End session (body: `browserbase_session_id`)

### Other
- `GET /api/auth/me` - Get current user profile
- `POST /api/auth/logout` - Logout
- `GET/POST /api/admin` - Admin user management
- `GET /api/screenshot/<test_result_id>/<step>` - Serve screenshots
- `GET /api/live-view/<test_execution_id>/` - Get live view URL
- `GET /api/health` - Health check

Note: API may be mounted at `/api/` or `/api/v1/` depending on project URL config. Frontend `lib/api.ts` uses `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000/api/v1`).

## Database Management

### Creating Migrations

```bash
# After modifying models
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# View SQL for migration
python manage.py sqlmigrate core 0001

# Rollback last migration
python manage.py migrate core 0001
```

**Run with:**
```bash
python manage.py seed_data
```

---

## Testing

## Running Tests Locally

### Backend Tests (Pytest)

```bash
cd backend

# Install pytest
pip install pytest pytest-django pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=api

# Run specific file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_create_user
```

### Frontend Tests (Jest)

```bash
cd frontend

# Run all tests
npm test

# Lint
npm run lint

# Run specific file
npm test FileName.test.tsx

# Watch mode (re-run on file changes)
npm test -- --watch
```

## CI/CD with GitHub Actions

**On every push and pull request:**
- Backend tests (pytest)
- Frontend linting (eslint)
- Frontend tests (jest)
- Code coverage (80%)

### Setup Instructions

1. Ensure `.github/workflows/tests.yml` is setup in your repository
2. Push changes to GitHub
3. Tests run automatically on every push

View results in GitHub Actions tab.

## Adding New Tests

### Backend Test

1. Create file in `backend/tests/` with `test_` prefix
2. Write test function with `test_` prefix
3. Use `@pytest.mark.django_db` for database tests
4. Run with `pytest`

Example:
```python
import pytest
from core.models import User

@pytest.mark.django_db
def test_my_feature():
    user = User.objects.create_user(
        username='test',
        email='test@example.com',
        password='pass'
    )
    assert user.username == 'test'
```

### Frontend Test

1. Create file in `frontend/src/` ending with `.test.tsx`
2. Import render and screen from testing-library
3. Write test with `test()` function
4. Run with `npm test`

Example:
```typescript
import { render, screen } from '@testing-library/react';
import MyComponent from './MyComponent';

test('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```
Add Jest or Vitest and `npm test` when tests are added.

## Code Style Guidelines

### Python (PEP 8)

**Key rules:**
- 4 spaces for indentation
- Max line length: 79 characters
- Use descriptive variable names
- Add docstrings to all functions
- Use type hints
- Follow import order: stdlib, third-party, local

**Enforce with:**
```bash
# Install tools
pip install black pylint flake8

# Format code
black backend/

# Check style
pylint backend/core/

# Check PEP 8 compliance
flake8 backend/
```

**Key rules:**
- Use TypeScript strict mode
- Define interfaces for all data structures
- Use const/let, never var
- Prefer arrow functions
- Use template literals over concatenation
- 2 spaces for indentation

**Enforce with:**
```bash
# Install tools
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin prettier

# Check code
npm run lint

# Format code
npm run format
```

---

## Contributing

### Git Workflow

**1. Create feature branch:**
```bash
git checkout -b feature/my-new-feature
```

**2. Make changes and commit:**
```bash
git add .
git commit -m "feat: Add test recording functionality"
```

**3. Push and create PR:**
```bash
git push origin feature/my-new-feature
```

Then create pull request on GitHub.

### Code Review Checklist

**Reviewer should check:**
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] No console.log or debug code
- [ ] Documentation updated
- [ ] No sensitive data (API keys, passwords)
- [ ] Error handling is appropriate
- [ ] Performance considerations addressed
- [ ] Security best practices followed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested these changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No new warnings
```

---

## Troubleshooting

### Common Issues

**Issue: Database connection error**
```
Error: could not connect to server: Connection refused
```
**Solution:**
- Check PostgreSQL is running: `pg_ctl status`
- Verify DATABASE_URL in .env
- Check firewall settings

**Issue: Redis connection error**
```
Error: Error 61 connecting to localhost:6379. Connection refused.
```
**Solution:**
- Start Redis: `redis-server`
- Check if Redis is running: `redis-cli ping` (should return PONG)

**Issue: Celery tasks not executing**
**Solution:**
- Check Celery worker is running
- Verify CELERY_BROKER_URL in .env
- Check Redis is running
- Look at Celery logs for errors

**Issue: CORS errors in browser**
```
Access to XMLHttpRequest blocked by CORS policy
```
**Solution:**
- Add frontend URL to ALLOWED_ORIGINS in backend .env
- Install django-cors-headers if not already installed
```