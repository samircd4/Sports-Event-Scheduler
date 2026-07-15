"""
send_all_events.py — Populate Google Sheet with today's event list.

Fetches all of today's events and inserts them as placeholder rows in the
Google Sheet (no odds data, no Telegram messages).

Use this to pre-fill the sheet at the start of the day.
The scheduler.py will then fill in the odds columns 1 minute before each game.
"""

import logging
from all_events import get_event_list
from storage import save_events_to_csv_batch

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

    ok = save_events_to_csv_batch(events)

    if ok:
        logger.info(f"\nDone! Successfully batch-processed {len(events)} events.")
    else:
        logger.info("\nDone, but batch process encountered errors.")
    logger.info("Odds will be fetched and written by scheduler.py 1 minute before each game.")


if __name__ == "__main__":
    run()
