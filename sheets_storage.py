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
    "result_added",
    "event_handle",
    "odds_moneyline_home",
    "odds_moneyline_away",
    "odds_spread_home",
    "odds_spread_away",
    "odds_total_over",
    "odds_total_under",
    "moneyline_consensus_bet_pct_home",
    "result_moneyline_home",
    "moneyline_consensus_bet_pct_away",
    "result_moneyline_away",
    "moneyline_consensus_money_pct_home",
    "moneyline_consensus_money_pct_away",
    "spread_consensus_bet_pct_home",
    "result_spread_home",
    "spread_consensus_bet_pct_away",
    "result_spread_away",
    "spread_consensus_money_pct_home",
    "spread_consensus_money_pct_away",
    "total_consensus_bet_pct_over",
    "result_total_over",
    "total_consensus_bet_pct_under",
    "result_total_under",
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

        "event_handle": event_data.get("event_handle") if event_data else "",

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

        # Result columns — left empty on initial insert / pre-game update
        "result_added":         "FALSE",
        "result_moneyline_home": "",
        "result_moneyline_away": "",
        "result_spread_home":    "",
        "result_spread_away":    "",
        "result_total_over":     "",
        "result_total_under":    "",
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
                    # Placeholder refresh: update status + ensure result_added is never empty
                    sheet_row_num = event_ids.index(event_id) + 2
                    all_rows = ws.get_all_values()
                    header = all_rows[0]
                    existing_row = all_rows[sheet_row_num - 1]

                    updates = []

                    # Always sync the latest status from the API
                    if "status" in header:
                        status_col = header.index("status") + 1
                        updates.append({
                            "range": f"{_col_letter(status_col)}{sheet_row_num}",
                            "values": [[row.get("status", "")]],
                        })

                    # Backfill result_added = FALSE if the cell is empty
                    if "result_added" in header:
                        ra_col = header.index("result_added") + 1
                        existing_ra = existing_row[ra_col - 1] if (ra_col - 1) < len(existing_row) else ""
                        if existing_ra.strip() == "":
                            updates.append({
                                "range": f"{_col_letter(ra_col)}{sheet_row_num}",
                                "values": [["FALSE"]],
                            })

                    if updates:
                        ws.batch_update(updates, value_input_option="USER_ENTERED")

                    logger.debug(f"Refreshed status for existing event: {event_name}")
                    return True

                # Full update: row number in the sheet = list index + 2 (1-based + header)
                sheet_row_num = event_ids.index(event_id) + 2

                # Guard: if results are already saved, preserve the result columns
                # to avoid overwriting them when the pre-game row is re-written.
                all_rows = ws.get_all_values()          # [[header...], [row...], ...]
                existing_row = all_rows[sheet_row_num - 1]   # 0-indexed
                header = all_rows[0]
                result_added_idx = header.index("result_added") if "result_added" in header else None
                if result_added_idx is not None:
                    existing_result_added = existing_row[result_added_idx] if result_added_idx < len(existing_row) else ""
                    if str(existing_result_added).upper() == "TRUE":
                        # Restore result columns into our values so we don't clobber them
                        result_cols = [
                            "result_added", "result_moneyline_home", "result_moneyline_away",
                            "result_spread_home", "result_spread_away",
                            "result_total_over", "result_total_under",
                        ]
                        for col_name in result_cols:
                            if col_name in header:
                                col_idx = header.index(col_name)
                                if col_idx < len(existing_row):
                                    values[col_idx] = existing_row[col_idx]

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


def save_events_to_sheet(events: list[dict]) -> bool:
    """
    Save a batch of events to Google Sheet.
    Reads the sheet once and does batch append/update to save API quota.
    """
    if not events:
        return True

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _sheet_lock:
        try:
            ws = _get_worksheet()
            all_rows = ws.get_all_values()
            
            header = all_rows[0] if all_rows else SHEET_COLUMNS
            
            event_id_to_row_idx = {}
            if all_rows:
                try:
                    event_id_col_idx = header.index("event_id")
                    for idx, r in enumerate(all_rows[1:], start=1):
                        if idx < len(all_rows) and event_id_col_idx < len(r):
                            eid = r[event_id_col_idx].strip()
                            if eid:
                                event_id_to_row_idx[eid] = idx
                except ValueError:
                    logger.error("save_events_to_sheet: event_id column missing from sheet header")
                    return False
            
            new_rows = []
            updates = []
            
            for event_meta in events:
                event_id = event_meta.get("event_id")
                if not event_id:
                    continue
                
                # Convert event_meta to a row dict for insertion
                row = {
                    "event_id":        event_meta.get("event_id"),
                    "league":          event_meta.get("league"),
                    "home":            event_meta.get("home"),
                    "away":            event_meta.get("away"),
                    "sport":           event_meta.get("sport"),
                    "event_full_name": event_meta.get("event_full_name"),
                    "start_time":      event_meta.get("start_time"),
                    "status":          event_meta.get("status"),
                    "result_added":    "FALSE",
                }
                
                if event_id in event_id_to_row_idx:
                    row_idx = event_id_to_row_idx[event_id]
                    existing_row = all_rows[row_idx]
                    sheet_row_num = row_idx + 1  # 1-based for sheet row number
                    
                    # 1. Update status if changed
                    if "status" in header:
                        status_col_idx = header.index("status")
                        new_status = event_meta.get("status", "")
                        existing_status = existing_row[status_col_idx] if status_col_idx < len(existing_row) else ""
                        if new_status and new_status != existing_status:
                            col_letter = _col_letter(status_col_idx + 1)
                            updates.append({
                                "range": f"{col_letter}{sheet_row_num}",
                                "values": [[new_status]],
                            })
                    
                    # 2. Ensure result_added is FALSE if empty
                    if "result_added" in header:
                        ra_col_idx = header.index("result_added")
                        existing_ra = existing_row[ra_col_idx] if ra_col_idx < len(existing_row) else ""
                        if existing_ra.strip() == "":
                            col_letter = _col_letter(ra_col_idx + 1)
                            updates.append({
                                "range": f"{col_letter}{sheet_row_num}",
                                "values": [["FALSE"]],
                            })
                else:
                    # New event placeholder
                    new_rows.append(_row_values(row))
            
            if new_rows:
                ws.append_rows(new_rows, value_input_option="USER_ENTERED")
                logger.info(f"Batch inserted {len(new_rows)} new row(s) to Google Sheet")
            
            if updates:
                ws.batch_update(updates, value_input_option="USER_ENTERED")
                logger.info(f"Batch updated {len(updates)} status/result_added field(s) in Google Sheet")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to batch save events to Google Sheet: {e}")
            return False


def get_events_needing_results() -> list[str]:
    """
    Return a list of event_ids that are:
      - status == 'closed'  (event has finished)
      - result_added != 'TRUE'  (results not yet written)

    Reads the sheet directly so it works across scheduler restarts.
    Returns an empty list on any error.
    """
    with _sheet_lock:
        try:
            ws = _get_worksheet()
            all_rows = ws.get_all_values()   # [[header...], [row...], ...]
            if len(all_rows) < 2:
                return []

            header = all_rows[0]
            try:
                event_id_idx    = header.index("event_id")
                status_idx      = header.index("status")
                result_added_idx = header.index("result_added")
            except ValueError as e:
                logger.error(f"get_events_needing_results: missing column in sheet header: {e}")
                return []

            event_ids = []
            for row in all_rows[1:]:
                if len(row) <= max(event_id_idx, status_idx, result_added_idx):
                    continue
                status       = row[status_idx].strip().lower()
                result_added = row[result_added_idx].strip().upper()
                if status == "closed" and result_added != "TRUE":
                    eid = row[event_id_idx].strip()
                    if eid:
                        event_ids.append(eid)

            logger.debug(f"Events needing results: {len(event_ids)}")
            return event_ids

        except Exception as e:
            logger.error(f"Failed to read events needing results from sheet: {e}")
            return []


def save_results_to_sheet(event_id: str, result_data: dict) -> bool:
    """
    Update only the result columns for an existing event row.

    result_data keys expected (all optional but at least one must be non-None):
        result_moneyline_home, result_moneyline_away,
        result_spread_home,    result_spread_away,
        result_total_over,     result_total_under

    Sets result_added = TRUE on success.
    Returns True on success, False on failure.
    """
    result_cols = [
        "result_moneyline_home",
        "result_moneyline_away",
        "result_spread_home",
        "result_spread_away",
        "result_total_over",
        "result_total_under",
    ]

    with _sheet_lock:
        try:
            ws = _get_worksheet()
            all_rows = ws.get_all_values()
            if len(all_rows) < 2:
                logger.warning(f"save_results_to_sheet: sheet is empty, cannot find {event_id}")
                return False

            header = all_rows[0]
            event_ids_in_sheet = [r[0] if r else "" for r in all_rows[1:]]

            if event_id not in event_ids_in_sheet:
                logger.warning(f"save_results_to_sheet: event_id not found in sheet: {event_id}")
                return False

            sheet_row_num = event_ids_in_sheet.index(event_id) + 2  # 1-based + header

            # Build a mapping of col_name -> col_index (1-based for gspread)
            try:
                result_added_col = header.index("result_added") + 1
            except ValueError:
                logger.error("save_results_to_sheet: 'result_added' column missing from sheet header")
                return False

            # Update each result column individually using batch_update for efficiency
            updates = []
            for col_name in result_cols:
                if col_name not in header:
                    continue
                col_idx = header.index(col_name) + 1   # 1-based
                value   = result_data.get(col_name) or ""
                col_letter = _col_letter(col_idx)
                updates.append({
                    "range": f"{col_letter}{sheet_row_num}",
                    "values": [[value]],
                })

            # Mark result_added = TRUE
            updates.append({
                "range": f"{_col_letter(result_added_col)}{sheet_row_num}",
                "values": [["TRUE"]],
            })

            if updates:
                ws.batch_update(updates, value_input_option="USER_ENTERED")
                logger.info(f"Results saved for event_id={event_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to save results for event_id={event_id}: {e}")
            return False



def _col_letter(n: int) -> str:
    """Convert a 1-based column index to an A1 column letter (e.g. 27 → 'AA')."""
    result = ""
    while n:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result
