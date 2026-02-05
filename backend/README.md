# ReplayQA Backend

Django REST API backend for ReplayQA test automation platform.

## Setup Instructions

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
cd 
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

Edit `.env` with your:
- Database credentials (PostgreSQL)
- Redis connection URL
- External service API keys (Browserbase, Stagehand, Gemini)
- Supabase configuration

### 4. Database Setup

Make sure PostgreSQL is running and create the database:

```bash
createdb replayqa  # Or use your preferred method
```

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## Project Structure

```
backend/
├── api/                      # API views and URL routing (Presentation/API Layer)
│   ├── views/               # Organized view files by domain
│   │   ├── pipeline.py      # Pipeline execution endpoints
│   │   ├── test_history.py  # Test history endpoints
│   │   ├── saved_tests.py   # Saved tests endpoints
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── admin.py         # Admin management endpoints
│   │   └── misc.py          # Utility endpoints (health, screenshots)
│   ├── urls.py              # URL routing configuration
│   └── apps.py
├── core/                     # Core models and business logic
│   ├── models.py            # Database models (User, Test, TestExecution, TestResult)
│   ├── serializers.py       # DRF serializers
│   └── admin.py             # Django admin configuration
├── services/                 # Core Services Layer (to be implemented)
│   └── __init__.py          # Future: RecordingService, RunnerService, etc.
├── replayqa/                # Django project settings
│   ├── settings.py          # Main configuration
│   ├── urls.py              # Root URL configuration
│   └── celery.py            # Celery configuration
├── manage.py                # Django management script
└── requirements.txt          # Python dependencies
```

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

## Next Steps

1. Implement authentication (JWT tokens)
2. Implement business logic in each endpoint
3. Set up Celery workers for background tasks
4. Integrate with Browserbase, Stagehand, and Gemini APIs
5. Implement blob storage integration with Supabase
