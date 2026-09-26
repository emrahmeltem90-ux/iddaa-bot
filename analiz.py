import os
import math
import datetime
import json
import time
import urllib.request
import urllib.parse

# Configuration & Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_KEY = "4b7109b6760cf29b78701c45406dbd9a"

IDDAA_LEAGUES = [
    203, 204, 636, 637,  # Türkiye (Süper Lig, 1.Lig, 2.Lig, 3.Lig)
    39, 40, 41, 42,      # İngiltere (Premier, Champ, League 1, League 2)
    140, 141,            # İspanya (La Liga, La Liga 2)
    135, 136,            # İtalya (Serie A, Serie B)
    78, 79,              # Almanya (Bundesliga, 2. Bundesliga)
    61, 62,              # Fransa (Ligue 1, Ligue 2)
    88, 89,              # Hollanda (Eredivisie, Eerste Divisie)
    94,                  # Portekiz
    253,                 # ABD (MLS)
    2, 3, 848, 5, 10, 32 # Şampiyonlar Ligi, Avrupa Ligi, Konferans, Uluslar Ligi
]

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"HTTP İstek Hatası: {e}")
    return None

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token veya chat_id eksik!")
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
        send_telegram("⚠️ API'den bugün için maç bülteni çekilemedi.")
        return

    fixtures = data.get("response", [])
    iddaa_fixtures = [f for f in fixtures if f.get("league", {}).get("id") in IDDAA_LEAGUES]
    target_fixtures = iddaa_fixtures if len(iddaa_fixtures) > 0 else fixtures
    
    analyzed_matches = []
    
    # Kota koruması için her çalıştırmada en fazla 25 maç analiz edilir
    for item in target_fixtures[:25]:
        fixture_id = item.get("fixture", {}).get("id")
        home_team = item.get("teams", {}).get("home", {}).get("name", "Ev")
        away_team = item.get("teams", {}).get("away", {}).get("name", "Deplasman")
        league_name = item.get("league", {}).get("name", "Lig")
        
        time.sleep(2)
        
        pred_url = f"https://v3.football.api-sports.io/predictions?fixture={fixture_id}"
        pred_data = http_get(pred_url, headers)
        
        if pred_data and pred_data.get("response"):
            pred_item = pred_data["response"][0]
            goals_exp = pred_item.get("predictions", {}).get("goals", {})
            
            try:
                home_exp = float(goals_exp.get("home") or 1.3)
                away_exp = float(goals_exp.get("away") or 1.1)
            except (ValueError, TypeError):
                home_exp, away_exp = 1.3, 1.1
            
            over25, over35, btts = calculate_poisson_probs(home_exp, away_exp)
            
            analyzed_matches.append({
                "home": home_team,
                "away": away_team,
                "league": league_name,
                "over25": over25,
                "over35": over35,
                "btts": btts
            })

    if not analyzed_matches:
        send_telegram("ℹ️ Bugün taranacak uygun İddaa maçı bulunamadı.")
        return

    # En yüksek 2.5 Üst oranına göre sırala
    analyzed_matches.sort(key=lambda x: x["over25"], reverse=True)

    # 1. BOTUN ÇALIŞTIĞINI KANITLAYAN GENEL ÖZET MESAJI
    summary_msg = f"📊 <b>İDDAA BÜLTEN TARAMA ÖZETİ</b>\n\n"
    summary_msg += f"🔍 Taranan Maç Sayısı: {len(analyzed_matches)}\n\n"
    summary_msg += f"🔥 <b>Günün En Yüksek Gol Beklentili 3 Maçı:</b>\n\n"
    
    for idx, match in enumerate(analyzed_matches[:3], 1):
        summary_msg += f"{idx}. <b>{match['home']} - {match['away']}</b>\n"
        summary_msg += f"   🏆 {match['league']}\n"
        summary_msg += f"   ⚽ 2.5 Üst: %{match['over25']:.1f} | 🤝 KG Var: %{match['btts']:.1f}\n\n"

    send_telegram(summary_msg)

    # 2. %50 EŞİĞİNİ GEÇENLER İÇİN DETAYLI BİLDİRİM
    for match in analyzed_matches:
        if match["over25"] >= 50 or match["btts"] >= 50:
            msg = f"🚨 <b>GOL FIRSAT SİNYALİ</b>\n\n"
            msg += f"⚔️ <b>{match['home']} vs {match['away']}</b>\n"
            msg += f"🏆 <b>Lig:</b> {match['league']}\n\n"
            msg += f"🟢 <b>2.5 Üst İhtimali:</b> %{match['over25']:.1f}\n"
            msg += f"🤝 <b>KG Var İhtimali:</b> %{match['btts']:.1f}\n"
            msg += f"🔥 <b>3.5 Üst İhtimali:</b> %{match['over35']:.1f}\n"
            send_telegram(msg)

if __name__ == "__main__":
    main()
