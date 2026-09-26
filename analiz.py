import os
import math
import datetime
import json
import urllib.request
import urllib.parse

# Configuration & Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_KEY = "4b7109b6760cf29b78701c45406dbd9a"

# Genişletilmiş Lig & Turnuva Listesi (Milli Maçlar + Kulüp Ligleri + Avrupa Kupaları)
TARGET_LEAGUES = [5, 10, 32, 203, 204, 39, 140, 135, 78, 61, 88, 94, 2, 3, 848]

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"HTTP İstek Hatası ({url}): {e}")
    return None

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token veya chat_id bulunamadı!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram Gönderim Hatası: {e}")

def poisson_pmf(k, lambd):
    if lambd <= 0:
        return 1.0 if k == 0 else 0.0
    return (lambd ** k) * math.exp(-lambd) / math.factorial(k)

def calculate_poisson_probs(home_exp, away_exp):
    max_goals = 10
    home_pmf = [poisson_pmf(i, home_exp) for i in range(max_goals)]
    away_pmf = [poisson_pmf(j, away_exp) for j in range(max_goals)]
    
    over25, over35, btts = 0.0, 0.0, 0.0
    for i in range(max_goals):
        for j in range(max_goals):
            p = home_pmf[i] * away_pmf[j]
            if i + j > 2.5:
                over25 += p
            if i + j > 3.5:
                over35 += p
            if i > 0 and j > 0:
                btts += p
            
    return over25 * 100, over35 * 100, btts * 100

def main():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    headers = {'x-apisports-key': API_KEY}
    
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    data = http_get(url, headers)
    
    if not data:
        print("API'den veri çekilemedi.")
        return

    fixtures = data.get("response", [])
    signals_sent = 0
    
    for item in fixtures:
        league_id = item.get("league", {}).get("id")
        if league_id not in TARGET_LEAGUES:
            continue
        
        fixture_id = item.get("fixture", {}).get("id")
        home_team = item.get("teams", {}).get("home", {}).get("name", "Ev")
        away_team = item.get("teams", {}).get("away", {}).get("name", "Deplasman")
        league_name = item.get("league", {}).get("name", "Lig")
        
        pred_url = f"https://v3.football.api-sports.io/predictions?fixture={fixture_id}"
        pred_data = http_get(pred_url, headers)
        
        if pred_data and pred_data.get("response"):
            pred_item = pred_data["response"][0]
            goals_exp = pred_item.get("predictions", {}).get("goals", {})
            
            try:
                home_exp = float(goals_exp.get("home") or 1.2)
                away_exp = float(goals_exp.get("away") or 1.0)
            except (ValueError, TypeError):
                home_exp, away_exp = 1.2, 1.0
            
            over25, over35, btts = calculate_poisson_probs(home_exp, away_exp)
            
            if over35 > 40 or (btts > 60 and over25 > 65):
                msg = f"🚨 <b>CANLI İDDAA GOL SİNYALİ</b>\n\n"
                msg += f"⚔️ <b>{home_team} vs {away_team}</b>\n"
                msg += f"🏆 <b>Turnuva/Lig:</b> {league_name}\n\n"
                msg += f"🎯 <b>Poisson Analiz Değerleri:</b>\n"
                if over35 > 40:
                    msg += f"🔥 <b>3.5 ÜST SÜRPRİZ:</b> %{over35:.1f}\n"
                if btts > 60:
                    msg += f"🤝 <b>KG VAR:</b> %{btts:.1f}\n"
                if over25 > 65:
                    msg += f"⚽ <b>2.5 ÜST:</b> %{over25:.1f}\n"
                msg += f"\n📱 <i>İddaa bülteninden takip edilebilir.</i>"
                
                send_telegram(msg)
                signals_sent += 1

    print(f"Bugünün bülten analizi tamamlandı. Gönderilen Sinyal: {signals_sent}")

if __name__ == "__main__":
    main()
