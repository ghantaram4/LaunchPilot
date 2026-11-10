import threading

from .storage import Store


def start_janitor(root, interval=300):
    """Enforce retention while the app is running, including while no browser is connected."""
    stopped = threading.Event()
    health = {"errors": []}
    def loop():
        while not stopped.wait(interval):
            try:
                health.update(Store(root).cleanup())
            except Exception:
                health["errors"] = ["Background retention cleanup failed. Run the cleanup command and check local storage."]
    thread = threading.Thread(target=loop, name="launchpilot-retention", daemon=True)
    thread.start()
    return stopped, health
