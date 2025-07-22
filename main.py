import os
import requests
from datetime import datetime
from time import sleep

FINNHUB_KEY = os.getenv("FINNHUB_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# Ambil candle 1M XAUUSD
def get_xauusd_1m():
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:XAU_USD",
        "resolution": "1",
        "count": 15,
        "token": FINNHUB_KEY
    }
    response = requests.get(url, params=params)
    return response.json()


# Kirim alert ke Telegram
def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)


# Sweep liquidity
def detect_liquidity_sweep(data):
    h, l = data["h"], data["l"]
    if len(h) < 2:
        return False, ""
    if l[-1] < l[-2]:
        return True, "sell-side liquidity sweep"
    if h[-1] > h[-2]:
        return True, "buy-side liquidity sweep"
    return False, ""


# CHoCH sederhana
def detect_choch(data):
    o, c = data["o"], data["c"]
    if len(o) < 3:
        return False
    prev_dir = "bull" if c[-3] > o[-3] else "bear"
    last_dir = "bull" if c[-2] > o[-2] else "bear"
    now_dir = "bull" if c[-1] > o[-1] else "bear"
    return (prev_dir == last_dir and now_dir != last_dir)


# Orderblock deteksi


def get_last_orderblock(data):
    o, c = data["o"]
    for i in range(len(o) - 3, 0, -1):
        direction = "bear" if c[i] < o[i] else "bull"
        return (min(o[i], c[i]), max(o[i], c[i]))
    return None, None


def is_touching_orderblock(price, ob_low, ob_high):
    if ob_low is None or ob_high is None:
        return False
    return ob_low <= price <= ob_high


# Deteksi FVG biasa dan IFVG (inverse)
def detect_fvg(data):
    h, l = data["h"], data["l"]
    fvg_zones = []
    for i in range(len(h) - 2):
        if h[i] < l[i + 2]:  # Bullish FVG
            fvg_zones.append((h[i], l[i + 2]))
        if l[i] > h[i + 2]:  # Bearish FVG
            fvg_zones.append((h[i + 2], l[i]))
    return fvg_zones


def is_price_in_fvg(price, fvg_zones):
    for zone in fvg_zones:
        if zone[0] <= price <= zone[1]:
            return True
    return False


# RR filter


def rr_valid(entry, sl, target):
    if sl == 0:
        return False
    rr = abs(target - entry) / abs(sl)
    return rr >= 2


# Killzone waktu aktif bot


def is_killzone():
    hour = datetime.utcnow().hour
    return (6 <= hour < 8) or (12 <= hour < 14)


# Main loop
if __name__ == "__main__":
    while True:
        try:
            if is_killzone():
                data = get_xauusd_1m()
                if data["s"] != "ok":
                    continue

                price = data["c"][-1]
                sweep_ok, sweep_type = detect_liquidity_sweep(data)
                choch_ok = detect_choch(data)
                ob_low, ob_high = get_last_orderblock(data)
                ob_ok = is_touching_orderblock(price, ob_low, ob_high)
                fvg_zones = detect_fvg(data)
                fvg_ok = is_price_in_fvg(price, fvg_zones)

                # SL dan TP dummy (simulasi RR)
                sl = abs(price - ob_low) if ob_low else 0
                tp = abs(price - data["h"][-2])  # target = high sebelumnya

                if sweep_ok and choch_ok and (ob_ok or fvg_ok) and rr_valid(
                        price, sl, tp):
                    send_alert(
                        f"🚨 VALID SETUP [XAUUSD 1M]\n{sweep_type} + CHoCH\nPrice: {price}\nArea: {'OB' if ob_ok else 'FVG'}\nRR: >= 1:2"
                    )
                print(f"[{datetime.now()}] ✅ Cek struktur (Killzone)")
            else:
                print(f"[{datetime.now()}] ⏸️ Di luar killzone")
        except Exception as e:
            print(f"❌ Error: {e}")
        sleep(60)
