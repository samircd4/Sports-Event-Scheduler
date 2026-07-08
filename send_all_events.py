"""
send_all_events.py — Populate Google Sheet with today's event list.

Fetches all of today's events and inserts them as placeholder rows in the
Google Sheet (no odds data, no Telegram messages).

Use this to pre-fill the sheet at the start of the day.
The scheduler.py will then fill in the odds columns 1 minute before each game.
"""

import logging
from all_events import get_event_list
from storage import save_to_csv   # shim → sheets_storage.save_to_sheet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    logger.info("Fetching event list...")
    events = get_event_list()
    logger.info(f"Found {len(events)} event(s). Writing placeholder rows to Google Sheet...")

    inserted = 0
    skipped  = 0
    failed   = 0

    for i, event_meta in enumerate(events, start=1):
        event_name = event_meta.get("event_full_name", event_meta.get("event_id"))
        logger.info(f"[{i}/{len(events)}] {event_name}")

        # event_data=None → placeholder insert (skips if row already exists)
        ok = save_to_csv(event_meta, None)

        if ok:
            inserted += 1
        else:
            failed += 1

    logger.info(f"\nDone!  inserted/skipped: {inserted}  failed: {failed}")
    logger.info("Odds will be fetched and written by scheduler.py 1 minute before each game.")


if __name__ == "__main__":
    run()
