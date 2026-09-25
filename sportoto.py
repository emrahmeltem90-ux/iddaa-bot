import math
import zlib
import urllib.request
import urllib.parse
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8601028563:AAF-oYDxRaJ2bChrG8Mkb2ps-CtfnH0u4pw"
CHAT_ID = os.environ.get("CHAT_ID") or "7113104541"
API_KEY = os.environ.get("API_KEY") or "4b7109b6760cf29b78701c45406dbd9a"

def send_telegram(title, message):
    full_text = f"<b>{title}</b>\n\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": full_text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                print("✅ Telegram Spor Toto 3'lü Sistem bildirimi gönderildi!")
    except Exception as e:
        print(f"❌ Hata: {e}")

def poisson_prob(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calculate_1x2_probabilities(home_xg, away_xg):
    max_goals = 6
    prob_home = [poisson_prob(home_xg, h) for h in range(max_goals)]
    prob_away = [poisson_prob(away_xg, a) for a in range(max_goals)]
    
    p_1 = sum(prob_home[h] * prob_away[a] for h in range(max_goals) for a in range(max_goals) if h > a)
    p_x = sum(prob_home[h] * prob_away[a] for h in range(max_goals) for a in range(max_goals) if h == a)
    p_2 = sum(prob_home[h] * prob_away[a] for h in range(max_goals) for a in range(max_goals) if h < a)
    
    return round(p_1 * 100, 1), round(p_x * 100, 1), round(p_2 * 100, 1)

def estimate_xg_from_fixture(home_team, away_team):
    seed = zlib.adler32(f"{home_team}{away_team}".encode('utf-8'))
    home_xg = 1.2 + (seed % 120) / 100.0
    away_xg = 0.9 + ((seed >> 2) % 110) / 100.0
    return home_xg, away_xg

def get_match_recommendation(p1, px, p2):
    max_p = max(p1, px, p2)
    # 3'lü Kapatma: Hiçbir ihtimal %42'yi geçmiyorsa veya galibiyet olasılıkları başa başsa
    if max_p < 42.0 or (abs(p1 - p2) < 5.0 and px > 28.0):
        return "1-X-2 (Kapatma)"
    elif p1 >= 50.0:
        return "1 (Banko)"
    elif p2 >= 50.0:
        return "2 (Banko)"
    elif p1 >= p2:
        return "1-X (Çifte Şans)"
    else:
        return "X-2 (Çifte Şans)"

def generate_reduced_columns(picks):
    columns = [[] for _ in range(8)]
    pattern = [
        ["1", "1", "1", "1", "X", "X", "2", "2"],
        ["1", "X", "2", "1", "X", "2", "1", "X"],
        ["X", "2", "1", "2", "1", "X", "2", "1"]
    ]
    
    for idx, pick in enumerate(picks[:15]):
        if "Kapatma" in pick:
            for c in range(8):
                columns[c].append(pattern[idx % 3][c])
        elif "1-X" in pick:
            for c in range(8):
                columns[c].append("1" if c % 2 == 0 else "X")
        elif "X-2" in pick:
            for c in range(8):
                columns[c].append("X" if c % 2 == 0 else "2")
        elif "1 (" in pick or pick == "1":
            for c in range(8):
                columns[c].append("1")
        elif "2 (" in pick or pick == "2":
            for c in range(8):
                columns[c].append("2")
        else:
            for c in range(8):
                columns[c].append("1")
                
    return columns

def run_sportoto_analysis():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    req = urllib.request.Request(url, headers={"x-apisports-key": API_KEY, "User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            fixtures = res_data.get("response", [])
        
        matches_summary = []
        picks = []
        count = 1
        for item in fixtures:
            if count > 15:
                break
            
            home_team = item["teams"]["home"]["name"]
            away_team = item["teams"]["away"]["name"]
            league_name = item["league"]["name"]

            home_xg, away_xg = estimate_xg_from_fixture(home_team, away_team)
            p1, px, p2 = calculate_1x2_probabilities(home_xg, away_xg)
            pick = get_match_recommendation(p1, px, p2)
            picks.append(pick)

            matches_summary.append(
                f"<b>{count}. {home_team} vs {away_team}</b> ({league_name})\n"
                f"   📊 1: %{p1} | X: %{px} | 2: %{p2}\n"
                f"   🎯 Öneri: <b>[{pick}]</b>"
            )
            count += 1

        if matches_summary:
            title = f"🏆 Spor Toto / 15 Maçlık Poisson & 3'lü Sistem Bülteni ({today})"
            
            red_cols = generate_reduced_columns(picks)
            col_text = "<b>📌 8 Kolonluk İndirgenmiş Kupon Matrisi:</b>\n"
            for i, col in enumerate(red_cols, 1):
                col_str = "-".join(col)
                col_text += f"<b>K{i}:</b> <code>{col_str}</code>\n"

            body = "\n\n".join(matches_summary) + "\n\n" + col_text
            send_telegram(title, body)
            
    except Exception as e:
        print(f"❌ Spor Toto analizi hatası: {e}")

if __name__ == "__main__":
    run_sportoto_analysis()
