import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logger = logging.getLogger(__name__)


def _fmt_odds(value):
    """Format an odds value, returning 'N/A' if None."""
    if value is None:
        return "N/A"
    return str(value)


def _fmt_pct(value):
    """Format a percentage value, returning 'N/A' if None."""
    if value is None:
        return "N/A"
    return f"{value}%"


def build_message(event_meta: dict, event_data: dict) -> str:
    """
    Build a formatted Telegram message from event metadata and odds data.

    Args:
        event_meta: dict with keys: league, home, away, sport, event_full_name, start_time
        event_data: dict returned by get_event_info()
    """
    league         = event_meta.get("league", "")
    sport          = event_meta.get("sport", "")
    event_full     = event_meta.get("event_full_name", "")
    start_time     = event_meta.get("start_time", "")
    home           = event_meta.get("home", "Home")
    away           = event_meta.get("away", "Away")

    ml_home        = _fmt_odds(event_data.get("odds_moneyline_home"))
    ml_away        = _fmt_odds(event_data.get("odds_moneyline_away"))
    sp_home_odds   = _fmt_odds(event_data.get("odds_spread_home"))
    sp_away_odds   = _fmt_odds(event_data.get("odds_spread_away"))
    tot_over       = _fmt_odds(event_data.get("odds_total_over"))
    tot_under      = _fmt_odds(event_data.get("odds_total_under"))

    ml_bet_home    = _fmt_pct(event_data.get("moneyline_consensus_bet_pct_home"))
    ml_bet_away    = _fmt_pct(event_data.get("moneyline_consensus_bet_pct_away"))
    ml_money_home  = _fmt_pct(event_data.get("moneyline_consensus_money_pct_home"))
    ml_money_away  = _fmt_pct(event_data.get("moneyline_consensus_money_pct_away"))

    sp_bet_home    = _fmt_pct(event_data.get("spread_consensus_bet_pct_home"))
    sp_bet_away    = _fmt_pct(event_data.get("spread_consensus_bet_pct_away"))
    sp_money_home  = _fmt_pct(event_data.get("spread_consensus_money_pct_home"))
    sp_money_away  = _fmt_pct(event_data.get("spread_consensus_money_pct_away"))

    tot_bet_over   = _fmt_pct(event_data.get("total_consensus_bet_pct_over"))
    tot_bet_under  = _fmt_pct(event_data.get("total_consensus_bet_pct_under"))
    tot_money_over = _fmt_pct(event_data.get("total_consensus_money_pct_over"))
    tot_money_under= _fmt_pct(event_data.get("total_consensus_money_pct_under"))

    sport_emoji = {
        "Soccer": "⚽",
        "Baseball": "⚾",
        "Basketball": "🏀",
        "Football": "🏈",
        "Hockey": "🏒",
    }.get(sport, "🏆")

    message = (
        f"{sport_emoji} <b>[{league}] {event_full}</b>\n"
        f"⏰ Starts: {start_time}\n"
        f"\n"
        f"📊 <b>ODDS (Full Game)</b>\n"
        f"  Moneyline:  {home} {ml_home}  |  {away} {ml_away}\n"
        f"  Spread:     {home} @ {sp_home_odds}  |  {away} @ {sp_away_odds}\n"
        f"  Total:      Over {tot_over}  |  Under {tot_under}\n"
        f"\n"
        f"📈 <b>CONSENSUS</b>\n"
        f"  Moneyline:\n"
        f"    {home}  {ml_bet_home} bets / {ml_money_home} money\n"
        f"    {away}  {ml_bet_away} bets / {ml_money_away} money\n"
        f"  Spread:\n"
        f"    {home}  {sp_bet_home} bets / {sp_money_home} money\n"
        f"    {away}  {sp_bet_away} bets / {sp_money_away} money\n"
        f"  Total:\n"
        f"    Over   {tot_bet_over} bets / {tot_money_over} money\n"
        f"    Under  {tot_bet_under} bets / {tot_money_under} money\n"
    )
    return message


def send_telegram(event_meta: dict, event_data: dict) -> bool:
    """
    Send a Telegram notification for an upcoming event.

    Returns True on success, False on failure.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not set in .env")
        return False

    message = build_message(event_meta, event_data)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram notification sent for event: {event_meta.get('event_full_name')}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False
