"""Summarize recorder steps into a short description using Gemini Flash."""
import json
import os
from typing import Any, List, Optional


def steps_to_text(steps: List[Any]) -> str:
    """Build human-readable steps text from steps JSON (for Job.steps field)."""
    lines = []
    for i, s in enumerate(steps or [], 1):
        if not isinstance(s, dict):
            continue
        kind = s.get("kind")
        if kind == "goto":
            u = s.get("url", "")
            lines.append(f"{i}. Navigate to {u}")
        elif kind == "act":
            instr = s.get("instruction", "")
            lines.append(f"{i}. {instr}")
        elif kind == "agent":
            instr = s.get("instruction", "")
            lines.append(f"{i}. {instr}")
        elif kind == "login":
            login_type = s.get("type", "username and password")
            lines.append(f"{i}. login with {login_type}")
        elif kind == "check":
            instr = s.get("instruction", "")
            lines.append(f"{i}. Check: {instr}")
        elif kind == "delay_ms":
            ms = s.get("delay_ms", 0)
            lines.append(f"{i}. Wait {ms}ms")
    return "\n".join(lines) if lines else ""


def summarize_steps(
    steps: List[Any],
    url: str = "",
    expected_behavior: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Use Gemini Flash to produce a short (1–2 sentence) description of the test.

    steps: The steps JSON (list of goto/act/delay_ms objects) stored in the DB.
    url: Start URL of the test (optional).
    expected_behavior: What the user expects to happen (optional).
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    fallback = "Recorded test steps"
    if not api_key:
        return fallback

    model = model_name or os.environ.get("GEMINI_SUMMARIZE_MODEL", "gemini-2.0-flash")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        steps_json = json.dumps(steps, indent=2) if steps else "[]"
        context_parts = []
        if url:
            context_parts.append(f"URL: {url}")
        if expected_behavior and expected_behavior.strip():
            context_parts.append(f"Expected behavior: {expected_behavior.strip()}")
        context = "\n".join(context_parts) if context_parts else ""

        prompt = (
            "Given the following browser automation test definition (JSON steps plus optional context), "
            "write a single short description (1-2 sentences) that summarizes what the test does. "
            "Be concise and descriptive. Output only the description, no preamble. "
            "Ommit things that are not relevant to the test.\n\n"
        )
        if context:
            prompt += context + "\n\n"
        prompt += "Steps (JSON):\n" + steps_json

        resp = client.models.generate_content(model=model, contents=prompt)
        if resp and resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
            text = (resp.candidates[0].content.parts[0].text or "").strip()
            return text if text else fallback
        return fallback
    except Exception as e:
        print(f"[SUMMARIZE] Gemini summarization failed: {e}")
        return fallback
