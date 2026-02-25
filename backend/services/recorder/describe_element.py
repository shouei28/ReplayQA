"""
Describe element from screenshot: uses Gemini vision to generate a short description
for unlabeled elements (e.g. 'menu icon' instead of 'button element').
"""
import os
from typing import Optional

DEFAULT_DESCRIBE_MODEL = "gemini-2.0-flash"

def _build_describe_prompt(selector: str, action_type: str) -> str:
    """Build the prompt for structured action description with context clues."""
    action_verbs = {
        "click": "Click",
        "dblclick": "Double-click",
        "rightclick": "Right-click",
        "hover": "Hover over",
    }
    verb = action_verbs.get(action_type, "Click")
    return (
        f"You are a tool that helps a recorder agent describe an action done on a page.\n"
        f"A user performed a {action_type} on an element (selector: {selector}). "
        "Look at this screenshot and describe the interaction using this exact structure:\n\n"
        f"Try to follow a template similar to: (action) the (adjective (optional)) (element name/identifier) (element type), (position or other context clues)\n\n"
        "**Fields:**\n"
        f"- action: Use '{verb}' (the verb for this interaction type)\n"
        "- adjective: Adjective to describe the element (e.g. black, grey, curcular) this is optional\n" 
        "- element name/identifier: Short label for the element (e.g. 'search', 'settings', 'hamburger menu', 'close')\n"
        "- element type: Element type (button, link, icon, dropdown, text field, checkbox, SVG icon, etc.)\n"
        "- position: Where it is on the page (e.g. top-right of header, left sidebar, bottom navigation bar) this is optional. Keep in mind the picture is cropped so please describe position relative to other elements in the picture\n\n"
        "**Examples:**\n"
        "- Click the black search button, located at the top-right of the header\n"
        "- Click the gray hamburger menu icon, top-left navigation bar\n"
        "- Hover over the white dropdown trigger, located at the center of the toolbar\n"
        "Output only the single line following the template. No other text.\n"
        f"If the user clicks on a random background space, just return 'Click on a random background space'\n"
    )


def describe_element_from_screenshot(
    screenshot_bytes: bytes,
    selector: str,
    action_type: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    mime_type: str = "image/jpeg",
) -> Optional[str]:
    """
    Call LLM with cropped screenshot to describe the element.

    Returns a structured description: "{action} the {name} {type} – {color}, {position}" or None on error.
    Caller should keep the original fallback description when None is returned.
    """
    print(
        f"[QUALTY DESCRIBE] describe_element triggered: action_type={action_type}, selector={selector[:60]}{'...' if len(selector) > 60 else ''}"
    )
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[QUALTY DESCRIBE] Failed: google-genai not available")
        return None

    api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[QUALTY DESCRIBE] Failed: no API key configured")
        return None

    model = model_name or os.environ.get("GEMINI_DESCRIBE_MODEL", DEFAULT_DESCRIBE_MODEL)
    client = genai.Client(api_key=api_key)
    prompt = _build_describe_prompt(selector, action_type)

    try:
        resp = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        types.Part.from_bytes(data=screenshot_bytes, mime_type=mime_type),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
            ),
        )
    except Exception as e:
        print(f"[QUALTY DESCRIBE] LLM call failed: {e}")
        return None

    text = ""
    if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        text = (resp.candidates[0].content.parts[0].text or "").strip()

    if not text:
        print("[QUALTY DESCRIBE] LLM returned empty response")
        return None

    # Take first line only (LLM may add extra text) and truncate to ~150 chars
    first_line = text.split("\n")[0].strip()
    result = first_line[:150].strip()
    if result:
        print(f"[QUALTY DESCRIBE] Success: '{result}'")
        return result
    print("[QUALTY DESCRIBE] LLM response was empty after trim")
    return None