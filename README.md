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
npm start

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
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page-level components
│   │   ├── services/           # API client services
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
├── docs/                       # Documentation
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

# External Services
BROWSERBASE_API_KEY=bb_your_key_here
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

### 2. Frontend Setup (React + TypeScript)

**Install dependencies:**
```bash
cd frontend
npm install
```

**Configure environment variables:**
Create `.env` file in `frontend/`:
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENV=development
```

**Run development server:**
```bash
npm start
```

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
│   Client    │ (React)
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

### Other
- `GET /api/auth/me` - Get current user profile
- `POST /api/auth/logout` - Logout
- `GET/POST /api/admin` - Admin user management
- `GET /api/screenshot/<test_result_id>/<step>` - Serve screenshots
- `GET /api/live-view/<test_execution_id>/` - Get live view URL
- `GET /api/health` - Health check

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

**Run tests:**
```bash
# Run all tests
pytest

# Run specific test file
pytest backend/tests/test_runner_service.py

# Run with coverage
pytest --cov=core --cov-report=html

# Run only fast tests (exclude integration)
pytest -m "not integration"
```

**Run tests:**
```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test MyComponent.test.tsx
```

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
```
# Operational use cases as of now:
 - Automate creating and running tests to verify student user workflows are working correctly after any site or app changes.
 - Simplify testing for developers with less experience in testing
 - Finding logical errors that weren’t caught during our testing.

```
```
# ReplayQA Beta Release

**Release Identifier (Git Tag):** `beta-release`

To checkout the code for this specific beta release, run the following command in your terminal:
```bash
git checkout beta-release
```
```
```
# ReplayQA
Making QA easier than ever

# Project Overview
ReplayQA aims to make software testing simple and efficient by automatically generating human-readable test cases from recorded user interactions with a web application. Developers can upload a link to the web application they want to test, and record by clicking the start button initiating a session. This session can overlook interactions with the UI elements such as clicking on buttons, scrolling, and submitting forms, and the system will automatically convert these interactions into executable test cases with clear summaries and results.

The goal is to reduce the time and effort required write and maintain testcases.

# Repository Structure
  - frontend/ - Web interface for recording UI interactions
  - backend/ - Server-side interpretting the recordings and generating testcases
  - tests/ - Example test cases
  - docs/ - Project documentation and design notes
  - README.md - Project overview and repository guide

# Living Document
The link for the project's living document:
https://docs.google.com/document/d/15oPi7MEKw8f-VNyCnYaS6Zs2bgq6pqCIovzq1Y4_FOE/edit?usp=sharing
```
