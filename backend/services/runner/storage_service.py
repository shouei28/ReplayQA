"""
Storage Service — upload/retrieve screenshots from Supabase blob storage.
"""

import logging
import os

logger = logging.getLogger(__name__)


def _get_supabase_client():
    """Lazy-initialised Supabase client."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


def upload_screenshot(
    test_execution_id: str,
    step_number: int,
    image_data: bytes,
) -> str:
    """
    Upload a PNG screenshot to Supabase storage.

    Args:
        test_execution_id: UUID of the execution (used as folder name).
        step_number: 1-based step index.
        image_data: Raw PNG bytes.

    Returns:
        Public URL of the uploaded screenshot.
    """
    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    path = f"{test_execution_id}/step_{step_number}.png"

    try:
        client = _get_supabase_client()
        client.storage.from_(bucket).upload(
            path,
            image_data,
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        public_url = client.storage.from_(bucket).get_public_url(path)
        logger.info("Uploaded screenshot %s", path)
        return public_url
    except Exception as exc:
        logger.error("Screenshot upload failed for %s: %s", path, exc)
        return ""


def get_screenshot_url(test_execution_id: str, step_number: int) -> str:
    """Return the public URL for a previously-uploaded screenshot."""
    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    path = f"{test_execution_id}/step_{step_number}.png"
    try:
        client = _get_supabase_client()
        return client.storage.from_(bucket).get_public_url(path)
    except Exception as exc:
        logger.error("Failed to get screenshot URL for %s: %s", path, exc)
        return ""


def delete_test_screenshots(test_execution_id: str, total_steps: int) -> None:
    """Remove all screenshots for a given test execution."""
    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    paths = [
        f"{test_execution_id}/step_{i}.png" for i in range(1, total_steps + 1)
    ]
    try:
        client = _get_supabase_client()
        client.storage.from_(bucket).remove(paths)
        logger.info("Deleted %d screenshots for %s", len(paths), test_execution_id)
    except Exception as exc:
        logger.warning("Failed to delete screenshots for %s: %s", test_execution_id, exc)
