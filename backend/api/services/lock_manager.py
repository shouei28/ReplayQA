from django.core.cache import cache

LOCK_KEY = "browserbase_global_lock"
LOCK_TIMEOUT = 60 * 60

def acquire_browser_slot(user_id: str) -> bool:
    """
    Tries to acquire the single browser slot.
    Returns True if successful, False if someone else is using it.
    """
    is_free = cache.add(LOCK_KEY, user_id, timeout=LOCK_TIMEOUT)
    return is_free

def release_browser_slot(user_id: str):
    """
    Releases the slot, but only if the requester owns it.
    """
    current_user = cache.get(LOCK_KEY)
    if current_user == user_id:
        cache.delete(LOCK_KEY)

def get_current_user():
    return cache.get(LOCK_KEY)

def force_release():
    """Emergency release if a session gets stuck"""
    cache.delete(LOCK_KEY)