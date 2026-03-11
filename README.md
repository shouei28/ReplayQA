# ReplayQA — User Guide

## Table of Contents

1. [What is ReplayQA?](#what-is-replayqa)
2. [Features](#features)
3. [Tag](#running-the-software)
4. [GenAI use](#using-genai)

---

## What is ReplayQA?

ReplayQA is a web-based QA testing platform that lets you record user interactions with any website and automatically replay them as test cases.

## Features

### Authentication
- Users can create accounts and sign in.

### Browser Recorder
- Enter a URL, pick a device type and browser, and just use the site normally. ReplayQA records every click, keystroke, and navigation as test steps.
- Recorded actions get summarized into readable step descriptions.
- You can edit the step descriptions before saving the test.

### Test Execution
- Saved tests are replayed using a Gemini Computer-Use Agent running in a real cloud browser through Browserbase. It adapts to minor UI changes instead of relying on brittle selectors.
- You can watch the test run live via an embedded browser stream.
- Tests run asynchronously in the background with Celery, so you can queue one and check back later.

### Evaluation & Results
- After each step, screenshots are captured and evaluated to determine pass/fail.
- The results page shows the overall status, a per-step breakdown (e.g., 8/10 passed), runtime, and the full execution log.
- You can browse step screenshots or replay the full browser session recording.

### Test Management
- Create, edit, and delete saved tests from the Tests page.
- Run a single test or select multiple to run in batch.
- View execution history with status, timestamps, and links to results.

### Scheduled Tests
- Schedule tests to run on a daily, weekly, or custom recurring basis using Celery Beat.
- View upcoming runs in a calendar.

### Dashboard Overview
- The overview page shows recent test activity, pass/fail counts, and shortcuts to start recording or run a test.

## Tag
todo

## Using GenAI
While we leveraged Claude AI and Cursor to assist with creating test cases and writing mundane code, all of the high-level architectural designs/pipelines were planned and conceived entirely by the team. To ensure high code quality, we used GitHub Copilot as an assistant during our code review to provide more constructive technical feedback.
