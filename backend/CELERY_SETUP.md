# Celery Setup Guide

## Prerequisites

1. **Install Redis** (if not already installed):
   ```bash
   # macOS
   brew install redis
   brew services start redis
   
   # Linux
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

2. **Verify Redis is running**:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

## Running Celery

### Option 1: Separate Processes (Recommended for Production)

**Terminal 1 - Celery Worker:**
```bash
celery -A replayqa worker --loglevel=info
```

**Terminal 2 - Celery Beat:**
```bash
celery -A replayqa beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Option 2: Combined (Development Only)

```bash
celery -A replayqa worker --beat --scheduler django --loglevel=info
```

## Creating Periodic Tasks

### Method 1: Using Management Command

```bash
python manage.py create_test_periodic_task
```

This creates a test task that runs every 30 seconds.

### Method 2: Using Django Admin

1. Start Django server: `python manage.py runserver`
2. Go to http://localhost:8000/admin/
3. Navigate to "Periodic Tasks" → "Periodic tasks"
4. Click "Add Periodic Task"
5. Fill in:
   - Name: Your task name
   - Task: `core.tasks.test_task` (or your custom task)
   - Interval: Create/select an interval schedule
   - Enabled: ✓

### Method 3: Programmatically (Python)

```python
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Create interval (every 10 seconds)
schedule, created = IntervalSchedule.objects.get_or_create(
    every=10,
    period=IntervalSchedule.SECONDS,
)

# Create periodic task
PeriodicTask.objects.create(
    interval=schedule,
    name='My Test Task',
    task='core.tasks.test_task',
    enabled=True,
)
```

## Available Mock Tasks

- `core.tasks.test_task` - Simple test task that prints a message
- `core.tasks.mock_pipeline_task` - Mock pipeline task for test execution

## Testing

1. Start Redis
2. Start Celery worker and beat
3. Create a periodic task using one of the methods above
4. Watch the Celery worker terminal for task execution logs

You should see output like:
```
Test: Celery task executed successfully!
```

## Troubleshooting

- **Redis connection error**: Make sure Redis is running (`redis-cli ping`)
- **Tasks not running**: Check that Celery Beat is running
- **Import errors**: Make sure you've run `python manage.py migrate` to create django_celery_beat tables
