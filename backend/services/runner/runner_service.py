"""
Runner Service — execute test steps via Playwright on a Browserbase session.

Flow:
1. Fetch TestExecution from DB, mark as *running*.
2. Create Browserbase session (via BrowserSlotManager).
3. Connect Playwright to the session via CDP.
4. Navigate to the target URL.
5. Execute each Gemini-returned action (click_at, type_text_at, …) via
   the action_executor, capturing a screenshot after every step.
6. Hand screenshots + step metadata to the EvaluatorService (Gemini).
7. Persist a TestResult and update TestExecution to *completed* / *failed*.
8. Clean up (close browser, release slot).
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from django.utils import timezone

from core.models import TestExecution, TestResult
from services.browser_slot_manager import get_slot_manager
from services.runner.action_executor import execute_action
from services.runner.evaluator_service import evaluate_test_results
from services.runner.storage_service import upload_screenshot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _viewport_for_device(device: str) -> Dict[str, int]:
    if device == "mobile":
        return {"width": 375, "height": 667}
    return {"width": 1280, "height": 720}


def _create_browser_session(device: str = "desktop", browser: str = "chrome") -> Dict[str, Any]:
    """Create a Browserbase session and acquire a browser slot."""
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


def _update_progress(execution: TestExecution, progress: int, message: str) -> None:
    execution.progress = progress
    execution.message = message
    execution.save(update_fields=["progress", "message", "updated_at"])


async def _capture_screenshot_async(page, execution_id: str, step_number: int) -> str:
    """Take a full-page screenshot and upload it; returns public URL or ''."""
    try:
        img_bytes = await page.screenshot(full_page=True)
        return upload_screenshot(str(execution_id), step_number, img_bytes)
    except Exception as exc:
        logger.error("Screenshot capture/upload failed (step %d): %s", step_number, exc)
        return ""


# ---------------------------------------------------------------------------
# Async step execution (using action_executor)
# ---------------------------------------------------------------------------

async def _execute_steps_async(
    page,
    steps: List[Dict[str, Any]],
    execution: TestExecution,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Walk through *steps* one-by-one using the Playwright action executor.

    Each step is a Gemini-returned command dict:
        {"name": "click_at", "args": {"x": 500, "y": 300}}

    Returns (executed_steps, screenshot_urls).
    """
    executed: List[Dict[str, Any]] = []
    screenshots: List[str] = []
    total = len(steps)

    for idx, step in enumerate(steps):
        step_num = idx + 1
        progress = 10 + int((step_num / total) * 70)
        _update_progress(execution, progress, f"Executing step {step_num}/{total}")

        # Execute via action_executor
        result = await execute_action(page, step)
        result["step_number"] = step_num
        result["instruction"] = _describe_action(step)
        result["type"] = step.get("name", "unknown")
        result["status"] = "passed" if result.get("success") else "failed"
        result["timestamp"] = datetime.now().isoformat()

        # Always attempt a screenshot (even on failure)
        url = await _capture_screenshot_async(page, str(execution.id), step_num)
        if url:
            screenshots.append(url)
            result["screenshot_url"] = url

        executed.append(result)

    return executed, screenshots


def _describe_action(step: Dict[str, Any]) -> str:
    """Human-readable description of a Gemini action."""
    name = step.get("name", "unknown")
    args = step.get("args", {})

    if name == "navigate":
        return f"Navigate to {args.get('url', '?')}"
    if name == "click_at":
        return f"Click at ({args.get('x')}, {args.get('y')})"
    if name == "type_text_at":
        return f"Type \"{args.get('text', '')}\" at ({args.get('x')}, {args.get('y')})"
    if name == "scroll_document":
        return f"Scroll {args.get('direction', 'down')}"
    if name == "scroll_at":
        return f"Scroll {args.get('direction', 'down')} at ({args.get('x')}, {args.get('y')})"
    if name == "hover_at":
        return f"Hover at ({args.get('x')}, {args.get('y')})"
    if name == "key_combination":
        return f"Press {args.get('keys', '?')}"
    if name == "drag_and_drop":
        return f"Drag ({args.get('x')}, {args.get('y')}) → ({args.get('destination_x')}, {args.get('destination_y')})"
    if name == "wait_5_seconds":
        return "Wait 5 seconds"
    if name == "go_back":
        return "Go back"
    if name == "go_forward":
        return "Go forward"
    if name == "search":
        return "Navigate to Google"
    return name


# ---------------------------------------------------------------------------
# Async pipeline core
# ---------------------------------------------------------------------------

async def _run_pipeline_async(execution: TestExecution) -> Dict[str, Any]:
    """The async heart of the pipeline — connect Playwright, run steps, evaluate."""
    from playwright.async_api import async_playwright

    session_info: Dict[str, Any] = {}
    pw_context = None
    browser = None

    try:
        # 1. Browser session
        _update_progress(execution, 5, "Creating browser session")
        session_info = _create_browser_session(
            execution.device or "desktop",
            execution.browser or "chrome",
        )
        execution.browserbase_session_id = session_info["session_id"]
        execution.save(update_fields=["browserbase_session_id", "updated_at"])

        # 2. Connect Playwright via CDP
        _update_progress(execution, 8, "Connecting Playwright")
        pw_context = await async_playwright().start()
        browser = await pw_context.chromium.connect_over_cdp(session_info["connect_url"])

        # Get (or create) the first page
        default_ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = default_ctx.pages[0] if default_ctx.pages else await default_ctx.new_page()

        # Set viewport
        vp = _viewport_for_device(execution.device or "desktop")
        await page.set_viewport_size(vp)

        # 3. Navigate to target URL
        _update_progress(execution, 10, "Navigating to target URL")
        await page.goto(execution.url, wait_until="networkidle")

        # 4. Execute steps (Gemini-returned actions)
        executed_steps, screenshots = await _execute_steps_async(
            page, execution.steps, execution,
        )

        runtime = (timezone.now() - execution.started_at).total_seconds()

        # 5. Evaluate with Gemini
        _update_progress(execution, 85, "Evaluating results with AI")
        evaluation = evaluate_test_results(
            test_execution_id=str(execution.id),
            executed_steps=executed_steps,
            screenshots=screenshots,
            expected_behavior=execution.expected_behavior,
            url=execution.url,
        )

        # 6. Persist TestResult
        test_result = TestResult.objects.create(
            test_execution=execution,
            user=execution.user,
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
            "Pipeline completed for %s — success=%s",
            execution.id,
            evaluation["success"],
        )
        return {
            "status": "completed",
            "test_execution_id": str(execution.id),
            "test_result_id": str(test_result.id),
            "success": evaluation["success"],
        }

    finally:
        # Cleanup
        if browser:
            try:
                await browser.close()
            except Exception as ce:
                logger.warning("Browser close error: %s", ce)
        if pw_context:
            try:
                await pw_context.stop()
            except Exception as ce:
                logger.warning("Playwright stop error: %s", ce)
        if session_info:
            _release_slot(
                session_info.get("device", "desktop"),
                session_info.get("browser", "chrome"),
            )


# ---------------------------------------------------------------------------
# Sync entry point (called from Celery)
# ---------------------------------------------------------------------------

def execute_test(test_execution_id: str) -> Dict[str, Any]:
    """
    End-to-end test execution pipeline.

    Called by the Celery task ``core.tasks.run_test_execution``.
    """
    logger.info("Starting pipeline for execution %s", test_execution_id)

    try:
        execution = TestExecution.objects.get(id=test_execution_id)
    except TestExecution.DoesNotExist:
        logger.error("TestExecution %s not found", test_execution_id)
        return {"status": "error", "message": "TestExecution not found"}

    # Mark running
    execution.status = "running"
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at", "updated_at"])

    try:
        # Run the async pipeline in a new event loop
        result = asyncio.run(_run_pipeline_async(execution))
        return result

    except Exception as exc:
        logger.error(
            "Pipeline failed for %s: %s", test_execution_id, exc, exc_info=True,
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
