import urllib.request
import urllib.parse
import json
import os
import math

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8601028563:AAF-oYDxRaJ2bChrG8Mkb2ps-CtfnH0u4pw"
CHAT_ID = os.environ.get("CHAT_ID") or "7113104541"

# Sadece İddaa Bülteninde Açılan Majör Ligler
IDDAA_LIGLERI = [
    203,  # Trendyol Süper Lig
    204,  # TFF 1. Lig
    39,   # Premier League
    40,   # Championship
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    2,    # Şampiyonlar Ligi
    3,    # Avrupa Ligi
    848,  # Konferans Ligi
    5,    # Uluslar Ligi / Milli Maçlar
    88,   # Eredivisie
    94,   # Primeira Liga
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "HTML"
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            pass
    except Exception as e:
        print(f"Telegram Gönderim Hatası: {e}")

def calculate_poisson_goals(home_xg, away_xg):
    max_goals = 6
    def poisson(lmbda, k):
        return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

    prob_matrix = [[poisson(home_xg, h) * poisson(away_xg, a) for a in range(max_goals)] for h in range(max_goals)]

    p_over25 = sum(prob_matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h + a) > 2.5)
    p_over35 = sum(prob_matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h + a) > 3.5)
    p_btts = sum(prob_matrix[h][a] for h in range(1, max_goals) for a in range(1, max_goals))

    return round(p_over25 * 100, 1), round(p_over35 * 100, 1), round(p_btts * 100, 1)

def run_live_signal_check():
    # Örnek İddaa Maç Akışı
    sample_matches = [
        {
            "league": {"id": 203, "name": "Trendyol Süper Lig"},
            "teams": {"home": {"name": "Galatasaray"}, "away": {"name": "Kasımpaşa"}},
            "home_xg": 2.2, "away_xg": 1.4,
            "odds_drop": 14.5
        },
        {
            "league": {"id": 140, "name": "La Liga"},
            "teams": {"home": {"name": "Villarreal"}, "away": {"name": "Girona"}},
            "home_xg": 1.9, "away_xg": 1.6,
            "odds_drop": 8.0
        }
    ]

    for match in sample_matches:
        league_id = match.get("league", {}).get("id")
        
        # 1. İddaa Dışı Lig Filtresi
        if league_id not in IDDAA_LIGLERI:
            continue

        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]
        p_over25, p_over35, p_btts = calculate_poisson_goals(match["home_xg"], match["away_xg"])
        odds_drop = match.get("odds_drop", 0)

        # 2. Sinyal Kriteri: 2.5 Üst %68+, KG VAR %65+ VEYA %10+ Oran Düşüşü
        if p_over25 >= 68.0 or p_btts >= 65.0 or odds_drop >= 10.0:
            signals = []
            if p_over25 >= 68.0:
                signals.append(f"⚽ <b>2.5 ÜST:</b> %{p_over25}")
            if p_over35 >= 42.0:
                signals.append(f"🔥 <b>3.5 ÜST SÜRPRİZ:</b> %{p_over35}")
            if p_btts >= 65.0:
                signals.append(f"🤝 <b>KG VAR:</b> %{p_btts}")
            if odds_drop >= 10.0:
                signals.append(f"📉 <b>ANLIK ORAN DÜŞÜŞÜ:</b> -%{odds_drop}")

            msg = (
                f"🚨 <b>İDDAA ANLIK GOL & ORAN SİNYALİ</b> 🚨\n\n"
                f"⚔️ <b>{home_team} vs {away_team}</b>\n"
                f"🏆 <b>Lig:</b> {match['league']['name']}\n\n"
                f"🎯 <b>Öne Çıkan Değerler:</b>\n" + "\n".join(signals) + "\n\n"
                f"📲 <i>Bilyoner/İddaa bülteninden hemen oynanabilir.</i>"
            )
            send_telegram(msg)

if __name__ == "__main__":
    run_live_signal_check()
