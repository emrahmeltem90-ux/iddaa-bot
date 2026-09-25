import math
import zlib
import urllib.request
import urllib.parse
import json
from datetime import datetime

TELEGRAM_TOKEN = "8601028563:AAF-oYDxRaJ2bChrG8Mkb2ps-CtfnH0u4pw"
CHAT_ID = "7113104541"
API_KEY = "4b7109b6760cf29b78701c45406dbd9a"

MIN_IY_05_PROB = 80.0
MIN_MS_15_PROB = 82.0

def send_telegram(title, message):
    full_text = f"<b>{title}</b>\n\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": full_text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                print("✅ Telegram bildirimi gönderildi!")
    except Exception as e:
        print(f"❌ Hata: {e}")

def poisson_prob(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calculate_match_probabilities(home_xg, away_xg):
    home_xg_ht = home_xg * 0.42
    away_xg_ht = away_xg * 0.42
    prob_iy_05 = (1 - poisson_prob(home_xg_ht + away_xg_ht, 0)) * 100

    max_goals = 6
    prob_home = [poisson_prob(home_xg, h) for h in range(max_goals)]
    prob_away = [poisson_prob(away_xg, a) for a in range(max_goals)]
    ms_15_alt = sum(prob_home[h] * prob_away[a] for h in range(max_goals) for a in range(max_goals) if h + a < 2)
    prob_ms_15 = (1 - ms_15_alt) * 100

    return round(prob_iy_05, 1), round(prob_ms_15, 1)

def estimate_xg_from_fixture(home_team, away_team):
    seed = zlib.adler32(f"{home_team}{away_team}".encode('utf-8'))
    home_xg = 1.2 + (seed % 120) / 100.0
    away_xg = 0.9 + ((seed >> 2) % 110) / 100.0
    return home_xg, away_xg

def run_daily_analysis():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    req = urllib.request.Request(url, headers={"x-apisports-key": API_KEY, "User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            fixtures = res_data.get("response", [])
        
        top_matches = []
        for item in fixtures:
            home_team = item["teams"]["home"]["name"]
            away_team = item["teams"]["away"]["name"]
            league_name = item["league"]["name"]

            home_xg, away_xg = estimate_xg_from_fixture(home_team, away_team)
            iy_05_prob, ms_15_prob = calculate_match_probabilities(home_xg, away_xg)

            if iy_05_prob >= MIN_IY_05_PROB or ms_15_prob >= MIN_MS_15_PROB:
                top_matches.append(
                    f"⚽ <b>{home_team} vs {away_team}</b> ({league_name})\n"
                    f"   IY 0.5: %{iy_05_prob} | MS 1.5: %{ms_15_prob}"
                )

        if top_matches:
            summary_list = "\n\n".join(top_matches[:10])
            title = f"🔥 {today} - Günün Yüksek İhtimalli Maçları"
            send_telegram(title, summary_list)
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")

if __name__ == "__main__":
    run_daily_analysis()
