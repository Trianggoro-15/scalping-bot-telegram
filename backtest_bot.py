# backtest_bot.py
import json
import statistics

# ===================== LOAD DATA HISTORIS =====================
# Format file harus JSON dengan key: o, h, l, c, v (open, high, low, close, volume)
with open("historical_data.json", "r") as f:
    data = json.load(f)


# ===================== FUNGSI SMC =====================
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


def detect_bos(data):
    return data["c"][-1] > data["h"][-3] if data["c"][-2] < data["h"][
        -3] else False


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


# ===================== BACKTEST LOOP =====================
window = 20  # jumlah candle yang dianalisis per loop
signals = []

for i in range(window, len(data["c"])):
    slice_data = {
        "o": data["o"][i - window:i],
        "h": data["h"][i - window:i],
        "l": data["l"][i - window:i],
        "c": data["c"][i - window:i],
        "v": data["v"][i - window:i],
    }
    price = slice_data["c"][-1]
    ob_low, ob_high = get_orderblock(slice_data)
    fvg = detect_fvg(slice_data)
    in_ob = ob_low and ob_high and ob_low <= price <= ob_high
    in_fvg = in_zone(price, fvg)
    eqh, eql = eqh_eql_target(slice_data)
    sl = atr(slice_data)
    tp = eqh if price < eqh else eql
    rr = abs(tp - price) / sl if sl > 0 else 0
    vol = volume_spike(slice_data.get("v", [1] * 10))
    if all([
            detect_sweep(slice_data)[0],
            detect_choch(slice_data),
            detect_micro_bos(slice_data),
            detect_bos(slice_data), (in_ob or in_fvg),
            wick_ratio(slice_data["o"][-1], slice_data["c"][-1],
                       slice_data["h"][-1], slice_data["l"][-1]) < 3,
            is_engulfing(slice_data["o"][-1], slice_data["c"][-1]), vol, rr
            >= 2
    ]):
        signal = {
            "index": i,
            "price": price,
            "tp": tp,
            "sl": sl,
            "rr": rr,
            "area": "OB" if in_ob else "FVG"
        }
        signals.append(signal)
        print(f"✅ Sinyal pada index {i} | Price: {price} | RR: {round(rr, 2)}")

# ===================== SIMPAN HASIL =====================
with open("backtest_signals.json", "w") as f:
    json.dump(signals, f, indent=2)

print(f"\n🎯 Total sinyal ditemukan: {len(signals)}")
