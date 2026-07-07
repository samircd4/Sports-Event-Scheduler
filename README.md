# Sports Event Scheduler — User Guide

This tool automatically fetches sports betting odds **1 minute before each game starts** and sends them to your Telegram bot. It also saves all data to a CSV file.

---

## What You'll Need (One-Time Setup)

Before running anything, make sure the following are done **once**:

### 1. Install `uv` (the tool that runs the scripts)

Open **Command Prompt** (press `Win + R`, type `cmd`, hit Enter) and paste this:

```
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen Command Prompt after it finishes.

---

### 2. Set up your credentials in the `.env` file

Open the `.env` file (it's in the same folder as the scripts) in Notepad and make sure it has these three lines filled in:

```
AUTHORIZATION_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

> ⚠️ Never share this file with anyone. It contains your private keys.

---

## How to Open the Folder in Command Prompt

1. Open **File Explorer** and go to the folder where these scripts are saved
2. Click on the **address bar** at the top (it shows the folder path)
3. Type `cmd` and press **Enter** — a Command Prompt window will open directly in that folder

---

## Running the Scripts

### ▶️ Option A — Run the Scheduler (Recommended)

This is the **main script**. Run it once in the morning and leave it running all day.
It will automatically send odds to your Telegram **1 minute before each game starts**.

```
uv run scheduler.py
```

---

### 🔍 What Exactly Happens When You Run `scheduler.py`

Here is a step-by-step breakdown of everything the scheduler does — in plain English:

**Step 1 — It starts and shows a startup message**
```
============================================================
  Event Scheduler started
  Trigger: 60s before each event
  Refresh interval: 60 minutes
============================================================
```
This confirms the script is alive and running.

**Step 2 — It fetches today's game list immediately**
```
[INFO] Refreshing event list...
[INFO] Event list refreshed — 10 new event(s) added. Total tracked: 10
```
It connects to the sports data source and loads all of today's scheduled games.

**Step 3 — It checks the clock every 10 seconds**
Behind the scenes, it keeps checking: *"Is any game starting in the next 60 seconds?"*
You won't see anything on screen during this time — that's normal. It's just waiting.

**Step 4 — Exactly 1 minute before a game starts, it fires**
```
[INFO] Triggering: Belgium vs. USA (starts: Jul 07, 2026 06:00 AM)
[INFO] Fetching odds for: Belgium vs. USA
[INFO] Telegram notification sent for event: Belgium vs. USA
[INFO] Updated CSV row for: Belgium vs. USA
```
For each game it:
1. Fetches the latest odds from the data source
2. Sends a formatted message to your Telegram bot
3. Saves/updates the row in `events_data.csv`

**Step 5 — Every 60 minutes it re-fetches the game list**
```
[INFO] Refreshing event list...
[INFO] Event list refreshed — 2 new event(s) added. Total tracked: 12
```
If any new games were added to the schedule during the day, they get picked up automatically.

**Step 6 — If it missed a game (started the script too late)**
```
[WARNING] Missed window for: Spain vs. Portugal (started: Jul 07, 2026 01:00 AM)
```
This just means that game had already started by the time the script ran. No action needed — it moves on to the next upcoming game.

**Step 7 — It keeps running until you stop it**
Press `Ctrl + C` to stop the scheduler at any time.

> ✅ **Best practice:** Start the scheduler first thing in the morning before any games begin.

---

### ▶️ Option B — Send All Events Right Now

If you want to **immediately send all of today's events** to Telegram (useful for reviewing the day's slate):

```
uv run send_all_events.py
```

This runs once and exits. It sends all games with their current odds to your bot.

---

## What Happens in Telegram

For each game, you'll receive a message like this:

```
⚾ [MLB] New York Yankees vs. Tampa Bay Rays
⏰ Starts: Jul 07, 2026 04:40 AM

📊 ODDS (Full Game)
  Moneyline:  Tampa Bay Rays 6.06  |  New York Yankees 1.18
  Spread:     Tampa Bay Rays @ 1.65  |  New York Yankees @ 1.44
  Total:      Over 2.06  |  Under 1.87

📈 CONSENSUS
  Moneyline:
    Tampa Bay Rays  44.18% bets / 56.8% money
    New York Yankees  55.82% bets / 43.2% money
  Spread:
    Tampa Bay Rays  56.1% bets / 44.39% money
    New York Yankees  43.9% bets / 55.61% money
  Total:
    Over   47.44% bets / 43.4% money
    Under  52.56% bets / 56.6% money
```

---

## The CSV File (`events_data.csv`)

After running either script, a file called `events_data.csv` will appear (or update) in the same folder.

- Open it with **Microsoft Excel** or **Google Sheets**
- Each row = one game with all its odds and consensus data
- If a game already exists in the file, its row gets **updated** (no duplicates)

---

## Files in This Folder (What Each One Does)

| File | Purpose |
|---|---|
| `scheduler.py` | ▶️ Main script — runs all day, sends alerts 1 min before each game |
| `send_all_events.py` | Sends all today's games to Telegram immediately (one-shot) |
| `events_data.csv` | The output CSV file with all game data |
| `.env` | Your private credentials (do not share) |
| `all_events.py` | Fetches the list of today's games (used internally) |
| `get_odds.py` | Fetches odds for a single game (used internally) |
| `notifier.py` | Sends the Telegram message (used internally) |
| `storage.py` | Saves data to the CSV (used internally) |
| `scheduler.log` | Log file — shows what the scheduler did and any errors |

---

## Troubleshooting

**"uv is not recognized"**
→ Restart Command Prompt after installing `uv`, or restart your computer.

**Telegram message not arriving**
→ Check that `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` are correct.
→ Make sure you've sent at least one message to your bot first (open Telegram, find your bot, press Start).

**"No events found" or script crashes**
→ Check that `AUTHORIZATION_KEY` in `.env` is correct and not expired.

**"Script shows 'Missed window' for all events"**
→ This is normal if you start the scheduler after games have already begun. Start it fresh the next morning.

---

## Developer Information

| | |
|---|---|
| **Developer** | Somir Chandra Dash |
| **Website** | [drpythonsolutions.com](https://drpythonsolutions.com) |

> For support, questions, or upgrade requests (e.g. Google Sheets integration), reach out via the website above.
