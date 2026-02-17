"""
Playwright Action Executor — translate Gemini-returned commands into
browser actions via Playwright.

Gemini returns actions as dicts::

    {"name": "click_at", "args": {"y": 300, "x": 500}}

All coordinate-based commands use a **1000×1000 virtual grid** that is
scaled to the actual viewport dimensions before execution.

Usage::

    from services.runner.action_executor import execute_action

    result = await execute_action(page, {"name": "click_at", "args": {"x": 500, "y": 300}})
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Default viewport assumed when scaling coordinates.
GRID_SIZE = 1000


# ------------------------------------------------------------------
# Coordinate helpers
# ------------------------------------------------------------------

async def _viewport_size(page: Page) -> Tuple[int, int]:
    """Return (width, height) of the current viewport."""
    size = page.viewport_size
    if size:
        return size["width"], size["height"]
    # Fallback: evaluate from JS
    dims = await page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight})")
    return dims["w"], dims["h"]


def _scale(x: int, y: int, vw: int, vh: int) -> Tuple[float, float]:
    """Map 1000×1000-grid coords to real pixel coords."""
    return (x / GRID_SIZE) * vw, (y / GRID_SIZE) * vh


# ------------------------------------------------------------------
# Individual action handlers
# ------------------------------------------------------------------

async def _open_web_browser(page: Page, _args: Dict) -> Dict[str, Any]:
    """No-op — the browser is already open."""
    return {"success": True, "action": "open_web_browser"}


async def _wait_5_seconds(page: Page, _args: Dict) -> Dict[str, Any]:
    await asyncio.sleep(5)
    return {"success": True, "action": "wait_5_seconds"}


async def _go_back(page: Page, _args: Dict) -> Dict[str, Any]:
    await page.go_back(wait_until="networkidle")
    return {"success": True, "action": "go_back"}


async def _go_forward(page: Page, _args: Dict) -> Dict[str, Any]:
    await page.go_forward(wait_until="networkidle")
    return {"success": True, "action": "go_forward"}


async def _search(page: Page, _args: Dict) -> Dict[str, Any]:
    await page.goto("https://www.google.com", wait_until="networkidle")
    return {"success": True, "action": "search"}


async def _navigate(page: Page, args: Dict) -> Dict[str, Any]:
    url = args.get("url", "")
    if not url:
        return {"success": False, "action": "navigate", "error": "No url provided"}
    await page.goto(url, wait_until="networkidle")
    return {"success": True, "action": "navigate", "url": url}


async def _click_at(page: Page, args: Dict) -> Dict[str, Any]:
    vw, vh = await _viewport_size(page)
    px, py = _scale(int(args["x"]), int(args["y"]), vw, vh)
    await page.mouse.click(px, py)
    # Small wait for any triggered navigation / animation
    await page.wait_for_timeout(500)
    return {"success": True, "action": "click_at", "x": px, "y": py}


async def _hover_at(page: Page, args: Dict) -> Dict[str, Any]:
    vw, vh = await _viewport_size(page)
    px, py = _scale(int(args["x"]), int(args["y"]), vw, vh)
    await page.mouse.move(px, py)
    await page.wait_for_timeout(300)
    return {"success": True, "action": "hover_at", "x": px, "y": py}


async def _type_text_at(page: Page, args: Dict) -> Dict[str, Any]:
    vw, vh = await _viewport_size(page)
    px, py = _scale(int(args["x"]), int(args["y"]), vw, vh)
    text = str(args.get("text", ""))
    press_enter = args.get("press_enter", True)
    clear_first = args.get("clear_before_typing", True)

    # Click to focus
    await page.mouse.click(px, py)
    await page.wait_for_timeout(200)

    # Optionally clear existing content
    if clear_first:
        await page.keyboard.press("Meta+A")  # macOS; Control+A on Linux/Win
        await page.keyboard.press("Backspace")

    # Type character-by-character for realistic input
    await page.keyboard.type(text, delay=30)

    if press_enter:
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)

    return {"success": True, "action": "type_text_at", "text": text}


async def _key_combination(page: Page, args: Dict) -> Dict[str, Any]:
    keys = str(args.get("keys", ""))
    if "+" in keys:
        # e.g. "Control+C" → page.keyboard.press("Control+C")
        await page.keyboard.press(keys)
    else:
        await page.keyboard.press(keys)
    await page.wait_for_timeout(300)
    return {"success": True, "action": "key_combination", "keys": keys}


async def _scroll_document(page: Page, args: Dict) -> Dict[str, Any]:
    direction = str(args.get("direction", "down"))
    delta_map = {
        "down": (0, 600),
        "up": (0, -600),
        "right": (600, 0),
        "left": (-600, 0),
    }
    dx, dy = delta_map.get(direction, (0, 600))
    await page.mouse.wheel(dx, dy)
    await page.wait_for_timeout(400)
    return {"success": True, "action": "scroll_document", "direction": direction}


async def _scroll_at(page: Page, args: Dict) -> Dict[str, Any]:
    vw, vh = await _viewport_size(page)
    px, py = _scale(int(args["x"]), int(args["y"]), vw, vh)
    direction = str(args.get("direction", "down"))
    magnitude = int(args.get("magnitude", 800))

    # Move mouse to target element first
    await page.mouse.move(px, py)

    scale_factor = magnitude / GRID_SIZE
    delta_map = {
        "down": (0, int(vh * scale_factor)),
        "up": (0, -int(vh * scale_factor)),
        "right": (int(vw * scale_factor), 0),
        "left": (-int(vw * scale_factor), 0),
    }
    dx, dy = delta_map.get(direction, (0, int(vh * scale_factor)))
    await page.mouse.wheel(dx, dy)
    await page.wait_for_timeout(400)
    return {"success": True, "action": "scroll_at", "direction": direction}


async def _drag_and_drop(page: Page, args: Dict) -> Dict[str, Any]:
    vw, vh = await _viewport_size(page)
    sx, sy = _scale(int(args["x"]), int(args["y"]), vw, vh)
    dx, dy = _scale(int(args["destination_x"]), int(args["destination_y"]), vw, vh)

    await page.mouse.move(sx, sy)
    await page.mouse.down()
    # Move in small steps for smoother drag
    steps = 10
    for i in range(1, steps + 1):
        ix = sx + (dx - sx) * i / steps
        iy = sy + (dy - sy) * i / steps
        await page.mouse.move(ix, iy)
        await page.wait_for_timeout(30)
    await page.mouse.up()
    await page.wait_for_timeout(300)
    return {"success": True, "action": "drag_and_drop"}


# ------------------------------------------------------------------
# Dispatch table
# ------------------------------------------------------------------

_ACTION_MAP = {
    "open_web_browser": _open_web_browser,
    "wait_5_seconds": _wait_5_seconds,
    "go_back": _go_back,
    "go_forward": _go_forward,
    "search": _search,
    "navigate": _navigate,
    "click_at": _click_at,
    "hover_at": _hover_at,
    "type_text_at": _type_text_at,
    "key_combination": _key_combination,
    "scroll_document": _scroll_document,
    "scroll_at": _scroll_at,
    "drag_and_drop": _drag_and_drop,
}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

async def execute_action(
    page: Page,
    action: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a single Gemini-returned action on a Playwright page.

    Args:
        page: Playwright ``Page`` instance.
        action: Dict with ``name`` (str) and ``args`` (dict).

    Returns:
        Result dict with ``success``, ``action``, and any extra info.
    """
    name = action.get("name", "")
    args = action.get("args", {})

    handler = _ACTION_MAP.get(name)
    if handler is None:
        logger.warning("Unknown action: %s", name)
        return {"success": False, "action": name, "error": f"Unknown action: {name}"}

    start = time.time()
    try:
        result = await handler(page, args)
        result["duration_ms"] = round((time.time() - start) * 1000)
        logger.info("Executed %s in %dms", name, result["duration_ms"])
        return result
    except Exception as exc:
        logger.error("Action %s failed: %s", name, exc, exc_info=True)
        return {
            "success": False,
            "action": name,
            "error": str(exc),
            "duration_ms": round((time.time() - start) * 1000),
        }


async def execute_actions(
    page: Page,
    actions: list[Dict[str, Any]],
    screenshot_callback=None,
) -> list[Dict[str, Any]]:
    """
    Execute a sequence of Gemini actions, optionally capturing a
    screenshot after each one.

    Args:
        page: Playwright ``Page`` instance.
        actions: List of action dicts.
        screenshot_callback: Optional async callable ``(page, step_num) -> url``
            called after each action to capture a screenshot.

    Returns:
        List of result dicts (one per action).
    """
    results: list[Dict[str, Any]] = []
    for idx, action in enumerate(actions):
        result = await execute_action(page, action)
        result["step_number"] = idx + 1

        if screenshot_callback:
            try:
                url = await screenshot_callback(page, idx + 1)
                result["screenshot_url"] = url
            except Exception as exc:
                logger.warning("Screenshot callback failed at step %d: %s", idx + 1, exc)

        results.append(result)

        # Stop early on critical failure (navigation error, crash, etc.)
        if not result["success"] and action.get("name") in ("navigate",):
            logger.error("Stopping execution after critical failure at step %d", idx + 1)
            break

    return results
