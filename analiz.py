import os
import math
import datetime
import json
import time
import urllib.request
import urllib.error

# ============================================================
# SKORLAB TELEGRAM BOT · v2
# Bol Gollü Maç Sinyali · Bülten Ligleri · Günlük 09:00 TR
# ============================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_KEY = "4b7109b6760cf29b78701c45406dbd9a"

# ============================================================
# BOL GOLLÜ LİGLER (2024/25 istatistikleri)
# ============================================================
UST_LIGLER = [
    # === TÜRKİYE ===
    203,   # Türkiye Süper Lig        (~2.85 gol/maç)
    204,   # Türkiye 1. Lig            (~2.70 gol/maç)

    # === İNGİLTERE ===
    39,    # Premier Lig               (~2.90 gol/maç)
    40,    # Championship              (~2.60 gol/maç)

    # === İSPANYA ===
    140,   # La Liga                   (~2.60 gol/maç)
    141,   # La Liga 2                 (~2.40 gol/maç)

    # === İTALYA ===
    135,   # Serie A                   (~2.80 gol/maç)
    136,   # Serie B                   (~2.60 gol/maç)

    # === ALMANYA (ÇOK GOLLÜ) ===
    78,    # Bundesliga                (~3.20 gol/maç) 🔥
    79,    # 2. Bundesliga             (~3.10 gol/maç) 🔥

    # === FRANSA ===
    61,    # Ligue 1                   (~2.80 gol/maç)
    62,    # Ligue 2                   (~2.50 gol/maç)

    # === HOLLANDA (EN GOLLÜ) ===
    88,    # Eredivisie                (~3.30 gol/maç) 🔥🔥
    89,    # Eerste Divisie            (~3.20 gol/maç) 🔥

    # === PORTEKİZ ===
    94,    # Primeira Liga             (~2.70 gol/maç)

    # === BELÇİKA (GOLLÜ) ===
    144,   # Pro League                (~3.00 gol/maç) 🔥

    # === AVUSTURYA (ÇOK GOLLÜ) ===
    218,   # Bundesliga                (~3.15 gol/maç) 🔥

    # === İSVİÇRE (ÇOK GOLLÜ) ===
    207,   # Süper Lig                 (~3.20 gol/maç) 🔥

    # === İSKANDİNAV (GOLLÜ) ===
    103,   # Norveç Eliteserien        (~3.10 gol/maç) 🔥
    113,   # İsveç Allsvenskan         (~3.00 gol/maç) 🔥
    119,   # Danimarka Süper Lig       (~2.95 gol/maç)

    # === AVRUPA KUPALARI ===
    2,     # Şampiyonlar Ligi          (~2.90 gol/maç)
    3,     # Avrupa Ligi               (~2.90 gol/maç)
    848,   # Konferans Ligi            (~2.80 gol/maç)
]

# ============================================================
# LİG İSİMLERİ (mesajda göstermek için)
# ============================================================
LIG_ISIMLERI = {
    203: "Türkiye Süper Lig",
    204: "Türkiye 1. Lig",
    39:  "Premier Lig",
    40:  "Championship",
    140: "La Liga",
    141: "La Liga 2",
    135: "Serie A",
    136: "Serie B",
    78:  "Bundesliga",
    79:  "2. Bundesliga",
    61:  "Ligue 1",
    62:  "Ligue 2",
    88:  "Eredivisie",
    89:  "Eerste Divisie",
    94:  "Primeira Liga",
    144: "Belçika Pro League",
    218: "Avusturya Bundesliga",
    207: "İsviçre Süper Lig",
    103: "Norveç Eliteserien",
    113: "İsveç Allsvenskan",
    119: "Danimarka Süper Lig",
    2:   "Şampiyonlar Ligi",
    3:   "Avrupa Ligi",
    848: "Konferans Ligi",
}

# ============================================================
# AYARLAR
# ============================================================
MAX_MAC = 30          # Günlük max analiz (kota koruması)
API_BEKLEME = 6.5     # Her maç arası bekleme (dakikalık limit)
GOLLU_ESIK = 60       # 2.5Ü veya KGV bu yüzdenin üstündeyse "gollü"


# ============================================================
# HTTP GET
# ============================================================
def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("⚠️ API limiti (429). 60 sn bekleniyor...")
                time.sleep(60)
            else:
                print(f"HTTP Hatası: {e}")
                break
        except Exception as e:
            print(f"HTTP Hatası: {e}")
            break
    return None


# ============================================================
# TELEGRAM GÖNDER
# ============================================================
def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat_id eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram Hatası: {e}")


# ============================================================
# POISSON
# ============================================================
def poisson_pmf(k, lambd):
    if lambd <= 0:
        return 1.0 if k == 0 else 0.0
    return (lambd ** k) * math.exp(-lambd) / math.factorial(k)


def poisson_probs(home_exp, away_exp):
    max_goals = 10
    home_pmf = [poisson_pmf(i, home_exp) for i in range(max_goals)]
    away_pmf = [poisson_pmf(j, away_exp) for j in range(max_goals)]

    over25, over35, btts = 0.0, 0.0, 0.0
    for i in range(max_goals):
        for j in range(max_goals):
            p = home_pmf[i] * away_pmf[j]
            if i + j > 2.5: over25 += p
            if i + j > 3.5: over35 += p
            if i > 0 and j > 0: btts += p

    return over25 * 100, over35 * 100, btts * 100


# ============================================================
# ANA FONKSİYON
# ============================================================
def main():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    headers = {'x-apisports-key': API_KEY}

    print(f"📅 {today} maçları çekiliyor...")

    # 1) Bugünkü maçlar
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    data = http_get(url, headers)

    if not data:
        send_telegram("⚠️ API'den bugün için maç bülteni çekilemedi.")
        return

    fixtures = data.get("response", [])
    print(f"📊 Toplam API maçı: {len(fixtures)}")

    # 2) Sadece üst ligleri filtrele
    filtrelenmis = [f for f in fixtures if f.get("league", {}).get("id") in UST_LIGLER]
    print(f"🎯 Bülten ligi maçı: {len(filtrelenmis)}")

    # Hiç maç yoksa boş mesaj at
    if not filtrelenmis:
        send_telegram(
            f"ℹ️ Bugün bülten liglerinde maç yok.\n"
            f"(API'de {len(fixtures)} maç var ama hiçbiri üst liglerden değil.)"
        )
        return

    # 3) Her maçı analiz et
    analyzed = []
    for item in filtrelenmis[:MAX_MAC]:
        fixture_id = item.get("fixture", {}).get("id")
        home = item.get("teams", {}).get("home", {}).get("name", "Ev")
        away = item.get("teams", {}).get("away", {}).get("name", "Deplasman")
        league_id = item.get("league", {}).get("id")
        league_name = LIG_ISIMLERI.get(league_id, item.get("league", {}).get("name", "Lig"))

        # Maç saati (TR saati)
        match_date = item.get("fixture", {}).get("date", "")
        try:
            dt = datetime.datetime.fromisoformat(match_date.replace("Z", "+00:00"))
            dt_tr = dt + datetime.timedelta(hours=3)
            match_time = dt_tr.strftime("%H:%M")
        except:
            match_time = "?"

        # Predictions API (dakikalık limit koruması)
        time.sleep(API_BEKLEME)
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

            over25, over35, btts = poisson_probs(home_exp, away_exp)

            analyzed.append({
                "home": home,
                "away": away,
                "league": league_name,
                "time": match_time,
                "over25": over25,
                "over35": over35,
                "btts": btts,
                "xg_ev": home_exp,
                "xg_dep": away_exp
            })

    if not analyzed:
        send_telegram("ℹ️ Bugün analiz edilecek uygun maç bulunamadı.")
        return

    # 4) 2.5 Üst'e göre sırala
    analyzed.sort(key=lambda x: x["over25"], reverse=True)

    # 5) Gollü maçları filtrele
    gollu_maclar = [m for m in analyzed if m["over25"] >= GOLLU_ESIK or m["btts"] >= GOLLU_ESIK]

    # 6) Özet mesaj
    ozet = f"📊 <b>SKORLAB · GÜNLÜK GOL SİNYALİ</b>\n"
    ozet += f"📅 {today}\n"
    ozet += f"🔍 Taranan: {len(analyzed)} maç\n"
    ozet += f"🔥 Gollü aday: {len(gollu_maclar)} maç\n\n"

    if not gollu_maclar:
        ozet += "ℹ️ Bugün belirgin gollü maç yok.\n\n"
        ozet += "📋 En yüksek gol ihtimalli 5 maç:\n\n"
        for idx, m in enumerate(analyzed[:5], 1):
            ozet += f"{idx}. <b>{m['home']} - {m['away']}</b>\n"
            ozet += f"   🏆 {m['league']} · 🕐 {m['time']}\n"
            ozet += f"   ⚽ 2.5Ü: %{m['over25']:.1f} | 🤝 KGV: %{m['btts']:.1f}\n\n"
        send_telegram(ozet)
        return

    ozet += "🔥 <b>GOL POTANSİYELİ YÜKSEK MAÇLAR:</b>\n\n"

    for idx, m in enumerate(gollu_maclar[:10], 1):
        # Emoji belirleme
        if m["over25"] >= 75:
            emoji = "🔥🔥🔥"
        elif m["over25"] >= 68:
            emoji = "🔥🔥"
        else:
            emoji = "🔥"

        ozet += f"{emoji} <b>{m['home']} - {m['away']}</b>\n"
        ozet += f"🏆 {m['league']} · 🕐 {m['time']}\n"
        ozet += f"⚽ <b>2.5 Üst: %{m['over25']:.1f}</b>\n"
        ozet += f"🤝 <b>KG Var: %{m['btts']:.1f}</b>\n"
        ozet += f"🎯 3.5 Üst: %{m['over35']:.1f}\n"
        ozet += f"📊 xG: {m['xg_ev']:.2f} - {m['xg_dep']:.2f}\n\n"

    send_telegram(ozet)
    print(f"✅ {len(gollu_maclar)} gollü maç gönderildi.")


if __name__ == "__main__":
    main()
