"""
Storage Service — upload/retrieve screenshots from Supabase blob storage.

Falls back gracefully if the ``supabase`` package is not installed,
SUPABASE_URL / SUPABASE_KEY are not configured, or the bucket is
inaccessible.  After the first failure the module disables itself so it
doesn't spam error logs on every CUA turn.
"""

import logging
import os

logger = logging.getLogger(__name__)

# After the first upload failure we flip this flag so subsequent calls
# return immediately instead of spamming the same error every turn.
_disabled = False


def _get_supabase_client():
    """Lazy-initialised Supabase client."""
    global _disabled
    if _disabled:
        return None

    try:
        from supabase import create_client
    except ImportError:
        logger.warning("supabase package not installed — screenshot storage disabled")
        _disabled = True
        return None

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        logger.warning("SUPABASE_URL / SUPABASE_KEY not set — screenshot storage disabled")
        _disabled = True
        return None
    return create_client(url, key)


def upload_screenshot(
    test_execution_id: str,
    step_number: int,
    image_data: bytes,
) -> str:
    """
    Upload a PNG screenshot to Supabase storage.

    Returns:
        Public URL of the uploaded screenshot, or empty string on failure.
    """
    global _disabled
    if _disabled:
        return ""

    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    path = f"{test_execution_id}/step_{step_number}.png"

    try:
        client = _get_supabase_client()
        if client is None:
            return ""
        client.storage.from_(bucket).upload(
            path,
            image_data,
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        public_url = client.storage.from_(bucket).get_public_url(path)
        logger.info("Uploaded screenshot %s", path)
        return public_url
    except Exception as exc:
        logger.warning(
            "Screenshot upload failed for %s: %s — disabling further uploads this worker",
            path, exc,
        )
        _disabled = True
        return ""


def get_screenshot_url(test_execution_id: str, step_number: int) -> str:
    """Return the public URL for a previously-uploaded screenshot."""
    if _disabled:
        return ""
    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    path = f"{test_execution_id}/step_{step_number}.png"
    try:
        client = _get_supabase_client()
        if client is None:
            return ""
        return client.storage.from_(bucket).get_public_url(path)
    except Exception as exc:
        logger.warning("Failed to get screenshot URL for %s: %s", path, exc)
        return ""


def delete_test_screenshots(test_execution_id: str, total_steps: int) -> None:
    """Remove all screenshots for a given test execution."""
    if _disabled:
        return
    bucket = os.getenv("SUPABASE_BUCKET", "screenshots")
    paths = [
        f"{test_execution_id}/step_{i}.png" for i in range(1, total_steps + 1)
    ]
    try:
        client = _get_supabase_client()
        if client is None:
            return
        client.storage.from_(bucket).remove(paths)
        logger.info("Deleted %d screenshots for %s", len(paths), test_execution_id)
    except Exception as exc:
        logger.warning("Failed to delete screenshots for %s: %s", test_execution_id, exc)
