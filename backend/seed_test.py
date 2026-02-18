"""Seed script — run with: python manage.py shell < seed_test.py"""

import json

from core.models import Test, User

# Get or create a demo user
user, created = User.objects.get_or_create(
    username="demo",
    defaults={"email": "demo@replayqa.com"},
)
if created:
    user.set_password("demo1234")
    user.save()
    print(f"Created user: {user.username}")
else:
    print(f"Using existing user: {user.username}")

steps = [
    {
        "kind": "act",
        "method": "click",
        "selector": '//*[@id="i23"]/div[4]/div/div/div[1]/div/div/input',
        "instruction": "Click the Where to? ",
    },
    {
        "kind": "act",
        "method": "fill",
        "selector": '//*[@id="i23"]/div[6]/div[2]/div[2]/div[1]/div/input',
        "arguments": ["Tokyo"],
        "instruction": 'Type "Tokyo" into the Where to? ',
    },
    {
        "kind": "act",
        "method": "click",
        "selector": '//*[@id="c193"]/div[2]/div[1]/div[1]',
        "instruction": "Click the Narita International Airport",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": '//*[@id="i23"]/div[1]/div/div/div[1]/div/div/input',
        "instruction": "Click the Where from?",
    },
    {
        "kind": "act",
        "method": "fill",
        "selector": '//*[@id="i23"]/div[6]/div[2]/div[2]/div[1]/div/input',
        "arguments": ["Jakarta"],
        "instruction": 'Type "Jakarta" into the Where else?',
    },
    {
        "kind": "act",
        "method": "click",
        "selector": '//*[@id="c382"]/div[2]/div[1]/div[1]',
        "instruction": "Click the Soekarno\u2013Hatta International Airport",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//button[@aria-label='1 passenger']",
        "instruction": "Click the 1 passenger",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//button[@aria-label='Add child aged 2 to 11']",
        "instruction": "Click the Add child aged 2 to 11",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//input[@aria-label='Departure']",
        "instruction": "Click the Departure",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//button[@aria-label='Next']",
        "instruction": "Click the Next",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//div[@aria-label='Wednesday, April 15, 2026']",
        "instruction": "Click April 15",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//div[@aria-label='Wednesday, April 29, 2026']",
        "instruction": "Click April 29",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//button[.//span[text()='Done']]",
        "instruction": "Click Done",
    },
    {
        "kind": "act",
        "method": "click",
        "selector": "//button[@aria-label='Search']",
        "instruction": "Click Search",
    },
]

test, created = Test.objects.get_or_create(
    user=user,
    test_name="Google Flights \u2014 Jakarta to Tokyo",
    defaults={
        "description": "Search for round trip flights from Jakarta to Tokyo (April 15-29) with 1 adult + 1 child",
        "url": "https://www.google.com/travel/flights",
        "steps": steps,
        "expected_behavior": "Flight search results should appear showing available flights from Jakarta (CGK) to Tokyo (NRT) for the selected dates with 1 adult and 1 child passenger.",
    },
)

if created:
    print(f"Created test: {test.test_name} (id={test.id})")
else:
    print(f"Test already exists: {test.test_name} (id={test.id})")
