# ReplayQA — User Guide

## Table of Contents

1. [What is ReplayQA?](#what-is-replayqa)
2. [Installation](#installation)
3. [Running the Software](#running-the-software)
4. [Using ReplayQA](#using-replayqa)
5. [Reporting Bugs](#reporting-bugs)
6. [Known Bugs & Limitations](#known-bugs--limitations)

---

## What is ReplayQA?

ReplayQA is a web-based QA testing platform that lets you record user interactions with any website and automatically replay them as test cases.

**Why use ReplayQA?**

- **Record once, test forever.** Click through your app in a browser and ReplayQA captures every action (clicks, typing, navigation) as reusable test steps.
- **AI-powered execution.** Tests are replayed by a Gemini-powered Computer-Use Agent that actually interacts with your site in a real browser, adapting to minor UI changes.
- **Live browser view.** Watch the AI agent execute your tests in real time via a live browser stream.
- **Automatic pass/fail evaluation.** An AI evaluator analyzes screenshots and determines whether each step passed, producing a clear results report.
- **No coding required.** Create, run, and manage tests entirely from the dashboard UI.

**Use cases:**
- Verify student or user workflows still work after site changes
- Simplify testing for developers with less QA experience
- Catch logical errors missed during manual testing

---

## Installation

### Prerequisites

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| Python | 3.9+ | Backend server | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | Frontend server | [nodejs.org](https://nodejs.org/) |
| PostgreSQL | 14+ | Database | [postgresql.org](https://www.postgresql.org/download/) or use [Supabase](https://supabase.com) |
| Redis | 6+ | Task queue | macOS: `brew install redis` · Ubuntu: `sudo apt install redis-server` |
| Git | any | Source control | [git-scm.com](https://git-scm.com/) |

### Step-by-Step Setup

**1. Clone the repository:**

```bash
git clone https://github.com/Jovewinston/ReplayQA.git
cd ReplayQA
```

**2. Set up the backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

**3. Configure backend environment variables:**

Create a file called `.env` in the `backend/` directory with the following:

```
DATABASE_URL=postgresql://user:password@localhost:5432/replayqa
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id
GEMINI_API_KEY=your_gemini_api_key

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000
```

You will need accounts on:
- [Browserbase](https://www.browserbase.com/) — for cloud browser sessions (free tier available)
- [Google AI Studio](https://aistudio.google.com/) — for a Gemini API key

**4. Initialize the database:**

```bash
python manage.py migrate
python manage.py createsuperuser    # Create an admin account
```

**5. Set up the frontend:**

```bash
cd ../frontend
npm install
```

Create a `.env` file in `frontend/`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## Running the Software

### Manual Start

If you prefer to start services individually, open **four terminal windows**:

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Backend API server
cd backend && source venv/bin/activate
python manage.py runserver

# Terminal 3 — Celery worker (required for running tests)
cd backend && source venv/bin/activate
celery -A replayqa worker --loglevel=info

# Terminal 4 — Frontend
cd frontend && npm run dev
```

### Accessing the Application

| Service | URL |
|---------|-----|
| Frontend (main UI) | http://localhost:3000 |
| Backend API | http://localhost:8000 |

**Browser requirements:** Any modern browser (Chrome, Firefox, Safari, Edge). Chrome is recommended for best compatibility.

---

## Using ReplayQA

### Logging In

1. Navigate to **http://localhost:3000/login**
2. Enter your credentials (created during `createsuperuser` or via admin)
3. You will be redirected to the **Dashboard**

### Dashboard Overview

The dashboard sidebar provides access to all features:

| Section | Description |
|---------|-------------|
| **Overview** | Summary of recent test activity |
| **Tests** | View all executed tests and their results |
| **Recorder** | Record new test cases |
| **Scheduled** | *Work in progress* — Schedule tests to run automatically |

### Recording a Test

1. Click **Recorder** in the sidebar (or go to http://localhost:3000/dashboard/recorder)
2. Enter the **URL** of the website you want to test
3. Select the **device** (desktop/mobile) and **browser** (chrome)
4. Click **Start Session** — a live browser window appears in the page
5. **Interact with the website** — click buttons, type in fields, navigate pages. ReplayQA captures every action as a test step.
6. Review the captured steps in the panel. You can edit step descriptions.
7. Click **Save Test** — give your test a name, description, and expected behavior
8. The test appears in the **Tests** section, ready to be run

### Running a Test

1. Go to **Tests** in the sidebar
2. Find the saved test you want to run
3. Click the **Run** button
4. You are redirected to the **Results** page, which shows:
   - A **progress bar** tracking execution status
   - A **live browser view** (iframe) showing the AI agent interacting with the site in real time
5. When the test completes, the results page shows:
   - **Pass/Fail** result
   - **Steps Passed** count (e.g., 8/10)
   - **Agent Execution Log** — every action the AI agent took
   - **AI Analysis** — the evaluator's explanation of what happened
   - **Screenshots** — captured after each agent turn

### Viewing Test Results

1. Go to **Tests** in the sidebar
2. Click on any completed test to view its results
3. Each result includes:
   - Overall pass/fail status
   - Per-step pass/fail breakdown
   - Total runtime and token usage
   - Screenshots from each execution step
4. Click the **Screenshot** link next to any step to view the captured screenshot
5. To delete a test result, click the **delete** icon


## Reporting Bugs

Report bugs and request features using the project’s **issue tracker**:

- **GitHub Issues:** [https://github.com/Jovewinston/ReplayQA/issues](https://github.com/Jovewinston/ReplayQA/issues)

When opening a bug report, please include:

- **What you did** — Steps to reproduce (e.g., “Went to Recorder → entered URL → clicked Start Session”).
- **What you expected** — Expected behavior.
- **What actually happened** — Actual behavior or error message.
- **Environment** — OS, browser (and version), and whether you’re using the default setup (local Redis, PostgreSQL, etc.).
- **Screenshots or logs** — If relevant (e.g., console errors, backend logs).

For more on writing useful bug reports, see [How to write a good bug report](https://www.chiark.greenend.org.uk/~sgtatham/bugs.html).

---

## Known Bugs & Limitations

Known issues and limitations are tracked in the issue tracker. Before testing, check:

- **Known issues:** [https://github.com/Jovewinston/ReplayQA/issues](https://github.com/Jovewinston/ReplayQA/issues) (filter or label for “bug” or “known issue” if your project uses them).

**Current limitations:**

- **Scheduled tests** — Scheduling UI and backend exist; recurring execution depends on Celery Beat being running. See *Running the Software* in this guide.
- **Recording playback** — Session replay (“View Recording”) is only available for executions that used a Browserbase session; older or failed sessions may not have recording data.
- **Browser support** — Chrome is recommended; other modern browsers are supported but not fully tested.

If you find a bug that isn’t listed, please report it using the steps in [Reporting Bugs](#reporting-bugs).

