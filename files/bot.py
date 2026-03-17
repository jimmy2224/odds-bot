import os
import requests
import schedule
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

SPORTS = [
    ("soccer_epl", "EPL"),
    ("soccer_spain_la_liga", "La Liga"),
    ("basketball_nba", "NBA"),
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def get_confidence(odds):
    dist = abs(odds - 1.5)
    if dist <= 0.05: return 95
    if dist <= 0.1: return 88
    if dist <= 0.2: return 78
    if dist <= 0.3: return 65
    if dist <= 0.5: return 52
    return 38

def fetch_and_send():
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    message = f"<b>🎯 1.5 Odds Picks — {now}</b>\n\n"
    total_picks = 0

    for sport_key, sport_name in SPORTS:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
            f"?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
        )
        try:
            res = requests.get(url, timeout=10)
            games = res.json()
        except Exception as e:
            message += f"<b>{sport_name}</b>: Could not fetch data\n\n"
            continue

        if not isinstance(games, list) or not games:
            continue

        picks = []
        for game in games:
            bm = game.get("bookmakers", [])
            if not bm:
                continue
            mkt = next((m for m in bm[0].get("markets", []) if m["key"] == "h2h"), None)
            if not mkt:
                continue
            outcomes = mkt.get("outcomes", [])
            if not outcomes:
                continue
            best = min(outcomes, key=lambda o: abs(o["price"] - 1.5))
            dist = abs(best["price"] - 1.5)
            if dist <= 0.3:
                conf = get_confidence(best["price"])
                picks.append({
                    "home": game["home_team"],
                    "away": game["away_team"],
                    "outcome": best["name"],
                    "odds": best["price"],
                    "conf": conf,
                    "time": game["commence_time"]
                })

        if picks:
            picks.sort(key=lambda x: abs(x["odds"] - 1.5))
            message += f"<b>⚽ {sport_name}</b>\n"
            for p in picks[:5]:
                star = "🟢" if p["conf"] >= 80 else "🟡"
                match_time = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
                time_str = match_time.strftime("%d %b %H:%M")
                message += (
                    f"{star} <b>{p['home']} vs {p['away']}</b>\n"
                    f"   Pick: {p['outcome']} @ <b>{p['odds']:.2f}</b> | Conf: {p['conf']}%\n"
                    f"   {time_str}\n\n"
                )
            total_picks += len(picks[:5])

    if total_picks == 0:
        message += "No strong 1.5 odds picks found right now. Check back later."

    message += f"\n<i>Powered by OddsPredictor Bot</i>"
    send_message(message)
    print(f"[{datetime.now()}] Sent {total_picks} picks")

def main():
    print("Bot started...")
    send_message("✅ <b>Odds Predictor Bot is online!</b>\nYou'll receive picks at 7:00 AM, 12:00 PM, and 6:00 PM daily.")

    schedule.every().day.at("07:00").do(fetch_and_send)
    schedule.every().day.at("12:00").do(fetch_and_send)
    schedule.every().day.at("18:00").do(fetch_and_send)

    # Send one immediately on startup
    fetch_and_send()

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
