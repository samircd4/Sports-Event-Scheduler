import requests
from rich import print
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_today_date(days_offset=0):
    return (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")


def get_event_list():

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,bn;q=0.8",
        "authorization": os.getenv("AUTHORIZATION_KEY"),
        "origin": "https://app.pikkit.com",
        "priority": "u=1, i",
        "referer": "https://app.pikkit.com/",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }

    event_list = []
    current_offset = 0

    while True:
        params = {
            "query_date": get_today_date(),
            "league_offset": str(current_offset),
        }

        response = requests.get(
            "https://prod-website.pikkit.app/events/all", params=params, headers=headers
        )
        raw_data = response.json()  # Equivalent to json.loads(response.text)
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
                    ).astimezone()

                    formatted_time = local_dt.strftime("%b %d, %Y %I:%M %p")
                else:
                    local_dt = None
                    formatted_time = None

                event_data = {}
                event_data["event_id"]      = event_id
                event_data["league"]        = league
                event_data["home"]          = home
                event_data["away"]          = away
                event_data["sport"]         = sport
                event_data["event_full_name"] = event_full_name
                event_data["start_time"]    = formatted_time
                event_data["start_time_dt"] = local_dt   # raw timezone-aware datetime for scheduler
                event_data["status"]        = status

                event_list.append(event_data)

        next_offset = raw_data.get('league_offset')
        if not next_offset or next_offset == 0 or next_offset == current_offset:
            break
            
        current_offset = next_offset


    return event_list


if __name__ == "__main__":
    event_list = get_event_list()
    print(event_list)
