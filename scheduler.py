"""
scheduler.py — Main runner for the event scheduler.

Behaviour:
- On startup: fetches today's event list
- Every 60 minutes: re-fetches the event list and merges any new events
- Every 10 seconds: checks if any event's trigger time (start - 1 min) has been reached
- When triggered: fetches odds, sends Telegram notification, saves to CSV
- Each fetch runs in its own thread so simultaneous events don't block each other
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from all_events import get_event_list
from get_odds import get_event_info
from notifier import send_telegram
from storage import save_to_csv

# ── Configuration ────────────────────────────────────────────────────────────
TRIGGER_BEFORE_SECONDS = 60   # fetch 1 minute before start
REFRESH_INTERVAL_SECONDS = 3600  # refresh event list every hour
TICK_INTERVAL_SECONDS = 10    # how often to check triggers
MAX_RETRY_ATTEMPTS = 2        # retries for get_event_info on failure
RETRY_DELAY_SECONDS = 5       # wait between retries

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %Z",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────
# { event_id: { ...event_meta, "status": "pending" | "triggered" | "skipped" } }
scheduled_events: dict = {}
state_lock = threading.Lock()
active_threads: list = []   # track running fetch threads for graceful shutdown
active_threads_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# Event list refresh
# ─────────────────────────────────────────────────────────────────────────────

def refresh_event_list():
    """Fetch the latest event list and merge new events into scheduled_events."""
    logger.info("Refreshing event list...")
    try:
        events = get_event_list()
    except Exception as e:
        logger.error(f"Failed to fetch event list: {e}")
        return

    added = 0
    with state_lock:
        for event in events:
            event_id = event.get("event_id")
            if not event_id:
                continue
            if event_id not in scheduled_events:
                scheduled_events[event_id] = {**event, "status": "pending"}
                added += 1

    logger.info(f"Event list refreshed — {added} new event(s) added. "
                f"Total tracked: {len(scheduled_events)}")

    # Store all events to CSV as placeholders immediately if they don't already exist
    for event in events:
        save_to_csv(event, None)




def schedule_periodic_refresh():
    """Re-schedule the event list refresh every REFRESH_INTERVAL_SECONDS."""
    refresh_event_list()
    timer = threading.Timer(REFRESH_INTERVAL_SECONDS, schedule_periodic_refresh)
    timer.daemon = True
    timer.start()


# ─────────────────────────────────────────────────────────────────────────────
# Event fetch + notify + save
# ─────────────────────────────────────────────────────────────────────────────

def fetch_and_notify(event_meta: dict):
    """
    Fetch odds for one event, send Telegram notification, save to CSV.
    Retries up to MAX_RETRY_ATTEMPTS times on API failure.
    """
    t = threading.current_thread()
    with active_threads_lock:
        active_threads.append(t)

    try:
        event_id   = event_meta["event_id"]
        event_name = event_meta.get("event_full_name", event_id)

        logger.info(f"Fetching odds for: {event_name}")

        event_data = None
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 2):
            try:
                event_data = get_event_info(event_id)
                break
            except Exception as e:
                if attempt <= MAX_RETRY_ATTEMPTS:
                    logger.warning(f"Attempt {attempt} failed for {event_name}: {e}. "
                                   f"Retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"All {MAX_RETRY_ATTEMPTS + 1} attempts failed for {event_name}: {e}")

        if event_data is None:
            logger.error(f"Skipping notification/CSV for {event_name} — no data.")
            return

        # Send Telegram (non-fatal if it fails)
        send_telegram(event_meta, event_data)

        # Save to CSV (non-fatal if it fails)
        save_to_csv(event_meta, event_data)

    finally:
        with active_threads_lock:
            try:
                active_threads.remove(t)
            except ValueError:
                pass



# ─────────────────────────────────────────────────────────────────────────────
# Main tick loop
# ─────────────────────────────────────────────────────────────────────────────

def run_tick():
    """Check all pending events and fire any whose trigger time has arrived."""
    now = datetime.now(tz=timezone.utc).astimezone()

    to_trigger = []
    to_skip    = []

    with state_lock:
        for event_id, event in scheduled_events.items():
            if event["status"] != "pending":
                continue

            start_dt = event.get("start_time_dt")
            if start_dt is None:
                continue

            trigger_dt = start_dt - timedelta(seconds=TRIGGER_BEFORE_SECONDS)

            if now >= trigger_dt:
                if now < start_dt:
                    # ✅ Within the trigger window — fire it
                    to_trigger.append(event_id)
                else:
                    # ⚠️  Already past start time — missed window
                    to_skip.append(event_id)

        for event_id in to_trigger:
            scheduled_events[event_id]["status"] = "triggered"
        for event_id in to_skip:
            scheduled_events[event_id]["status"] = "skipped"

    # Fire triggered events each in their own thread
    for event_id in to_trigger:
        event_meta = scheduled_events[event_id]
        tz = event_meta.get('timezone', '')
        logger.info(f"Triggering: {event_meta.get('event_full_name')} "
                    f"(starts: {event_meta.get('start_time')} {tz})")
        t = threading.Thread(target=fetch_and_notify, args=(event_meta,), daemon=True)
        t.start()

    for event_id in to_skip:
        event_meta = scheduled_events[event_id]
        tz = event_meta.get('timezone', '')
        logger.warning(f"Missed window for: {event_meta.get('event_full_name')} "
                       f"(started: {event_meta.get('start_time')} {tz})")



# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("  Event Scheduler started")
    logger.info(f"  Trigger: {TRIGGER_BEFORE_SECONDS}s before each event")
    logger.info(f"  Refresh interval: {REFRESH_INTERVAL_SECONDS // 60} minutes")
    logger.info("=" * 60)

    # Initial fetch + start periodic refresh timer
    schedule_periodic_refresh()

    # Main tick loop
    try:
        while True:
            run_tick()
            time.sleep(TICK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Scheduler stopping — waiting for active fetches to finish...")
        # Wait up to 30s for any in-flight fetch threads to complete
        with active_threads_lock:
            threads_to_wait = list(active_threads)
        for t in threads_to_wait:
            t.join(timeout=30)
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
