"""
Runner Service — Gemini CUA agentic loop on a Browserbase session.

Uses the google.genai SDK with the native ComputerUse tool.
The model returns function_call parts which we execute via Playwright
and send back as FunctionResponse with screenshot blobs.

Flow:
1. Fetch TestExecution from DB, mark as *running*.
2. Create Browserbase session.
3. Connect Playwright to the session via CDP.
4. Navigate to the target URL.
5. CUA agent loop:
   a. Send prompt + initial screenshot → Gemini
   b. Model returns function_call parts (click_at, type_text_at, etc.)
   c. Execute actions via Playwright
   d. Take screenshot, send back as FunctionResponse
   e. Repeat until model returns text-only (no more actions) or max turns
6. Evaluate with Gemini for pass/fail.
7. Persist TestResult, update TestExecution.
"""

import logging
import os
from datetime import datetime

# google.genai uses httpx/anyio internally, which creates an async context.
# Django detects this and blocks sync ORM calls. This flag disables that check.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
from typing import Any, Dict, List

from asgiref.sync import sync_to_async
from django.utils import timezone
from playwright.sync_api import sync_playwright

from google.genai.types import Content, Part

from core.models import TestExecution, TestResult
from services.browser_slot_manager import get_slot_manager
from services.runner.gemini_cua_service import (
    MAX_CUA_STEPS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    execute_function_calls_sync,
    get_cua_client_and_config,
    get_function_responses,
)
from services.runner.evaluator_service import evaluate_test_results
from services.runner.storage_service import upload_screenshot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _viewport_for_device(device: str) -> Dict[str, int]:
    if device == "mobile":
        return {"width": 375, "height": 667}
    return {"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}


def _create_browser_session(
    device: str = "desktop", browser: str = "chrome"
) -> Dict[str, Any]:
    project_id = os.getenv("BROWSERBASE_PROJECT_ID", "")
    slot_mgr = get_slot_manager()
    slot_mgr.acquire_slot(device, browser)

    try:
        session = slot_mgr.create_session_with_retry(
            project_id=project_id,
            browser_settings={"viewport": _viewport_for_device(device)},
            device=device,
            browser=browser,
        )
        return {
            "session_id": session.id,
            "connect_url": session.connect_url,
            "device": device,
            "browser": browser,
        }
    except Exception:
        slot_mgr.release_slot(device, browser)
        raise


def _release_slot(device: str = "desktop", browser: str = "chrome") -> None:
    try:
        get_slot_manager().release_slot(device, browser)
    except Exception as exc:
        logger.warning("Error releasing browser slot: %s", exc)


# ---------------------------------------------------------------------------
# Build prompt from test steps
# ---------------------------------------------------------------------------


def _build_user_prompt(execution: TestExecution) -> str:
    """Build the initial prompt with all test context."""
    steps_text = ""
    for i, step in enumerate(execution.steps, 1):
        instruction = step.get("instruction", step.get("value", ""))
        method = step.get("method", step.get("kind", ""))
        steps_text += f"  {i}. [{method}] {instruction}\n"

    return (
        f"You are a QA test agent. Execute these test steps on the web page:\n\n"
        f"URL: {execution.url}\n"
        f"Test: {execution.test_name}\n"
        f"Description: {execution.description}\n\n"
        f"Steps to execute:\n{steps_text}\n"
        f"Expected behavior: {execution.expected_behavior}\n\n"
        f"Execute each step carefully. After completing all steps, "
        f"describe what you observed and whether the expected behavior was met."
    )


# ---------------------------------------------------------------------------
# Sync CUA agent loop (runs inside sync_playwright)
# ---------------------------------------------------------------------------


def _run_cua_loop(
    page,
    execution: TestExecution,
    screen_width: int,
    screen_height: int,
) -> Dict[str, Any]:
    """
    The core CUA agent loop using the google.genai SDK.

    Returns dict with: executed_steps, screenshot_urls, success, final_text
    """
    client, model_name, config = get_cua_client_and_config()

    executed_steps: List[Dict[str, Any]] = []
    screenshot_urls: List[str] = []
    screenshot_bytes_list: List[bytes] = []  # raw bytes for evaluator

    # Take initial screenshot
    initial_screenshot = page.screenshot(type="png")
    screenshot_bytes_list.append(initial_screenshot)

    # Try to upload initial screenshot (best-effort, not required)
    try:
        url = upload_screenshot(str(execution.id), 0, initial_screenshot)
        if url:
            screenshot_urls.append(url)
    except Exception as exc:
        logger.warning("Initial screenshot upload failed: %s", exc)

    # Build initial content with prompt + screenshot
    user_prompt = _build_user_prompt(execution)
    contents = [
        Content(
            role="user",
            parts=[
                Part(text=user_prompt),
                Part.from_bytes(data=initial_screenshot, mime_type="image/png"),
            ],
        )
    ]

    final_text = ""
    turn_limit = MAX_CUA_STEPS

    for turn in range(1, turn_limit + 1):
        logger.info("--- CUA Turn %d ---", turn)

        # Update execution progress
        progress = 10 + int((turn / turn_limit) * 70)
        execution.progress = min(progress, 80)
        execution.message = f"CUA turn {turn} — thinking…"
        execution.save(update_fields=["progress", "message", "updated_at"])

        # Call Gemini
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            logger.error("Gemini CUA call failed at turn %d: %s", turn, exc)
            executed_steps.append(
                {
                    "step_number": turn,
                    "thought": f"Gemini API error: {exc}",
                    "action": {"name": "error"},
                    "status": "failed",
                    "error": str(exc),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            break

        candidate = response.candidates[0]

        # Append model response to conversation history
        contents.append(candidate.content)

        # Check if there are function calls
        has_function_calls = any(part.function_call for part in candidate.content.parts)

        if not has_function_calls:
            # Model is done — extract text response
            final_text = " ".join(
                part.text for part in candidate.content.parts if part.text
            )
            logger.info("Agent finished at turn %d: %s", turn, final_text[:200])

            executed_steps.append(
                {
                    "step_number": turn,
                    "thought": final_text,
                    "action": {"name": "done"},
                    "instruction": "Test completed",
                    "type": "done",
                    "status": "passed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            break

        # Extract thoughts from text parts
        thoughts = [part.text for part in candidate.content.parts if part.text]
        thought_text = " ".join(thoughts) if thoughts else ""

        # Extract action names for logging
        action_names = [
            part.function_call.name
            for part in candidate.content.parts
            if part.function_call
        ]
        logger.info(
            "Turn %d — thought: %s | actions: %s",
            turn,
            thought_text[:100],
            action_names,
        )

        # Update progress with action info
        execution.message = f"CUA turn {turn} — executing: {', '.join(action_names)}"
        execution.save(update_fields=["message", "updated_at"])

        # Execute the function calls via Playwright
        results = execute_function_calls_sync(
            candidate, page, screen_width, screen_height
        )

        # Build function responses with new screenshot
        function_responses, screenshot_bytes = get_function_responses(page, results)
        screenshot_bytes_list.append(screenshot_bytes)  # keep raw bytes for evaluator

        # Upload screenshot (best-effort, not required for evaluation)
        try:
            url = upload_screenshot(str(execution.id), turn, screenshot_bytes)
            if url:
                screenshot_urls.append(url)
        except Exception as exc:
            logger.warning("Screenshot upload failed at turn %d: %s", turn, exc)

        # Append function responses to conversation history
        contents.append(
            Content(
                role="user",
                parts=[Part(function_response=fr) for fr in function_responses],
            )
        )

        # Record executed steps
        for fname, result in results:
            executed_steps.append(
                {
                    "step_number": turn,
                    "thought": thought_text,
                    "action": {"name": fname},
                    "instruction": thought_text,
                    "type": fname,
                    "status": "failed" if result.get("error") else "passed",
                    "error": result.get("error"),
                    "screenshot_url": screenshot_urls[-1] if screenshot_urls else "",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    return {
        "executed_steps": executed_steps,
        "screenshot_urls": screenshot_urls,
        "screenshot_bytes": screenshot_bytes_list,
        "final_text": final_text,
    }


# ---------------------------------------------------------------------------
# Full pipeline (sync — called from Celery)
# ---------------------------------------------------------------------------


def execute_test(test_execution_id: str) -> Dict[str, Any]:
    """
    End-to-end test execution pipeline.
    Called by Celery task or directly from Django shell.
    """
    logger.info("Starting CUA pipeline for execution %s", test_execution_id)

    try:
        execution = TestExecution.objects.select_related("user").get(
            id=test_execution_id
        )
    except TestExecution.DoesNotExist:
        logger.error("TestExecution %s not found", test_execution_id)
        return {"status": "error", "message": "TestExecution not found"}

    execution.status = "running"
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at", "updated_at"])

    session_info: Dict[str, Any] = {}
    pw = None
    browser = None

    try:
        # 1. Create browser session
        execution.progress = 5
        execution.message = "Creating browser session"
        execution.save(update_fields=["progress", "message", "updated_at"])

        session_info = _create_browser_session(
            execution.device or "desktop",
            execution.browser or "chrome",
        )
        execution.browserbase_session_id = session_info["session_id"]
        execution.save(update_fields=["browserbase_session_id", "updated_at"])

        # 2. Connect Playwright via CDP
        execution.message = "Connecting Playwright"
        execution.save(update_fields=["message", "updated_at"])

        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(session_info["connect_url"])

        default_ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = default_ctx.pages[0] if default_ctx.pages else default_ctx.new_page()

        vp = _viewport_for_device(execution.device or "desktop")
        page.set_viewport_size(vp)

        # 3. Navigate to target URL
        execution.progress = 10
        execution.message = "Navigating to target URL"
        execution.save(update_fields=["progress", "message", "updated_at"])

        page.goto(execution.url, wait_until="networkidle")

        # 4. Run the CUA agent loop
        loop_result = _run_cua_loop(
            page=page,
            execution=execution,
            screen_width=vp["width"],
            screen_height=vp["height"],
        )

        executed_steps = loop_result["executed_steps"]
        screenshot_urls = loop_result["screenshot_urls"]
        screenshot_bytes_list = loop_result.get("screenshot_bytes", [])

        runtime = (timezone.now() - execution.started_at).total_seconds()

        # 5. Evaluate with Gemini (pass/fail)
        # Prefer raw bytes (always available) over URLs (may fail with Supabase)
        eval_screenshots = (
            screenshot_bytes_list if screenshot_bytes_list else screenshot_urls
        )

        execution.progress = 85
        execution.message = "Evaluating results with AI"
        execution.save(update_fields=["progress", "message", "updated_at"])

        evaluation = evaluate_test_results(
            test_execution_id=str(execution.id),
            executed_steps=executed_steps,
            screenshots=eval_screenshots,
            expected_behavior=execution.expected_behavior,
            url=execution.url,
        )

        # 6. Persist TestResult
        test_result = TestResult.objects.create(
            test_execution=execution,
            user_id=execution.user_id,
            test_name=execution.test_name,
            description=execution.description,
            url=execution.url,
            steps=execution.steps,
            expected_behavior=execution.expected_behavior,
            success=evaluation["success"],
            total_steps=len(execution.steps),
            passed_steps=evaluation["passed_steps"],
            executed_steps=executed_steps,
            runtime_sec=runtime,
            started_at=execution.started_at,
            total_tokens=evaluation.get("total_tokens", 0),
            explanation=evaluation.get("explanation", ""),
            agent_output=evaluation.get("agent_output", ""),
        )

        # 7. Mark completed
        execution.status = "completed"
        execution.completed_at = timezone.now()
        execution.total_runtime_sec = runtime
        execution.progress = 100
        execution.message = "Test execution completed"
        execution.save()

        logger.info(
            "Pipeline completed for %s — success=%s, turns=%d",
            execution.id,
            evaluation["success"],
            len(executed_steps),
        )
        return {
            "status": "completed",
            "test_execution_id": str(execution.id),
            "test_result_id": str(test_result.id),
            "success": evaluation["success"],
        }

    except Exception as exc:
        logger.error(
            "Pipeline failed for %s: %s",
            test_execution_id,
            exc,
            exc_info=True,
        )
        execution.status = "failed"
        execution.completed_at = timezone.now()
        execution.error_message = str(exc)
        execution.message = f"Execution failed: {exc}"
        if execution.started_at:
            execution.total_runtime_sec = (
                timezone.now() - execution.started_at
            ).total_seconds()
        execution.save()
        return {
            "status": "failed",
            "test_execution_id": str(execution.id),
            "error": str(exc),
        }

    finally:
        if browser:
            try:
                browser.close()
            except Exception as ce:
                logger.warning("Browser close error: %s", ce)
        if pw:
            try:
                pw.stop()
            except Exception as ce:
                logger.warning("Playwright stop error: %s", ce)
        if session_info:
            _release_slot(
                session_info.get("device", "desktop"),
                session_info.get("browser", "chrome"),
            )
