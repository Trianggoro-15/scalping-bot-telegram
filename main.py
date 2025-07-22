import os
import requests
from datetime import datetime
from time import sleep

# === Konfigurasi dari Railway ===
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# Ambil data 1M XAUUSD (5 candle terakhir)
def get_xauusd_1m():
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:XAU_USD",
        "resolution": "1",
        "count": 5,
        "token": FINNHUB_KEY
    }
    response = requests.get(url, params=params)
    return response.json()


# Kirim alert ke Telegram
def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)


# Cek apakah terjadi sweep liquidity (candle terakhir break low/high sebelumnya)
def detect_liquidity_sweep(data):
    h, l = data["h"], data["l"]
    if len(h) < 2:
        return False, ""

    prev_high, last_high = h[-2], h[-1]
    prev_low, last_low = l[-2], l[-1]

    if last_high > prev_high:
        return True, "buy-side liquidity sweep"
    elif last_low < prev_low:
        return True, "sell-side liquidity sweep"
    return False, ""


# Deteksi CHoCH sederhana (reversal mikro)
def detect_choch(data):
    o, c = data["o"], data["c"]
    if len(o) < 3:
        return False

    # Deteksi dari dua candle terakhir
    prev_dir = "bull" if c[-3] > o[-3] else "bear"
    last_dir = "bull" if c[-2] > o[-2] else "bear"
    now_dir = "bull" if c[-1] > o[-1] else "bear"

    # Contoh: dua candle sebelumnya turun, sekarang candle naik → CHoCH
    if prev_dir == "bear" and last_dir == "bear" and now_dir == "bull":
        return True
    if prev_dir == "bull" and last_dir == "bull" and now_dir == "bear":
        return True
    return False


# Jam killzone saja


def is_killzone():
    now_utc = datetime.utcnow()
    hour = now_utc.hour
    return (6 <= hour < 8) or (12 <= hour < 14)  # WIB = UTC+7


# Loop utama
if __name__ == "__main__":
    while True:
        try:
            if is_killzone():
                data = get_xauusd_1m()
                if data["s"] != "ok":
                    print("❌ Data error dari Finnhub")
                    continue

                sweep_ok, sweep_type = detect_liquidity_sweep(data)
                choch_ok = detect_choch(data)

                if sweep_ok and choch_ok:
                    price = data["c"][-1]
                    send_alert(
                        f"🚨 SCALPING SETUP VALID (XAUUSD 1M)\n{ sweep_type } + CHoCH terdeteksi\nHarga: {price}"
                    )
                print(
                    f"[{datetime.now()}] ✅ Cek struktur selesai (killzone aktif)"
                )
            else:
                print(f"[{datetime.now()}] ⏸️ Di luar jam killzone")

        except Exception as e:
            print(f"❌ Error: {e}")

        sleep(60)
