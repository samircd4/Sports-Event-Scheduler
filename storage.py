import csv
import os
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

CSV_FILE = "events_data.csv"

CSV_COLUMNS = [
    "event_id",
    "league",
    "home",
    "away",
    "sport",
    "event_full_name",
    "start_time",
    "status",
    "odds_moneyline_home",
    "odds_moneyline_away",
    "odds_spread_home",
    "odds_spread_away",
    "odds_total_over",
    "odds_total_under",
    "moneyline_consensus_bet_pct_home",
    "moneyline_consensus_bet_pct_away",
    "moneyline_consensus_money_pct_home",
    "moneyline_consensus_money_pct_away",
    "spread_consensus_bet_pct_home",
    "spread_consensus_bet_pct_away",
    "spread_consensus_money_pct_home",
    "spread_consensus_money_pct_away",
    "total_consensus_bet_pct_over",
    "total_consensus_bet_pct_under",
    "total_consensus_money_pct_over",
    "total_consensus_money_pct_under",
    "fetched_at",
]

# Serialize all CSV writes so concurrent threads don't race each other
_csv_lock = threading.Lock()


def save_to_csv(event_meta: dict, event_data: dict = None) -> bool:
    """
    Upsert a single event row in the CSV file.
    - If event_data is provided: always overwrite the existing row with fresh data.
    - If event_data is None (placeholder): only insert if event_id does not already exist in CSV.
    - Creates the file with headers if it doesn't exist yet.

    Args:
        event_meta: dict with keys: event_id, league, home, away, sport,
                    event_full_name, start_time
        event_data: dict returned by get_event_info(), or None for placeholder

    Returns True on success, False on failure.
    """
    row = {
        "event_id":           event_meta.get("event_id"),
        "league":             event_meta.get("league"),
        "home":               event_meta.get("home"),
        "away":               event_meta.get("away"),
        "sport":              event_meta.get("sport"),
        "event_full_name":    event_meta.get("event_full_name"),
        "start_time":         event_meta.get("start_time"),
        "status":             event_meta.get("status"),

        "odds_moneyline_home":  event_data.get("odds_moneyline_home") if event_data else None,
        "odds_moneyline_away":  event_data.get("odds_moneyline_away") if event_data else None,
        "odds_spread_home":     event_data.get("odds_spread_home") if event_data else None,
        "odds_spread_away":     event_data.get("odds_spread_away") if event_data else None,
        "odds_total_over":      event_data.get("odds_total_over") if event_data else None,
        "odds_total_under":     event_data.get("odds_total_under") if event_data else None,

        "moneyline_consensus_bet_pct_home":   event_data.get("moneyline_consensus_bet_pct_home") if event_data else None,
        "moneyline_consensus_bet_pct_away":   event_data.get("moneyline_consensus_bet_pct_away") if event_data else None,
        "moneyline_consensus_money_pct_home": event_data.get("moneyline_consensus_money_pct_home") if event_data else None,
        "moneyline_consensus_money_pct_away": event_data.get("moneyline_consensus_money_pct_away") if event_data else None,

        "spread_consensus_bet_pct_home":   event_data.get("spread_consensus_bet_pct_home") if event_data else None,
        "spread_consensus_bet_pct_away":   event_data.get("spread_consensus_bet_pct_away") if event_data else None,
        "spread_consensus_money_pct_home": event_data.get("spread_consensus_money_pct_home") if event_data else None,
        "spread_consensus_money_pct_away": event_data.get("spread_consensus_money_pct_away") if event_data else None,

        "total_consensus_bet_pct_over":    event_data.get("total_consensus_bet_pct_over") if event_data else None,
        "total_consensus_bet_pct_under":   event_data.get("total_consensus_bet_pct_under") if event_data else None,
        "total_consensus_money_pct_over":  event_data.get("total_consensus_money_pct_over") if event_data else None,
        "total_consensus_money_pct_under": event_data.get("total_consensus_money_pct_under") if event_data else None,

        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if event_data else None,
    }

    event_id = row["event_id"]

    with _csv_lock:   # only one thread writes at a time
        try:
            # ── Read existing rows ────────────────────────────────────────────────
            existing_rows = []
            file_exists = os.path.isfile(CSV_FILE)

            if file_exists:
                with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)

            # ── Check if event_id already exists ──────────────────────────────────
            found_index = -1
            for i, existing_row in enumerate(existing_rows):
                if existing_row.get("event_id") == event_id:
                    found_index = i
                    break

            if found_index != -1:
                # Event already exists in CSV
                if event_data is None:
                    # Do not overwrite with placeholder if it's already in there
                    return True
                else:
                    # Overwrite existing row with the fully fetched event_data
                    existing_rows[found_index] = row
            else:
                # Event is not in CSV, append it
                existing_rows.append(row)

            # ── Write all rows back ───────────────────────────────────────────────
            with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(existing_rows)

            action = "Updated" if (found_index != -1) else "Inserted"
            logger.info(f"{action} CSV row for: {event_meta.get('event_full_name')}")
            return True

        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return False


