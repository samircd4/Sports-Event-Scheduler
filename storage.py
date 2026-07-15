"""
storage.py — Public save interface (shim).

All writes now go to Google Sheets via sheets_storage.py.
The function name save_to_csv is kept for backwards compatibility so that
scheduler.py and send_all_events.py require zero changes.
"""

from sheets_storage import save_to_sheet as save_to_csv  # noqa: F401
from sheets_storage import save_events_to_sheet as save_events_to_csv_batch  # noqa: F401

