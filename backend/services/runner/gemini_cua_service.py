"""
Gemini Computer Use Agent Service.

Uses the google.genai SDK with the native ComputerUse tool.
The CUA model returns function_call parts (click_at, type_text_at, etc.)
which are executed by the runner, then screenshots are sent back as
FunctionResponse blobs.
"""

import logging
import os
import time
from typing import Any, Dict, List, Tuple

from google import genai
from google.genai import types
from google.genai.types import Content, Part

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_CUA_STEPS = 50
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


# ---------------------------------------------------------------------------
# Coordinate helpers (model outputs 0-999 normalised coords)
# ---------------------------------------------------------------------------


def denormalize_x(x: int, screen_width: int = SCREEN_WIDTH) -> int:
    return int(x / 1000 * screen_width)


def denormalize_y(y: int, screen_height: int = SCREEN_HEIGHT) -> int:
    return int(y / 1000 * screen_height)


# ---------------------------------------------------------------------------
# Execute function calls from model response via Playwright
# ---------------------------------------------------------------------------


def execute_function_calls_sync(candidate, page, screen_width, screen_height):
    """
    Extract function_call parts from the model response and execute them
    on the Playwright page.  Returns a list of (name, result_dict) tuples.
    """
    function_calls = [
        part.function_call for part in candidate.content.parts if part.function_call
    ]

    results: List[Tuple[str, Dict[str, Any]]] = []

    for fc in function_calls:
        fname = fc.name
        args = dict(fc.args) if fc.args else {}
        action_result: Dict[str, Any] = {}
        logger.info("  -> Executing: %s  args=%s", fname, args)

        try:
            if fname == "open_web_browser":
                url = args.get("url", "")
                if url:
                    page.goto(url, wait_until="domcontentloaded")

            elif fname == "click_at":
                ax = denormalize_x(args["x"], screen_width)
                ay = denormalize_y(args["y"], screen_height)
                page.mouse.click(ax, ay)

            elif fname == "double_click_at":
                ax = denormalize_x(args["x"], screen_width)
                ay = denormalize_y(args["y"], screen_height)
                page.mouse.dblclick(ax, ay)

            elif fname == "hover_at":
                ax = denormalize_x(args["x"], screen_width)
                ay = denormalize_y(args["y"], screen_height)
                page.mouse.move(ax, ay)

            elif fname == "type_text_at":
                ax = denormalize_x(args["x"], screen_width)
                ay = denormalize_y(args["y"], screen_height)
                text = args.get("text", "")
                press_enter = args.get("press_enter", False)
                page.mouse.click(ax, ay)
                page.keyboard.press("Meta+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(text)
                if press_enter:
                    page.keyboard.press("Enter")

            elif fname == "key_combination":
                keys = args.get("keys", [])
                combo = "+".join(keys)
                page.keyboard.press(combo)

            elif fname == "scroll_at":
                ax = denormalize_x(args["x"], screen_width)
                ay = denormalize_y(args["y"], screen_height)
                direction = args.get("direction", "down")
                amount = args.get("amount", 3)
                delta = amount * 100 * (1 if direction == "down" else -1)
                page.mouse.move(ax, ay)
                page.mouse.wheel(0, delta)

            elif fname == "scroll_document":
                direction = args.get("direction", "down")
                amount = args.get("amount", 3)
                delta = amount * 100 * (1 if direction == "down" else -1)
                page.mouse.wheel(0, delta)

            elif fname == "wait_5_seconds":
                time.sleep(5)

            elif fname == "go_back":
                page.go_back()

            elif fname == "go_forward":
                page.go_forward()

            elif fname == "navigate":
                url = args.get("url", "")
                if url:
                    page.goto(url, wait_until="domcontentloaded")

            elif fname == "search":
                query = args.get("query", "")
                page.goto(
                    f"https://www.google.com/search?q={query}",
                    wait_until="domcontentloaded",
                )

            elif fname == "drag_and_drop":
                sx = denormalize_x(args["start_x"], screen_width)
                sy = denormalize_y(args["start_y"], screen_height)
                ex = denormalize_x(args["end_x"], screen_width)
                ey = denormalize_y(args["end_y"], screen_height)
                page.mouse.move(sx, sy)
                page.mouse.down()
                page.mouse.move(ex, ey)
                page.mouse.up()

            else:
                logger.warning("Unimplemented action: %s", fname)

            # Wait for the page to settle
            try:
                page.wait_for_load_state(timeout=5000)
            except Exception:
                pass
            time.sleep(1)

        except Exception as e:
            logger.error("Error executing %s: %s", fname, e)
            action_result = {"error": str(e)}

        results.append((fname, action_result))

    return results


# ---------------------------------------------------------------------------
# Build FunctionResponse parts with screenshot
# ---------------------------------------------------------------------------


def get_function_responses(page, results):
    """
    After executing actions, take a screenshot and build FunctionResponse
    objects to send back to the model.
    """
    screenshot_bytes = page.screenshot(type="png")
    current_url = page.url

    function_responses = []
    for name, result in results:
        response_data = {"url": current_url}
        response_data.update(result)
        function_responses.append(
            types.FunctionResponse(
                name=name,
                response=response_data,
                parts=[
                    types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png",
                            data=screenshot_bytes,
                        )
                    )
                ],
            )
        )

    return function_responses, screenshot_bytes


# ---------------------------------------------------------------------------
# Build the Gemini CUA client + config
# ---------------------------------------------------------------------------


def get_cua_client_and_config():
    """Return a configured genai Client and GenerateContentConfig."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    model_name = os.getenv(
        "GEMINI_MODEL_NAME", "gemini-2.5-computer-use-preview-10-2025"
    )

    config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                )
            )
        ],
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )

    return client, model_name, config
