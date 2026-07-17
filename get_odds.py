import os
from dotenv import load_dotenv
from http_client import session
load_dotenv()

def _safe_round(value, digits=2):
    """Round a value safely, returning None if value is None."""
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def get_event_info(event_id):
    """
    Fetch live odds and community consensus for an event.
    Called 1 minute before the event starts.
    Does NOT fetch result data.
    """
    response = session.get(f'https://prod-website.pikkit.app/event/foryou/{event_id}')
    data = response.json()

    odds_list = data.get('odds') or []
    odds = odds_list[0].get('odds', {}) if odds_list else {}

    moneyline = odds.get('moneyline') or {}
    spread    = odds.get('spread')    or {}
    total     = odds.get('total')     or {}

    odds_moneyline_home = moneyline.get('home') or {}
    odds_moneyline_away = moneyline.get('away') or {}
    odds_spread_home    = spread.get('home')    or {}
    odds_spread_away    = spread.get('away')    or {}
    odds_total_over     = total.get('over')     or {}
    odds_total_under    = total.get('under')    or {}

    community = data.get('community', {})
    event_handle = community.get('total_wagered')

    moneyline_consensus_bet_pct_home   = community.get('breakdowns', {}).get('moneyline', {}).get('home', {}).get('bet_pct')
    moneyline_consensus_bet_pct_away   = community.get('breakdowns', {}).get('moneyline', {}).get('away', {}).get('bet_pct')
    moneyline_consensus_money_pct_home = community.get('breakdowns', {}).get('moneyline', {}).get('home', {}).get('handle_pct')
    moneyline_consensus_money_pct_away = community.get('breakdowns', {}).get('moneyline', {}).get('away', {}).get('handle_pct')
    spread_consensus_bet_pct_home      = community.get('breakdowns', {}).get('spread',    {}).get('home', {}).get('bet_pct')
    spread_consensus_bet_pct_away      = community.get('breakdowns', {}).get('spread',    {}).get('away', {}).get('bet_pct')
    spread_consensus_money_pct_home    = community.get('breakdowns', {}).get('spread',    {}).get('home', {}).get('handle_pct')
    spread_consensus_money_pct_away    = community.get('breakdowns', {}).get('spread',    {}).get('away', {}).get('handle_pct')
    total_consensus_bet_pct_over       = community.get('breakdowns', {}).get('total',     {}).get('over',  {}).get('bet_pct')
    total_consensus_bet_pct_under      = community.get('breakdowns', {}).get('total',     {}).get('under', {}).get('bet_pct')
    total_consensus_money_pct_over     = community.get('breakdowns', {}).get('total',     {}).get('over',  {}).get('handle_pct')
    total_consensus_money_pct_under    = community.get('breakdowns', {}).get('total',     {}).get('under', {}).get('handle_pct')

    event_data = {}
    event_data['event_id']            = event_id
    event_data['event_handle']        = _safe_round(event_handle)
    event_data['odds_moneyline_home'] = _safe_round(odds_moneyline_home.get('odds'))
    event_data['odds_moneyline_away'] = _safe_round(odds_moneyline_away.get('odds'))
    event_data['odds_spread_home']    = _safe_round(odds_spread_home.get('odds'))
    event_data['odds_spread_away']    = _safe_round(odds_spread_away.get('odds'))
    event_data['odds_total_over']     = _safe_round(odds_total_over.get('odds'))
    event_data['odds_total_under']    = _safe_round(odds_total_under.get('odds'))

    event_data['moneyline_consensus_bet_pct_home']   = _safe_round(moneyline_consensus_bet_pct_home   * 100 if moneyline_consensus_bet_pct_home   is not None else None)
    event_data['moneyline_consensus_bet_pct_away']   = _safe_round(moneyline_consensus_bet_pct_away   * 100 if moneyline_consensus_bet_pct_away   is not None else None)
    event_data['moneyline_consensus_money_pct_home'] = _safe_round(moneyline_consensus_money_pct_home * 100 if moneyline_consensus_money_pct_home is not None else None)
    event_data['moneyline_consensus_money_pct_away'] = _safe_round(moneyline_consensus_money_pct_away * 100 if moneyline_consensus_money_pct_away is not None else None)
    event_data['spread_consensus_bet_pct_home']      = _safe_round(spread_consensus_bet_pct_home      * 100 if spread_consensus_bet_pct_home      is not None else None)
    event_data['spread_consensus_bet_pct_away']      = _safe_round(spread_consensus_bet_pct_away      * 100 if spread_consensus_bet_pct_away      is not None else None)
    event_data['spread_consensus_money_pct_home']    = _safe_round(spread_consensus_money_pct_home    * 100 if spread_consensus_money_pct_home    is not None else None)
    event_data['spread_consensus_money_pct_away']    = _safe_round(spread_consensus_money_pct_away    * 100 if spread_consensus_money_pct_away    is not None else None)
    event_data['total_consensus_bet_pct_over']       = _safe_round(total_consensus_bet_pct_over       * 100 if total_consensus_bet_pct_over       is not None else None)
    event_data['total_consensus_bet_pct_under']      = _safe_round(total_consensus_bet_pct_under      * 100 if total_consensus_bet_pct_under      is not None else None)
    event_data['total_consensus_money_pct_over']     = _safe_round(total_consensus_money_pct_over     * 100 if total_consensus_money_pct_over     is not None else None)
    event_data['total_consensus_money_pct_under']    = _safe_round(total_consensus_money_pct_under    * 100 if total_consensus_money_pct_under    is not None else None)

    return event_data


def get_event_result(event_id):
    """
    Fetch only the WIN/LOSS result statuses for a closed event.
    Called periodically after the event status becomes 'closed'.
    Does NOT fetch odds or consensus data.
    """
    response = session.get(f'https://prod-website.pikkit.app/event/foryou/{event_id}')
    data = response.json()

    # closing_line is only populated once the event has finished
    closing_line = data.get('closing_line', [])
    cl_odds = closing_line[0].get('odds', {}) if closing_line else {}

    cl_moneyline = cl_odds.get('moneyline') or {}
    cl_spread    = cl_odds.get('spread')    or {}
    cl_total     = cl_odds.get('total')     or {}

    cl_moneyline_home = cl_moneyline.get('home') or {}
    cl_moneyline_away = cl_moneyline.get('away') or {}
    cl_spread_home    = cl_spread.get('home')    or {}
    cl_spread_away    = cl_spread.get('away')    or {}
    cl_total_over     = cl_total.get('over')     or {}
    cl_total_under    = cl_total.get('under')    or {}

    return {
        'result_moneyline_home': cl_moneyline_home.get('status'),
        'result_moneyline_away': cl_moneyline_away.get('status'),
        'result_spread_home':    cl_spread_home.get('status'),
        'result_spread_away':    cl_spread_away.get('status'),
        'result_total_over':     cl_total_over.get('status'),
        'result_total_under':    cl_total_under.get('status'),
    }



if __name__ == "__main__":
    event_id = '6a46edb2c6729e408556ee72'
    # event_id = '6a46edb2c6729e408556ee72'
    data = get_event_info(event_id)
    print(data)

