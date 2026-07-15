from rich import print
import os
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from http_client import session
from notifier import send_alert

load_dotenv()

logger = logging.getLogger(__name__)

# Read the desired display timezone from .env  (e.g. "America/Denver" for MDT)
_TZ = ZoneInfo(os.getenv("SERVER_TIMEZONE", "America/Denver"))


def get_today_date(days_offset=0):
    return (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")


def get_event_list():

    event_list = []
    current_offset = 0

    while True:
        params = {
            "query_date": get_today_date(),
            "league_offset": str(current_offset),
        }

        response = session.get(
            "https://prod-website.pikkit.app/events/all", params=params
        )
        raw_data = response.json()  # Equivalent to json.loads(response.text)

        # Guard: API returned Forbidden — auth key is missing or expired
        if raw_data.get("message") == "Forbidden":
            alert_msg = "⚠️ <b>Scheduler Alert</b>\nPlease provide the auth key"
            logger.error("API returned Forbidden — sending Telegram alert")
            send_alert(alert_msg)
            raise RuntimeError("API Forbidden: auth key required")

        data = raw_data.get("leagues", [])
        
        for leagues_data in data:
            for event in leagues_data[1:]:
                event_id = event.get("value", {}).get("_id")
                league = (
                    event.get("value", {})
                    .get("event_info", {})
                    .get("league", {})
                    .get("short")
                )
                home = (
                    event.get("value", {}).get("event_info", {}).get("home", {}).get("full")
                )
                away = (
                    event.get("value", {}).get("event_info", {}).get("away", {}).get("full")
                )
                sport = (
                    event.get("value", {})
                    .get("event_info", {})
                    .get("sport", {})
                    .get("name")
                )
                event_full_name = (
                    event.get("value", {}).get("event_info", {}).get("full_name")
                )
                start_time = event.get("value", {}).get("start_time")
                status = event.get("value", {}).get("status")

                if start_time:
                    local_dt = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    ).astimezone(_TZ)

                    formatted_time = local_dt.strftime("%b %d, %Y %I:%M %p")
                    timezone_name  = local_dt.strftime("%Z")  # e.g. "MDT", "UTC"
                else:
                    local_dt       = None
                    formatted_time = None
                    timezone_name  = None

                event_data = {}
                event_data["event_id"]        = event_id
                event_data["league"]          = league
                event_data["home"]            = home
                event_data["away"]            = away
                event_data["sport"]           = sport
                event_data["event_full_name"] = event_full_name
                event_data["start_time"]      = formatted_time
                event_data["timezone"]        = timezone_name
                event_data["start_time_dt"]   = local_dt
                event_data["status"]          = status

                event_list.append(event_data)

        next_offset = raw_data.get('league_offset')
        if not next_offset or next_offset == 0 or next_offset == current_offset:
            break
            
        current_offset = next_offset


    return event_list


if __name__ == "__main__":
    event_list = get_event_list()
    print(event_list)
