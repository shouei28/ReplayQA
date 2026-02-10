"""
Django management command to create a test periodic task
Usage: python manage.py create_test_periodic_task
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Creates a test periodic task that runs every 30 seconds'

    def handle(self, *args, **options):
        # Create interval schedule (every 30 seconds)
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.SECONDS,
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created interval schedule: every 30 seconds')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Interval schedule already exists')
            )

        # Create or update the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Test Periodic Task',
            defaults={
                'task': 'core.tasks.test_task',
                'interval': schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created periodic task: {task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Periodic task already exists: {task.name}'
                )
            )
            # Update it to use the schedule
            task.interval = schedule
            task.enabled = True
            task.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated periodic task: {task.name}')
            )
