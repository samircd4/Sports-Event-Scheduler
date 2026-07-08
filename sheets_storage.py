"""
sheets_storage.py — Google Sheets upsert storage backend.

Replaces the CSV storage in storage.py.
Public API is identical: save_to_sheet(event_meta, event_data)

Auth: Google Service Account (headless — works on VPS/Docker).
Required .env variables:
    GOOGLE_SHEET_ID               — the long ID from the Sheet URL
    GOOGLE_SHEET_TAB              — worksheet/tab name (default: Sheet1)
    GOOGLE_SERVICE_ACCOUNT_JSON   — path to the service account JSON key file

The sheet is expected to already have a header row in Row 1.
"""

import os
import logging
import threading
from datetime import datetime

import gspread
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
_SHEET_ID   = os.getenv("GOOGLE_SHEET_ID", "").strip()
_SHEET_TAB  = os.getenv("GOOGLE_SHEET_TAB", "Sheet1").strip()
_SA_JSON    = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json").strip()

# Column order must match the sheet header row exactly
SHEET_COLUMNS = [
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

# ── Thread safety ─────────────────────────────────────────────────────────────
_sheet_lock = threading.Lock()

# ── Lazy worksheet handle — opened once, reused across all calls ──────────────
_ws: gspread.Worksheet | None = None


def _get_worksheet() -> gspread.Worksheet:
    """Return a cached worksheet handle, opening it on first call."""
    global _ws
    if _ws is not None:
        return _ws

    if not _SHEET_ID:
        raise RuntimeError(
            "GOOGLE_SHEET_ID is not set in .env. "
            "Add it before running the scheduler."
        )
    if not os.path.isfile(_SA_JSON):
        raise FileNotFoundError(
            f"Service account JSON not found at '{_SA_JSON}'. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON in .env to the correct path."
        )

    gc = gspread.service_account(filename=_SA_JSON)
    _ws = gc.open_by_key(_SHEET_ID).worksheet(_SHEET_TAB)
    logger.info(f"Connected to Google Sheet '{_SHEET_TAB}' (id={_SHEET_ID})")
    return _ws


def _row_values(row: dict) -> list:
    """Convert a row dict to an ordered list matching SHEET_COLUMNS."""
    return [row.get(col, "") for col in SHEET_COLUMNS]


def save_to_sheet(event_meta: dict, event_data: dict | None = None) -> bool:
    """
    Upsert a single event row in the Google Sheet.

    - event_data=None  → placeholder insert: only adds the row if event_id is
                         not already in the sheet.
    - event_data given → full upsert: updates the existing row in-place, or
                         appends a new row if not found.

    Returns True on success, False on failure.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "event_id":        event_meta.get("event_id"),
        "league":          event_meta.get("league"),
        "home":            event_meta.get("home"),
        "away":            event_meta.get("away"),
        "sport":           event_meta.get("sport"),
        "event_full_name": event_meta.get("event_full_name"),
        "start_time":      event_meta.get("start_time"),
        "status":          event_meta.get("status"),

        "odds_moneyline_home": event_data.get("odds_moneyline_home") if event_data else "",
        "odds_moneyline_away": event_data.get("odds_moneyline_away") if event_data else "",
        "odds_spread_home":    event_data.get("odds_spread_home")    if event_data else "",
        "odds_spread_away":    event_data.get("odds_spread_away")    if event_data else "",
        "odds_total_over":     event_data.get("odds_total_over")     if event_data else "",
        "odds_total_under":    event_data.get("odds_total_under")    if event_data else "",

        "moneyline_consensus_bet_pct_home":   event_data.get("moneyline_consensus_bet_pct_home")   if event_data else "",
        "moneyline_consensus_bet_pct_away":   event_data.get("moneyline_consensus_bet_pct_away")   if event_data else "",
        "moneyline_consensus_money_pct_home": event_data.get("moneyline_consensus_money_pct_home") if event_data else "",
        "moneyline_consensus_money_pct_away": event_data.get("moneyline_consensus_money_pct_away") if event_data else "",

        "spread_consensus_bet_pct_home":   event_data.get("spread_consensus_bet_pct_home")   if event_data else "",
        "spread_consensus_bet_pct_away":   event_data.get("spread_consensus_bet_pct_away")   if event_data else "",
        "spread_consensus_money_pct_home": event_data.get("spread_consensus_money_pct_home") if event_data else "",
        "spread_consensus_money_pct_away": event_data.get("spread_consensus_money_pct_away") if event_data else "",

        "total_consensus_bet_pct_over":    event_data.get("total_consensus_bet_pct_over")    if event_data else "",
        "total_consensus_bet_pct_under":   event_data.get("total_consensus_bet_pct_under")   if event_data else "",
        "total_consensus_money_pct_over":  event_data.get("total_consensus_money_pct_over")  if event_data else "",
        "total_consensus_money_pct_under": event_data.get("total_consensus_money_pct_under") if event_data else "",

        "fetched_at": now_str if event_data else "",
    }

    event_id   = row["event_id"]
    event_name = event_meta.get("event_full_name", event_id)

    with _sheet_lock:
        try:
            ws = _get_worksheet()

            # ── Read all existing event_ids (column A, skip header row 1) ─────
            # get_col returns a flat list; index 0 = header, 1+ = data rows
            col_a = ws.col_values(1)          # ["event_id", "abc123", "def456", ...]
            event_ids = col_a[1:]             # skip header

            values = _row_values(row)

            if event_id in event_ids:
                # ── Row exists ────────────────────────────────────────────────
                if event_data is None:
                    # Placeholder: don't overwrite an existing row
                    logger.debug(f"Skipped placeholder (already in sheet): {event_name}")
                    return True

                # Full update: row number in the sheet = list index + 2 (1-based + header)
                sheet_row_num = event_ids.index(event_id) + 2
                # Build A1 notation for the full row range
                end_col_letter = _col_letter(len(SHEET_COLUMNS))
                cell_range = f"A{sheet_row_num}:{end_col_letter}{sheet_row_num}"
                ws.update(cell_range, [values], value_input_option="USER_ENTERED")
                logger.info(f"Updated sheet row for: {event_name}")
            else:
                # ── New row — append ──────────────────────────────────────────
                ws.append_row(values, value_input_option="USER_ENTERED")
                logger.info(f"Inserted sheet row for: {event_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to write to Google Sheet for '{event_name}': {e}")
            return False


def _col_letter(n: int) -> str:
    """Convert a 1-based column index to an A1 column letter (e.g. 27 → 'AA')."""
    result = ""
    while n:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result
