"""
Browserbase Slot Manager - Manages concurrent browser session limits and queues requests.

Handles:
- Rate limiting (429 errors) with retry logic
- Queue management when all slots are occupied
- Automatic slot release when sessions complete
"""

import os
import time
import threading
from typing import Optional, Dict, Any
from collections import deque
from browserbase import Browserbase


class BrowserSlotManager:
    """
    Thread-safe manager for Browserbase concurrent session limits.
    
    Features:
    - Tracks available browser slots
    - Queues requests when slots are full
    - Handles 429 rate limit errors with retry
    - Automatically processes queue when slots free up
    """
    
    _instance: Optional['BrowserSlotManager'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_concurrent: int = 1):
        """
        Initialize the slot manager.
        
        Args:
            max_concurrent: Maximum number of concurrent browser sessions allowed
        """
        self.max_concurrent = max_concurrent
        self.available_slots = max_concurrent
        self.queue = deque()
        self.slot_lock = threading.Lock()
        self.condition = threading.Condition(self.slot_lock)
        self.active_sessions = 0
        self._bb: Optional[Browserbase] = None
        
    @classmethod
    def get_instance(cls) -> 'BrowserSlotManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    max_concurrent = int(os.environ.get("BROWSERBASE_MAX_CONCURRENT", "1"))
                    cls._instance = cls(max_concurrent=max_concurrent)
        return cls._instance
    
    def _get_browserbase(self) -> Browserbase:
        """Lazy initialization of Browserbase client."""
        if self._bb is None:
            api_key = os.environ.get("BROWSERBASE_API_KEY")
            if not api_key:
                raise RuntimeError("BROWSERBASE_API_KEY environment variable not set")
            self._bb = Browserbase(api_key=api_key)
        return self._bb
    
    def acquire_slot(self, device: str, browser: str) -> None:
        """
        Acquire a browser slot. Blocks until a slot is available.
        
        Args:
            device: Device type (for logging)
            browser: Browser type (for logging)
        """
        with self.condition:
            # Wait until a slot is available
            while self.available_slots <= 0:
                print(f"[SLOT MANAGER] {device}/{browser}: Waiting for available slot (queue position: {len(self.queue) + 1})")
                self.queue.append((device, browser))
                self.condition.wait()
                # Remove from queue if we were queued
                if self.queue and self.queue[0] == (device, browser):
                    self.queue.popleft()
            
            # Acquire slot
            self.available_slots -= 1
            self.active_sessions += 1
            print(f"[SLOT MANAGER] {device}/{browser}: Acquired slot ({self.active_sessions}/{self.max_concurrent} active)")
    
    def release_slot(self, device: str, browser: str) -> None:
        """
        Release a browser slot and notify waiting threads.
        
        Args:
            device: Device type (for logging)
            browser: Browser type (for logging)
        """
        with self.condition:
            self.available_slots += 1
            self.active_sessions -= 1
            print(f"[SLOT MANAGER] {device}/{browser}: Released slot ({self.active_sessions}/{self.max_concurrent} active, {len(self.queue)} queued)")
            # Notify waiting threads
            self.condition.notify()
    
    def create_session_with_retry(
        self,
        project_id: str,
        browser_settings: Dict[str, Any],
        device: str,
        browser: str,
        max_retries: int = 3
    ) -> Any:
        """
        Create a Browserbase session with automatic retry on 429 errors.
        
        Args:
            project_id: Browserbase project ID
            browser_settings: Browser settings dict
            device: Device type (for logging)
            browser: Browser type (for logging)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Browserbase session object
            
        Raises:
            Exception: If session creation fails after all retries
        """
        bb = self._get_browserbase()
        
        for attempt in range(max_retries):
            try:
                session = bb.sessions.create(
                    project_id=project_id,
                    browser_settings=browser_settings
                )
                print(f"[SLOT MANAGER] {device}/{browser}: Session created successfully (attempt {attempt + 1})")
                return session
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a 429 rate limit error
                if "429" in error_str or "Too Many Requests" in error_str or "rate limit" in error_str.lower():
                    # Try to extract retry-after from error or use exponential backoff
                    retry_after = self._extract_retry_after(e) or (2 ** attempt)
                    
                    if attempt < max_retries - 1:
                        print(f"[SLOT MANAGER] {device}/{browser}: Rate limited (429), waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} attempts: {error_str}")
                else:
                    # Non-rate-limit error, raise immediately
                    raise
        
        raise Exception(f"Failed to create session after {max_retries} attempts")
    
    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """
        Extract retry-after value from error response.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Retry-after seconds, or None if not found
        """
        # Try to extract from error message/response
        error_str = str(error)
        
        # Look for retry-after in error message
        import re
        match = re.search(r'retry[_-]after[:\s]+(\d+)', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Check if error has response attribute (HTTP response)
        if hasattr(error, 'response'):
            response = error.response
            if hasattr(response, 'headers'):
                retry_after = response.headers.get('retry-after')
                if retry_after:
                    try:
                        return float(retry_after)
                    except ValueError:
                        pass
        
        return None


# Global singleton instance
_slot_manager: Optional[BrowserSlotManager] = None


def get_slot_manager() -> BrowserSlotManager:
    """Get the global BrowserSlotManager instance."""
    global _slot_manager
    if _slot_manager is None:
        _slot_manager = BrowserSlotManager.get_instance()
    return _slot_manager

