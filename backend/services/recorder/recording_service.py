"""Recording pipeline: Playwright connect, inject script, polling loop, keep-alive."""

import os
import threading
import time
from io import BytesIO

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from . import state
from .describe_element import describe_element_from_screenshot
from .normalization import compact_payload
from .script import build_recorder_script


def _crop_screenshot_around_cursor(
    screenshot_bytes: bytes,
    cursor_x: int,
    cursor_y: int,
) -> tuple[bytes, int, int]:
    """Crop screenshot to half width × half height, centered on cursor. Clamp to image bounds.
    Returns (cropped_bytes, cursor_x_in_crop, cursor_y_in_crop)."""
    img = Image.open(BytesIO(screenshot_bytes)).convert("RGB")
    w, h = img.size
    crop_w = max(1, w // 2)
    crop_h = max(1, h // 2)
    left = max(0, min(int(cursor_x - crop_w / 2), w - crop_w))
    top = max(0, min(int(cursor_y - crop_h / 2), h - crop_h))
    right = min(left + crop_w, w)
    bottom = min(top + crop_h, h)
    cropped = img.crop((left, top, right, bottom))
    cx_crop = int(cursor_x - left)
    cy_crop = int(cursor_y - top)
    buf = BytesIO()
    cropped.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), cx_crop, cy_crop


def _annotate_cursor_on_image(
    image_bytes: bytes, cursor_x: int, cursor_y: int
) -> bytes:
    """Draw a red circle at cursor position for debugging."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    r = 20
    draw.ellipse(
        (cursor_x - r, cursor_y - r, cursor_x + r, cursor_y + r),
        outline="red",
        width=4,
    )
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _enrich_action_with_llm_description(action: dict, page_ref) -> None:
    """Replace fallback description with LLM-generated description using cropped screenshot."""
    try:
        screenshot_bytes = page_ref.screenshot(type="jpeg")
    except Exception as e:
        print(f"[RECORDER] LLM enrichment skipped: screenshot failed ({e})")
        return
    cursor_pos = action.get("cursor_position") or {}
    cx = cursor_pos.get("x", 0)
    cy = cursor_pos.get("y", 0)
    dpr = cursor_pos.get("device_pixel_ratio", 1)
    cx_scaled = int(cx * dpr)
    cy_scaled = int(cy * dpr)
    cropped, cx_crop, cy_crop = _crop_screenshot_around_cursor(
        screenshot_bytes, cx_scaled, cy_scaled
    )

    # Annotate the cropped image with cursor position for LLM
    annotated = _annotate_cursor_on_image(cropped, cx_crop, cy_crop)

    orig = action.get("description", "")
    orig_preview = orig[:50] + ("..." if len(orig) > 50 else "")
    print(
        f"[RECORDER] Enriching fallback description via LLM: method={action.get('method')}, "
        f"original='{orig_preview}', cursor=({cx},{cy}) dpr={dpr} -> scaled({cx_scaled},{cy_scaled})"
    )
    result = describe_element_from_screenshot(
        annotated,
        action.get("selector", ""),
        action.get("method", "click"),
    )
    if result is None:
        print("[RECORDER] LLM enrichment failed, keeping original description")
        return
    action["description"] = result
    action.pop("needs_llm_description", None)
    action.pop("raw_description", None)
    action.pop("cursor_position", None)


def start_recording(
    session_id: str,
    browserbase_session_id: str,
    connect_url: str | None,
    device: str = "desktop",
    slot_browser: str = "chrome",
    initial_url: str | None = None,
) -> None:
    """
    Start a daemon thread that connects Playwright to Browserbase, optionally navigates to
    initial_url, injects the capture script, and runs the polling loop.
    """
    if not connect_url:
        connect_url = (
            f"wss://connect.browserbase.com/v1/sessions/{browserbase_session_id}"
        )

    def _thread():
        page = None
        browser = None
        # Register session immediately so get_recorded_actions returns session_closed=False
        # while we connect. Otherwise the frontend polls before we're ready and shows "Session closed".
        actions_queue = []
        with state.recording_lock:
            state.recording_sessions[session_id] = {
                "playwright": None,
                "browser": None,
                "page": None,
                "recording_enabled": True,
                "browserbase_session_id": browserbase_session_id,
                "connect_url": connect_url,
                "actions_queue": actions_queue,
                "device": device,
                "slot_browser": slot_browser,
            }
        try:
            with sync_playwright() as playwright:
                chromium = playwright.chromium
                browser = chromium.connect_over_cdp(connect_url, timeout=30000)
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                if initial_url:
                    # Use domcontentloaded for faster init: DOM ready sooner, recorder active earlier.
                    # networkidle can add several seconds on heavy pages; we only need DOM for recording.
                    page.goto(
                        initial_url, wait_until="domcontentloaded", timeout=60000
                    )

                recorder_script = build_recorder_script(session_id)
                # Use add_init_script so the recorder runs on every navigation (CDP Page.addScriptToEvaluateOnNewDocument).
                # This runs automatically on each new document load—no manual re-injection, no duplicate listeners.
                page.add_init_script(recorder_script)
                # Run once for the current page (already loaded); add_init_script only runs on future navigations.
                page.evaluate(recorder_script)

                with state.recording_lock:
                    if session_id in state.recording_sessions:
                        state.recording_sessions[session_id].update(
                            {
                                "playwright": playwright,
                                "browser": browser,
                                "page": page,
                            }
                        )

                last_poll_time = time.time()
                last_keepalive_time = time.time()
                keepalive_interval = (
                    60  # seconds; ping Browserbase to avoid idle disconnect
                )
                session_active = True
                consecutive_errors = 0
                max_consecutive_errors = 10

                while session_active:
                    try:
                        page_ref = None
                        recording_enabled = False

                        with state.recording_lock:
                            session_data = state.recording_sessions.get(session_id)
                            if not session_data:
                                session_active = False
                                print(
                                    f"[RECORDER] Session {session_id} deleted, exiting polling loop"
                                )
                                break
                            page_ref = session_data.get("page")
                            recording_enabled = session_data.get(
                                "recording_enabled", False
                            )

                        if not page_ref:
                            time.sleep(0.1)
                            continue

                        current_time = time.time()
                        if current_time - last_keepalive_time >= keepalive_interval:
                            try:
                                browserbase_api_key = os.environ.get(
                                    "BROWSERBASE_API_KEY"
                                )
                                if browserbase_api_key and browserbase_session_id:
                                    from browserbase import Browserbase

                                    bb = Browserbase(api_key=browserbase_api_key)
                                    session_info = bb.sessions.retrieve(
                                        browserbase_session_id
                                    )
                                    if session_info:
                                        last_keepalive_time = current_time
                                        print(
                                            f"[RECORDER] Keep-alive ping for Browserbase session {browserbase_session_id}"
                                        )
                                    else:
                                        print(
                                            f"[RECORDER] Browserbase session {browserbase_session_id} not found; releasing slot and exiting"
                                        )
                                        state.release_slot_and_remove_session(
                                            session_id
                                        )
                                        session_active = False
                                        break
                            except Exception as keepalive_error:
                                err_str = str(keepalive_error).lower()
                                if (
                                    "not found" in err_str
                                    or "404" in err_str
                                    or "session" in err_str
                                ):
                                    print(
                                        f"[RECORDER] Browserbase session gone (keep-alive error): {keepalive_error}; releasing slot"
                                    )
                                    state.release_slot_and_remove_session(session_id)
                                    session_active = False
                                    break
                                print(
                                    f"[RECORDER] Keep-alive ping failed: {keepalive_error}"
                                )

                        try:
                            # Update recording enabled flag; add_init_script handles persistence across navigations.
                            page_ref.evaluate(
                                f"() => {{ window.__qualty_recording_enabled = {str(recording_enabled).lower()}; }}"
                            )
                            consecutive_errors = 0

                            if current_time - last_poll_time >= 0.5:
                                if recording_enabled:
                                    try:
                                        actions = page_ref.evaluate(
                                            "() => window.__qualty_actions || []"
                                        )
                                        if actions:
                                            page_ref.evaluate(
                                                "() => { window.__qualty_actions = []; }"
                                            )
                                            normalized_actions = []
                                            for action in actions:
                                                if (
                                                    action.get("needs_llm_description")
                                                    and page_ref
                                                ):
                                                    try:
                                                        _enrich_action_with_llm_description(
                                                            action, page_ref
                                                        )
                                                    except Exception:
                                                        pass
                                                compact_action = compact_payload(action)
                                                if (
                                                    isinstance(compact_action, dict)
                                                    and compact_action
                                                ):
                                                    normalized_actions.append(
                                                        compact_action
                                                    )
                                            with state.recording_lock:
                                                if (
                                                    session_id
                                                    in state.recording_sessions
                                                ):
                                                    state.recording_sessions[
                                                        session_id
                                                    ]["actions_queue"].extend(
                                                        normalized_actions
                                                    )
                                    except Exception as poll_error:
                                        consecutive_errors += 1
                                        with state.recording_lock:
                                            if (
                                                session_id
                                                not in state.recording_sessions
                                            ):
                                                session_active = False
                                                break
                                        if consecutive_errors <= 3:
                                            print(
                                                f"[RECORDER] Error polling actions: {poll_error}"
                                            )
                                        if consecutive_errors >= max_consecutive_errors:
                                            print(
                                                f"[RECORDER] Too many consecutive polling errors, exiting loop and cleaning up session"
                                            )
                                            state.release_slot_and_remove_session(
                                                session_id
                                            )
                                            session_active = False
                                            break
                                last_poll_time = current_time

                        except Exception as page_error:
                            consecutive_errors += 1
                            with state.recording_lock:
                                if session_id not in state.recording_sessions:
                                    session_active = False
                                    break
                            if consecutive_errors <= 3:
                                print(
                                    f"[RECORDER] Warning: Page evaluate failed (session still exists): {page_error}"
                                )
                            if consecutive_errors >= max_consecutive_errors:
                                print(
                                    f"[RECORDER] Too many consecutive page errors, exiting loop and cleaning up session"
                                )
                                state.release_slot_and_remove_session(session_id)
                                session_active = False
                                break
                            current_time = time.time()
                            if current_time - last_poll_time >= 0.5:
                                last_poll_time = current_time

                    except Exception as e:
                        consecutive_errors += 1
                        print(
                            f"[RECORDER] Unexpected error in polling loop ({consecutive_errors}/{max_consecutive_errors}): {e}"
                        )
                        with state.recording_lock:
                            if session_id not in state.recording_sessions:
                                session_active = False
                                break
                        if consecutive_errors >= max_consecutive_errors:
                            print(
                                f"[RECORDER] Too many consecutive errors, exiting polling loop and cleaning up session"
                            )
                            state.release_slot_and_remove_session(session_id)
                            session_active = False
                            break

                    time.sleep(0.1)

                print(f"[RECORDER] Polling loop ended for session {session_id}")

        except Exception as e:
            print(f"[RECORDER] Recording thread error: {e}")
            import traceback

            traceback.print_exc()
            state.release_slot_and_remove_session(session_id)
            try:
                if page:
                    page.close()
            except Exception:
                pass
            try:
                if browser:
                    browser.close()
            except Exception:
                pass

    thread = threading.Thread(target=_thread, daemon=True)
    thread.start()
    time.sleep(0.5)
