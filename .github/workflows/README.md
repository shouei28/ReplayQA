# GitHub Actions CI/CD Pipeline

This directory contains GitHub Actions workflows for continuous integration and deployment.

## Workflows

### `ci.yml`

Runs on:
- Push to `dev` or `main` branches
- Pull requests targeting `dev` or `main` branches

**Jobs:**

1. **test** - Runs the test suite
   - Sets up PostgreSQL and Redis services
   - Installs dependencies
   - Runs database migrations
   - Executes pytest with coverage
   - Uploads coverage reports

2. **lint** - Checks code quality
   - Runs flake8 for linting
   - Checks code formatting with black
   - Verifies import sorting with isort

## Running Tests Locally

```bash
cd backend
pytest
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## Code Quality Checks

```bash
# Linting
flake8 .

# Formatting check
black --check .

# Import sorting check
isort --check-only .
```

## Adding New Tests

Create test files in the `backend/tests/` directory following the naming convention:
- `test_*.py` or `*_test.py`

Example:
```python
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_example():
    # Your test code here
    pass
```
