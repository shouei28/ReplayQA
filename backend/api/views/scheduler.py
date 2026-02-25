"""
Scheduler API – create/list/delete scheduled test runs.

Stores schedules as django_celery_beat PeriodicTask rows.
Celery Beat triggers core.tasks.run_scheduled_test(test_id, user_id).
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Test
from core.tasks import SCHEDULED_TASK_NAME, run_scheduled_test

logger = logging.getLogger(__name__)

# Frontend sends times in this timezone; we convert to UTC for celery-beat.
USER_TZ = ZoneInfo("America/Los_Angeles")


def _time_pacific_to_utc(hour: int, minute: int, date=None) -> datetime:
    """Build naive UTC datetime from hour/minute (in Pacific) and optional date."""
    if date:
        dt = datetime(date.year, date.month, date.day, hour, minute, 0, tzinfo=USER_TZ)
    else:
        # Use today in Pacific for “time only” (crontab will repeat)
        now = timezone.now().astimezone(USER_TZ)
        dt = datetime(now.year, now.month, now.day, hour, minute, 0, tzinfo=USER_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def schedule_list(request):
    """
    GET /schedules – list scheduled tests for the current user.
    POST /schedules – create a new schedule (same body as schedule_create).
    """
    if request.method == "POST":
        return schedule_create(request)
    from django_celery_beat.models import PeriodicTask

    user_id = str(request.user.id)
    tasks = (
        PeriodicTask.objects.filter(
            task=SCHEDULED_TASK_NAME,
            enabled=True,
        )
        .exclude(kwargs="")
        .order_by("date_changed")
    )

    out = []
    for pt in tasks:
        try:
            kwargs = json.loads(pt.kwargs) if isinstance(pt.kwargs, str) else pt.kwargs
            if kwargs.get("user_id") != user_id:
                continue
            test_id = kwargs.get("test_id")
            if not test_id:
                continue
        except (json.JSONDecodeError, TypeError):
            continue

        try:
            test = Test.objects.get(id=test_id, user=request.user)
        except Test.DoesNotExist:
            continue

        # Infer schedule type and human-readable info from beat model
        schedule_type = "custom"
        run_at = "09:00"
        run_on_days = []
        run_on_date = ""
        repeat_every = 0
        repeat_unit = "minutes"

        if pt.interval_id:
            schedule_type = "custom"
            inv = pt.interval
            if inv.period == "seconds":
                repeat_every = inv.every
                repeat_unit = "seconds"
            elif inv.period == "minutes":
                repeat_every = inv.every
                repeat_unit = "minutes"
            elif inv.period == "hours":
                repeat_every = inv.every
                repeat_unit = "hours"
            elif inv.period == "days":
                repeat_every = inv.every
                repeat_unit = "days"
        elif pt.crontab_id:
            cr = pt.crontab
            minute = int(cr.minute) if cr.minute != "*" else 0
            hour = int(cr.hour) if cr.hour != "*" else 9
            # Convert back to Pacific for display
            utc_dt = datetime(2000, 1, 1, hour, minute, 0)
            pacific_dt = timezone.make_aware(utc_dt, timezone.utc).astimezone(USER_TZ)
            run_at = f"{pacific_dt.hour:02d}:{pacific_dt.minute:02d}"
            if cr.day_of_week != "*":
                run_on_days = [int(x) for x in str(cr.day_of_week).split(",") if x.strip().isdigit()]
                schedule_type = "weekly" if len(run_on_days) > 0 else "daily"
            else:
                schedule_type = "daily"
        elif pt.clocked_id:
            schedule_type = "once"
            cl = pt.clocked
            # clocked_time is stored in UTC in DB
            run_on_date = cl.clocked_time.strftime("%Y-%m-%d") if cl.clocked_time else ""
            run_at = cl.clocked_time.strftime("%H:%M") if cl.clocked_time else "09:00"

        last_run = None
        if pt.last_run_at:
            last_run = pt.last_run_at.isoformat()

        out.append({
            "id": str(pt.id),
            "test_id": str(test.id),
            "test_name": test.test_name,
            "schedule_type": schedule_type,
            "run_on_days": run_on_days,
            "run_on_date": run_on_date,
            "run_at": run_at,
            "repeat_every": repeat_every,
            "repeat_unit": repeat_unit,
            "name": pt.name or f"Scheduled: {test.test_name}",
            "last_run_at": last_run,
            "enabled": pt.enabled,
        })

    return Response(out)


def schedule_create(request):
    """
    POST /schedules
    Create a scheduled test run. Body: test_id, schedule_type, run_on_days, run_on_date, run_at, starts_on, repeat_every, repeat_unit, name.
    """
    from django_celery_beat.models import (
        ClockedSchedule,
        CrontabSchedule,
        IntervalSchedule,
        PeriodicTask,
    )

    data = request.data
    user = request.user
    test_id = data.get("test_id")
    schedule_type = (data.get("schedule_type") or "weekly").lower()
    name = (data.get("name") or "").strip() or None

    if not test_id:
        return Response(
            {"test_id": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        test = Test.objects.get(id=test_id, user=user)
    except Test.DoesNotExist:
        return Response(
            {"test_id": "Test not found or does not belong to you."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    run_at = data.get("run_at") or "09:00"
    try:
        hour, minute = map(int, run_at.replace(":", " ").split()[:2])
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    kwargs = {"test_id": str(test.id), "user_id": str(user.id)}
    task_name = name or f"Scheduled: {test.test_name} ({test.id})"
    # Ensure unique name for django_celery_beat
    base_name = task_name
    idx = 0
    from django_celery_beat.models import PeriodicTask
    while PeriodicTask.objects.filter(name=task_name).exists():
        idx += 1
        task_name = f"{base_name} #{idx}"

    if schedule_type == "once":
        run_on_date = data.get("run_on_date") or ""
        if not run_on_date:
            return Response(
                {"run_on_date": "Required for one-time schedule."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            year, month, day = map(int, run_on_date.split("-")[:3])
            clocked_time = _time_pacific_to_utc(hour, minute, date=datetime(year, month, day))
            clocked_time_aware = timezone.make_aware(clocked_time, timezone.utc)
        except (ValueError, TypeError):
            return Response(
                {"run_on_date": "Invalid date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=clocked_time_aware)
        PeriodicTask.objects.create(
            name=task_name,
            task=SCHEDULED_TASK_NAME,
            kwargs=json.dumps(kwargs),
            clocked=clocked,
            one_off=True,
            enabled=True,
        )
        return Response({"detail": "Schedule created.", "schedule_type": "once"}, status=status.HTTP_201_CREATED)

    if schedule_type == "daily":
        utc_dt = _time_pacific_to_utc(hour, minute)
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=str(utc_dt.minute),
            hour=str(utc_dt.hour),
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        PeriodicTask.objects.create(
            name=task_name,
            task=SCHEDULED_TASK_NAME,
            kwargs=json.dumps(kwargs),
            crontab=crontab,
            enabled=True,
        )
        return Response({"detail": "Schedule created.", "schedule_type": "daily"}, status=status.HTTP_201_CREATED)

    if schedule_type == "weekly":
        run_on_days = data.get("run_on_days") or []
        if not run_on_days:
            return Response(
                {"run_on_days": "Select at least one day for weekly schedule."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Celery crontab: 0=Sunday, 6=Saturday
        day_of_week = ",".join(str(d) for d in sorted(set(run_on_days)))
        utc_dt = _time_pacific_to_utc(hour, minute)
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=str(utc_dt.minute),
            hour=str(utc_dt.hour),
            day_of_week=day_of_week,
            day_of_month="*",
            month_of_year="*",
        )
        PeriodicTask.objects.create(
            name=task_name,
            task=SCHEDULED_TASK_NAME,
            kwargs=json.dumps(kwargs),
            crontab=crontab,
            enabled=True,
        )
        return Response({"detail": "Schedule created.", "schedule_type": "weekly"}, status=status.HTTP_201_CREATED)

    if schedule_type == "custom":
        repeat_every = int(data.get("repeat_every") or 30)
        repeat_unit = (data.get("repeat_unit") or "minutes").lower()
        if repeat_every < 1:
            repeat_every = 1
        period_map = {"seconds": IntervalSchedule.SECONDS, "minutes": IntervalSchedule.MINUTES, "hours": IntervalSchedule.HOURS, "days": IntervalSchedule.DAYS}
        period = period_map.get(repeat_unit, IntervalSchedule.MINUTES)
        interval, _ = IntervalSchedule.objects.get_or_create(every=repeat_every, period=period)
        PeriodicTask.objects.create(
            name=task_name,
            task=SCHEDULED_TASK_NAME,
            kwargs=json.dumps(kwargs),
            interval=interval,
            enabled=True,
        )
        return Response({"detail": "Schedule created.", "schedule_type": "custom"}, status=status.HTTP_201_CREATED)

    return Response(
        {"schedule_type": "Must be weekly, once, daily, or custom."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def schedule_delete(request, schedule_id):
    """
    DELETE /schedules/<id>
    Delete a scheduled test. Only tasks owned by the current user (via kwargs user_id) can be deleted.
    """
    from django_celery_beat.models import PeriodicTask

    try:
        pt = PeriodicTask.objects.get(id=schedule_id, task=SCHEDULED_TASK_NAME)
    except PeriodicTask.DoesNotExist:
        return Response(
            {"detail": "Schedule not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        kwargs = json.loads(pt.kwargs) if isinstance(pt.kwargs, str) else pt.kwargs
        if kwargs.get("user_id") != str(request.user.id):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
    except (json.JSONDecodeError, TypeError):
        return Response({"detail": "Invalid schedule."}, status=status.HTTP_400_BAD_REQUEST)

    pt.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
