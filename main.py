import os
import requests
from datetime import datetime
from time import sleep

# Ambil API KEY dan konfigurasi dari Railway (Environment Variables)
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# Fungsi untuk ambil 5 candle 1M XAUUSD dari Finnhub
def get_xauusd_1m():
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:XAU_USD",
        "resolution": "1",  # candle 1 menit
        "count": 5,  # ambil 5 candle terakhir
        "token": FINNHUB_KEY
    }
    response = requests.get(url, params=params)
    return response.json()


# Kirim pesan alert ke Telegram
def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)


# Cek candle bullish besar sebagai dummy sinyal
def check_bullish_engulfing(data):
    try:
        o, c = data["o"], data["c"]
        if len(o) >= 2:
            prev_open, prev_close = o[-2], c[-2]
            last_open, last_close = o[-1], c[-1]
            if (last_close > last_open) and (last_close > prev_close):
                return True
    except:
        pass
    return False


# Cek apakah sekarang waktu Killzone (13:00–15:00 dan 19:00–21:00 WIB)
def is_killzone():
    now_utc = datetime.utcnow()
    hour = now_utc.hour
    return (6 <= hour < 8) or (12 <= hour < 14)  # WIB = UTC+7


# Loop utama bot
if __name__ == "__main__":
    while True:
        try:
            if is_killzone():
                data = get_xauusd_1m()
                if data["s"] == "ok" and check_bullish_engulfing(data):
                    price = data["c"][-1]
                    send_alert(
                        f"📈 Bullish candle XAUUSD terdeteksi!\nHarga terakhir: {price}"
                    )
                print(f"[{datetime.now()}] ✅ Killzone aktif – data dicek.")
            else:
                print(f"[{datetime.now()}] ⏸️ Di luar jam killzone.")
        except Exception as e:
            print(f"❌ Error: {e}")
        sleep(60)
