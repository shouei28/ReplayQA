"""
Evaluator Service — use Gemini to decide pass/fail from screenshots.

Workflow:
1. Receive executed_steps list + screenshot bytes/URLs.
2. Build a multimodal prompt (text + images).
3. Call Gemini and parse structured PASS/FAIL response.
"""

import base64
import logging
import os
from typing import Any, Dict, List

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """You are a QA test evaluator. Analyse the web-application test execution described below.

**Test URL:** {url}

**Original Test Steps (what the user intended):**
{original_steps_text}

**Agent Execution Log (what the AI agent actually did):**
{execution_log}

**Expected Behaviour:**
{expected_behavior}

**Screenshots Provided:** {num_screenshots} (captured during execution, in order)

**Your Task:**
1. Map the agent's execution log to the original test steps.
2. For each ORIGINAL test step, decide if the agent successfully completed it.
3. Decide if the **overall** test PASSED or FAILED based on whether the final state matches the expected behaviour.

**Respond in EXACTLY this format (no markdown fences):**
RESULT: PASS or FAIL

STEP ANALYSIS:
Step 1: <one-line verdict for original test step 1>
Step 2: <one-line verdict for original test step 2>
...

EXPLANATION:
<2-4 sentence summary>
"""


def _build_prompt(
    original_steps: List[Dict[str, Any]],
    executed_steps: List[Dict[str, Any]],
    expected_behavior: str,
    url: str,
    num_screenshots: int,
) -> str:
    # Format original test steps
    original_lines = []
    for i, step in enumerate(original_steps, 1):
        instr = step.get("instruction", step.get("value", "unknown"))
        method = step.get("method", step.get("kind", ""))
        original_lines.append(f"{i}. [{method}] {instr}")

    # Format CUA execution log
    exec_lines = []
    for i, step in enumerate(executed_steps, 1):
        instr = step.get("instruction") or step.get("type") or "unknown"
        status = step.get("status", "unknown")
        exec_lines.append(f"  Turn {i}: {instr} (status: {status})")

    return _PROMPT_TEMPLATE.format(
        url=url,
        original_steps_text="\n".join(original_lines),
        execution_log="\n".join(exec_lines),
        expected_behavior=expected_behavior or "Not specified",
        num_screenshots=num_screenshots,
    )


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------


def _determine_success(analysis: str) -> bool:
    upper = analysis.upper()
    if "RESULT: PASS" in upper or "RESULT:PASS" in upper:
        return True
    if "RESULT: FAIL" in upper or "RESULT:FAIL" in upper:
        return False
    # Fallback heuristic
    return upper.count("PASS") > upper.count("FAIL")


def _count_passed_steps(analysis: str, total: int) -> int:
    passed = 0
    upper = analysis.upper()
    for i in range(1, total + 1):
        marker = f"STEP {i}:"
        idx = upper.find(marker)
        if idx == -1:
            continue
        end = upper.find(f"STEP {i + 1}:", idx) if i < total else len(upper)
        chunk = upper[idx:end]
        if any(kw in chunk for kw in ("PASS", "SUCCESS", "CORRECT", "COMPLETED")):
            passed += 1
    if passed == 0 and _determine_success(analysis):
        passed = total
    return passed


def _download_screenshot(url: str) -> bytes:
    """Download screenshot from URL and return raw bytes."""
    import requests as _req

    resp = _req.get(url, timeout=10)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Use a simpler model for evaluation (CUA model requires ComputerUse tool)
EVAL_MODEL = os.getenv("GEMINI_EVAL_MODEL", "gemini-2.0-flash")


def evaluate_test_results(
    test_execution_id: str,
    executed_steps: List[Dict[str, Any]],
    screenshots: List[Any],
    expected_behavior: str,
    url: str = "",
    original_steps: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Evaluate test results using Gemini multimodal.

    Returns dict with keys:
        success (bool), passed_steps (int), explanation (str),
        total_tokens (int), agent_output (str).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "success": False,
            "passed_steps": 0,
            "explanation": "GEMINI_API_KEY is not configured.",
            "total_tokens": 0,
            "agent_output": "",
        }

    client = genai.Client(api_key=api_key)

    # Filter out empty screenshot entries
    valid_screenshots = [s for s in screenshots if s]

    if not valid_screenshots:
        return {
            "success": False,
            "passed_steps": 0,
            "explanation": "No screenshots were captured — cannot evaluate.",
            "total_tokens": 0,
            "agent_output": "",
        }

    # Use original test steps as the basis for evaluation
    steps_for_eval = original_steps if original_steps else executed_steps
    num_eval_steps = len(steps_for_eval)

    prompt = _build_prompt(
        original_steps=steps_for_eval,
        executed_steps=executed_steps,
        expected_behavior=expected_behavior,
        url=url,
        num_screenshots=len(valid_screenshots),
    )

    # Build multimodal content parts
    parts = [types.Part(text=prompt)]

    for idx, shot in enumerate(valid_screenshots):
        parts.append(types.Part(text=f"\n--- Screenshot after step {idx + 1} ---"))

        # Handle different screenshot formats
        if isinstance(shot, bytes):
            parts.append(types.Part.from_bytes(data=shot, mime_type="image/png"))
        elif isinstance(shot, str) and shot.startswith("http"):
            try:
                img_bytes = _download_screenshot(shot)
                parts.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                )
            except Exception as exc:
                logger.warning("Failed to download screenshot %s: %s", shot, exc)
                parts.append(types.Part(text=f"[Screenshot unavailable: {exc}]"))
        elif isinstance(shot, str):
            # Assume base64
            img_bytes = base64.b64decode(shot)
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    try:
        response = client.models.generate_content(
            model=EVAL_MODEL,
            contents=parts,
        )
        analysis = response.text
        token_count = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            token_count = getattr(response.usage_metadata, "total_token_count", 0)

        success = _determine_success(analysis)
        passed = _count_passed_steps(analysis, num_eval_steps)

        logger.info(
            "Evaluation for %s: success=%s passed=%d/%d tokens=%d",
            test_execution_id,
            success,
            passed,
            num_eval_steps,
            token_count,
        )

        return {
            "success": success,
            "passed_steps": passed,
            "explanation": analysis,
            "total_tokens": token_count,
            "agent_output": analysis,
        }
    except Exception as exc:
        logger.error(
            "Gemini evaluation failed for %s: %s", test_execution_id, exc, exc_info=True
        )
        return {
            "success": False,
            "passed_steps": 0,
            "explanation": f"Evaluation error: {exc}",
            "total_tokens": 0,
            "agent_output": "",
        }
