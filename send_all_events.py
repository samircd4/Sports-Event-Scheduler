"""
send_all_events.py — One-shot script to send all today's events to Telegram immediately.
Useful for testing or getting a full snapshot of the day's events.
"""

import time
import logging
from all_events import get_event_list
from get_odds import get_event_info
from notifier import send_telegram
from storage import save_to_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DELAY_BETWEEN_EVENTS = 1  # seconds between sends to avoid Telegram rate limits


def run():
    logger.info("Fetching event list...")
    events = get_event_list()
    logger.info(f"Found {len(events)} event(s). Starting to send...")

    success = 0
    failed = 0

    for i, event_meta in enumerate(events, start=1):
        event_name = event_meta.get("event_full_name", event_meta.get("event_id"))
        logger.info(f"[{i}/{len(events)}] Processing: {event_name}")

        try:
            event_data = get_event_info(event_meta["event_id"])
        except Exception as e:
            logger.error(f"  ✗ Failed to fetch odds: {e}")
            failed += 1
            continue

        ok = send_telegram(event_meta, event_data)
        save_to_csv(event_meta, event_data)

        if ok:
            logger.info(f"  ✓ Sent to Telegram")
            success += 1
        else:
            logger.warning(f"  ✗ Telegram send failed (data still saved to CSV)")
            failed += 1

        if i < len(events):
            time.sleep(DELAY_BETWEEN_EVENTS)

    logger.info(f"\nDone! ✓ {success} sent  ✗ {failed} failed")


if __name__ == "__main__":
    run()
