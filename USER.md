# ReplayQA — User Guide

## Table of Contents

1. [What is ReplayQA?](#what-is-replayqa)
2. [Logging In](#logging-in)
3. [Dashboard Overview](#dashboard-overview)
4. [Recording a Test](#recording-a-test)
5. [Running a Test](#running-a-test)
6. [Viewing Test Results](#viewing-test-results)
7. [Reporting Bugs](#reporting-bugs)
8. [Known Limitations](#known-limitations)

---

## What is ReplayQA?

ReplayQA is a web-based QA testing platform that lets you record user interactions with any website and automatically replay them as test cases.

**Why use ReplayQA?**

- **Record once, test forever.** Click through your app in a browser and ReplayQA captures every action (clicks, typing, navigation) as reusable test steps.
- **AI-powered execution.** Tests are replayed by a Gemini-powered agent that interacts with your site in a real browser, adapting to minor UI changes.
- **Live browser view.** Watch the AI agent execute your tests in real time via a live browser stream.
- **Automatic pass/fail evaluation.** An AI evaluator analyzes screenshots and determines whether each step passed, producing a clear results report.
- **No coding required.** Create, run, and manage tests entirely from the dashboard UI.

**Use cases:**
- Verify student or user workflows still work after site changes
- Simplify testing for developers with less QA experience
- Catch logical errors missed during manual testing

---

## Logging In or Creating an Account

1. Navigate to the ReplayQA app URL
2. If you don't have an account, click on the "Create Account" button enter credentials and click "Create Account".
3. Enter your credentials on the login page
4. You will be redirected to the **Dashboard**


## Dashboard Overview

The dashboard sidebar provides access to all features:

| Section | Description |
|---------|-------------|
| **Overview** | Summary of recent test activity |
| **Tests** | View all executed tests and their results |
| **Recorder** | Record new test cases |
| **Scheduled** | *Work in progress* — Schedule tests to run automatically |

---

## Recording a Test

1. Click **Recorder** in the sidebar
2. Enter the **URL** of the website you want to test
3. Click **Start Session** — a live browser window appears in the page
4. **Interact with the website** — click buttons, type in fields, navigate pages. ReplayQA captures every action as a test step.
5. Review the captured steps in the panel. You can edit step descriptions.
6. Click **Save Test** — give your test a name, description, and expected behavior
7. The test appears in the **Tests** section, ready to be run

---

## Running a Test

1. Go to **Tests** in the sidebar
2. Find the saved test you want to run
3. Click the **Run** button
4. You are redirected to the **Results** page, which shows:
   - A **progress bar** tracking execution status
   - A **live browser view** showing the AI agent interacting with the site in real time
5. When the test completes, the results page shows:
   - **Pass/Fail** result
   - **Steps Passed** count (e.g., 8/10)
   - **Agent Execution Log** — every action the AI agent took
   - **AI Analysis** — the evaluator's explanation of what happened
   - **Screenshots** — captured after each agent turn

---

## Viewing Test Results

1. Go to **Tests** in the sidebar
2. Click on any completed test to view its results
3. Each result includes:
   - Overall pass/fail status
   - Per-step pass/fail breakdown
   - Total runtime and token usage
   - Screenshots from each execution step
4. Click the **Screenshot** link next to any step to view the captured screenshot
5. To delete a test result, click the **delete** icon

---

## Reporting Bugs

Report bugs and request features using the project's **issue tracker**:

- **GitHub Issues:** [https://github.com/Jovewinston/ReplayQA/issues](https://github.com/Jovewinston/ReplayQA/issues)

When opening a bug report, please include:

- **What you did** — Steps to reproduce (e.g., "Went to Recorder → entered URL → clicked Start Session").
- **What you expected** — Expected behavior.
- **What actually happened** — Actual behavior or error message.
- **Environment** — OS and browser (and version).
- **Screenshots** — If relevant.

---

## Known Limitations

- **Scheduled tests** — The scheduling UI exists but recurring test execution is not yet fully supported.
- **Recording playback** — "View Recording" is only available for sessions that used a Browserbase session; older or failed sessions may not have recording data.
- **Browser support** — Chrome is recommended; other modern browsers are supported but not fully tested.

If you find a bug that isn't listed, please report it using the steps in [Reporting Bugs](#reporting-bugs).
