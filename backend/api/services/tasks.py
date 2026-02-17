from celery import shared_task
from playwright.sync_api import sync_playwright
from api.services.session_manager import start_session, end_session


def run_browserbase_session(connect_url, actions):
    """Runs the actual automation steps inside Browserbase"""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(connect_url)
        page = browser.contexts[0].pages[0]

        for action in actions:
            try:
                name = action.get("name")
                args = action.get("args", {})

                if name == "navigate":
                    page.goto(args.get("url"), timeout=30000)
                elif name == "click":
                    page.click(args.get("selector"))
                elif name == "type":
                    page.fill(args.get("selector"), args.get("text"))

                results.append({"step": name, "status": "passed"})
            except Exception as e:
                results.append({"step": name, "status": "failed", "error": str(e)})

        browser.close()
    return results


@shared_task(bind=True, max_retries=10)
def queue_test_run(self, test_actions):
    session_id = None
    lock_token = None

    try:
        # 1. Try to get the browser (Will fail if busy)
        session_data = start_session(user_id="automated_worker")
        session_id = session_data["session_id"]
        lock_token = session_data["lock_token"]

        # 2. Run the tests
        logs = run_browserbase_session(session_data["connect_url"], test_actions)
        return {"status": "completed", "logs": logs}

    except BlockingIOError:  # Locked retry after delay
        raise self.retry(countdown=10)

    except Exception as e:
        return {"status": "failed", "error": str(e)}

    finally:
        if session_id and lock_token:
            end_session(session_id, lock_token)
