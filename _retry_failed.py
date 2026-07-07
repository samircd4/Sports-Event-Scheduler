from get_odds import get_event_info
from notifier import send_telegram
from storage import save_to_csv

failed_events = [
    {
        "event_id": "6a483f40e5efe71207bf546b",
        "event_full_name": "Spain vs. Portugal",
        "league": "WORLDCUP",
        "home": "Portugal",
        "away": "Spain",
        "sport": "Soccer",
        "start_time": "Jul 07, 2026 01:00 AM",
    },
    {
        "event_id": "696089b7784778a143730589",
        "event_full_name": "Philadelphia Phillies vs. Kansas City Royals",
        "league": "MLB",
        "home": "Kansas City Royals",
        "away": "Philadelphia Phillies",
        "sport": "Baseball",
        "start_time": "Jul 07, 2026 12:10 AM",
    },
]

for event_meta in failed_events:
    name = event_meta["event_full_name"]
    print(f"Testing: {name}")
    try:
        event_data = get_event_info(event_meta["event_id"])
        print(f"  Odds fetched OK")
        send_telegram(event_meta, event_data)
        save_to_csv(event_meta, event_data)
        print(f"  OK - Sent to Telegram")
    except Exception as e:
        print(f"  FAIL: {e}")
