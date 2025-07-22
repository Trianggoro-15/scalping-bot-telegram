# SCALPING + INTRADAY + SWING MULTI-MODE BOT v2.0
import os
import requests
import json
from datetime import datetime, timezone
from time import sleep
import statistics

FINNHUB_KEY = os.getenv("FINNHUB_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RISK_PER_TRADE = 0.01  # 1% risk
ACCOUNT_BALANCE = 100000  # simulasi balance untuk kalkulasi lot
MODE = 'scalping'  # scalping, intraday, swing
LOG_FILE = "signal_log.json"

# Config mode setting
MODE_CONFIG = {
    "scalping": {
        "tf": "1",
        "htf": "15",
        "window": 15
    },
    "intraday": {
        "tf": "15",
        "htf": "60",
        "window": 40
    },
    "swing": {
        "tf": "60",
        "htf": "240",
        "window": 80
    },
}


# ===================== DATA =====================
def get_candle_data(tf: str, count: int):
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:XAU_USD",
        "resolution": tf,
        "count": count,
        "token": FINNHUB_KEY
    }
    res = requests.get(url, params=params)
    return res.json() if res.status_code == 200 else {}


# ===================== UTILS =====================
def now_utc():
    return datetime.now(timezone.utc)


def send_alert(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)


def log_signal(entry):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Logging error: {e}")


# ===================== SMC UTAMA =====================
def detect_sweep(data):
    h, l = data["h"], data["l"]
    return (l[-1] < l[-2], "sell-side") if l[-1] < l[-2] else (
        h[-1] > h[-2], "buy-side") if h[-1] > h[-2] else (False, "")


def detect_choch(data):
    o, c = data["o"], data["c"]
    prev = "bull" if c[-3] > o[-3] else "bear"
    last = "bull" if c[-2] > o[-2] else "bear"
    now = "bull" if c[-1] > o[-1] else "bear"
    return (prev == last and now != last)


def detect_bos(htf):
    return htf["c"][-1] > htf["h"][-3] if htf["c"][-2] < htf["h"][-3] else False


def detect_micro_bos(data):
    return data["h"][-1] > data["h"][-3] and data["l"][-1] > data["l"][-3]


def get_orderblock(data):
    o, c = data["o"], data["c"]
    for i in range(len(o) - 3, 0, -1):
        if c[i] != o[i]:
            return (min(o[i], c[i]), max(o[i], c[i]))
    return None, None


def detect_fvg(data):
    h, l = data["h"], data["l"]
    return [(h[i], l[i + 2]) for i in range(len(h) - 2) if h[i] < l[i + 2]] + [
        (h[i + 2], l[i]) for i in range(len(h) - 2) if l[i] > h[i + 2]
    ]


def in_zone(price, zones):
    return any(low <= price <= high for low, high in zones)


def is_engulfing(o, c):
    return abs(c - o) > 0.5 * max(o, c)


def wick_ratio(o, c, h, l):
    wick_top = h - max(o, c)
    wick_bot = min(o, c) - l
    body = abs(c - o)
    return max(wick_top, wick_bot) / body if body > 0 else 99


def volume_spike(vol):
    return vol[-1] > statistics.mean(vol[-6:-1]) * 1.3


def eqh_eql_target(data):
    h, l = data["h"], data["l"]
    eqh = max(h[:-2])
    eql = min(l[:-2])
    return eqh, eql


def atr(data):
    h, l, c = data["h"], data["l"], data["c"]
    return statistics.mean([h[i] - l[i] for i in range(-6, -1)])


# ===================== MAIN =====================
if __name__ == "__main__":
    while True:
        try:
            config = MODE_CONFIG[MODE]
            tf = config["tf"]
            htf = config["htf"]
            data = get_candle_data(tf, config["window"])
            htf_data = get_candle_data(htf, 40)

            if data.get("s") != "ok":
                sleep(60)
                continue

            price = data["c"][-1]
            ob_low, ob_high = get_orderblock(data)
            fvg = detect_fvg(data)
            in_ob = ob_low and ob_high and ob_low <= price <= ob_high
            in_fvg = in_zone(price, fvg)
            eqh, eql = eqh_eql_target(data)
            sl = atr(data)
            tp = eqh if price < eqh else eql
            rr = abs(tp - price) / sl if sl > 0 else 0
            vol = volume_spike(data.get("v", [1] * 10))

            if all([
                    detect_sweep(data)[0],
                    detect_choch(data),
                    detect_micro_bos(data),
                    detect_bos(htf_data), (in_ob or in_fvg),
                    wick_ratio(data["o"][-1], data["c"][-1], data["h"][-1],
                               data["l"][-1]) < 3,
                    is_engulfing(data["o"][-1], data["c"][-1]), vol, rr >= 2
            ]):
                signal = {
                    "time": str(now_utc()),
                    "price": price,
                    "mode": MODE,
                    "tp": tp,
                    "sl": sl,
                    "rr": rr,
                    "area": "OB" if in_ob else "FVG"
                }
                send_alert(
                    f"🚨 VALID SETUP [XAUUSD TF:{tf}M] – Mode: {MODE.upper()}\nPrice: {price}\nArea: {signal['area']}\nRR: {round(rr, 2)}\nTP: {tp} | SL: {round(sl, 2)}"
                )
                log_signal(signal)
                print(f"✅ Sinyal {MODE} terkirim: {price}")
            else:
                print(f"[{now_utc()}] ⏸️ Belum valid ({MODE})")
        except Exception as e:
            print(f"❌ Error: {e}")
        sleep(60)
