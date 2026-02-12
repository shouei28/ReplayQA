from celery import shared_task
from api.services.session_manager import start_session, end_session
from api.services.browser import run_browserbase_session

@shared_task(bind=True, max_retries=10)
def queue_test_run(self, test_actions):
    """
    Celery task that waits for the browser slot to be free.
    """
    try:
        # 1. Try to start session
        print("Attempting to acquire browser slot...")
        session_data = start_session(user_id="automated_worker")
        
        # 2. If successful, run the test
        session_id = session_data["session_id"]
        lock_token = session_data["lock_token"]
        
        print(f"Slot acquired! Running session {session_id}")
        
        # Connect to browser and run actions
        results = run_browserbase_session(session_data["connect_url"], test_actions)
        
        # 3. Cleanup
        end_session(session_id, lock_token)
        return results

    except BlockingIOError:
        # 4. If busy, retry in 10 seconds
        print("Slot busy. Queuing retry...")
        raise self.retry(countdown=10)
        
    except Exception as e:
        print(f"Test failed: {e}")
        return {"status": "failed", "error": str(e)}