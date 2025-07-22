import os
import requests
from datetime import datetime
from time import sleep

# API KEY dan Chat ID dari Railway Variables
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# Ambil data 1M candle dari Finnhub
def get_xauusd_1m():
    url = f"https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:XAU_USD",
        "resolution": "1",
        "count": 5,  # ambil 5 candle terakhir
        "token": FINNHUB_KEY
    }
    res = requests.get(url, params=params)
    return res.json()


# Kirim alert ke Telegram
def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)


# Cek apakah ada candle bullish besar (dummy logic untuk testing)
def check_bullish_engulfing(data):
    o, c = data["o"], data["c"]
    if len(o) >= 2:
        prev_open, prev_close = o[-2], c[-2]
        last_open, last_close = o[-1], c[-1]
        if (last_close > last_open) and (last_close > prev_close):
            return True
    return False


# Loop utama
if __name__ == "__main__":
    while True:
        try:
            data = get_xauusd_1m()
            if data["s"] == "ok" and check_bullish_engulfing(data):
                price = data["c"][-1]
                send_alert(
                    f"📈 Bullish candle XAUUSD terdeteksi!\nHarga terakhir: {price}"
                )
            print(f"[{datetime.now()}] Checked. Status: {data['s']}")
        except Exception as e:
            print(f"Error: {e}")
        sleep(60)  # cek setiap 1 menit
