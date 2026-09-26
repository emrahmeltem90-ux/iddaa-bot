import os
import datetime
import requests
import numpy as np
from scipy.stats import poisson

# Configuration & Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = "4b7109b6760cf29b78701c45406dbd9a"

# İddaa bültenindeki başlıca ligler (API-Football ID'leri)
# 203: Süper Lig, 39: Premier League, 140: La Liga, 135: Serie A, 78: Bundesliga, 61: Ligue 1, 204: 1. Lig
TARGET_LEAGUES = [203, 39, 140, 135, 78, 61, 204]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def calculate_poisson_probs(home_exp, away_exp):
    max_goals = 10
    home_pmf = [poisson.pmf(i, home_exp) for i in range(max_goals)]
    away_pmf = [poisson.pmf(j, away_exp) for j in range(max_goals)]
    
    matrix = np.outer(home_pmf, away_pmf)
    
    over25 = sum(matrix[i, j] for i in range(max_goals) for j in range(max_goals) if i + j > 2.5)
    over35 = sum(matrix[i, j] for i in range(max_goals) for j in range(max_goals) if i + j > 3.5)
    btts = sum(matrix[i, j] for i in range(1, max_goals) for j in range(1, max_goals))
            
    return over25 * 100, over35 * 100, btts * 100

def main():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    headers = {'x-apisports-key': API_KEY}
    
    # Bugünün maçlarını çek
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print("API Bağlantı Hatası!")
        return

    fixtures = response.json().get("response", [])
    signals_sent = 0
    
    for item in fixtures:
        league_id = item["league"]["id"]
        if league_id not in TARGET_LEAGUES:
            continue
        
        fixture_id = item["fixture"]["id"]
        home_team = item["teams"]["home"]["name"]
        away_team = item["teams"]["away"]["name"]
        league_name = item["league"]["name"]
        
        # Tahmin & istatistik verisini çek
        pred_url = f"https://v3.football.api-sports.io/predictions?fixture={fixture_id}"
        pred_res = requests.get(pred_url, headers=headers)
        
        if pred_res.status_code == 200:
            pred_data = pred_res.json().get("response", [])
            if pred_data:
                goals_exp = pred_data[0].get("predictions", {}).get("goals", {})
                
                try:
                    home_exp = float(goals_exp.get("home") or 1.2)
                    away_exp = float(goals_exp.get("away") or 1.0)
                except (ValueError, TypeError):
                    home_exp, away_exp = 1.2, 1.0
                
                over25, over35, btts = calculate_poisson_probs(home_exp, away_exp)
                
                # Sinyal Kriterleri (3.5 Üst > %40 VEYA KG Var > %60 + 2.5 Üst > %65)
                if over35 > 40 or (btts > 60 and over25 > 65):
                    msg = f"🚨 <b>CANLI İDDAA GOL SİNYALİ</b>\n\n"
                    msg += f"⚔️ <b>{home_team} vs {away_team}</b>\n"
                    msg += f"🏆 <b>Lig:</b> {league_name}\n\n"
                    msg += f"🎯 <b>Poisson Analiz Değerleri:</b>\n"
                    if over35 > 40:
                        msg += f"🔥 <b>3.5 ÜST SÜRPRİZ:</b> %{over35:.1f}\n"
                    if btts > 60:
                        msg += f"🤝 <b>KG VAR:</b> %{btts:.1f}\n"
                    if over25 > 65:
                        msg += f"⚽ <b>2.5 ÜST:</b> %{over25:.1f}\n"
                    msg += f"\n📱 <i>İddaa / Bilyoner bülteninden takip edilebilir.</i>"
                    
                    send_telegram(msg)
                    signals_sent += 1

    print(f"Bugünün canlı bülten analizi tamamlandı. Gönderilen Sinyal: {signals_sent}")

if __name__ == "__main__":
    main()
