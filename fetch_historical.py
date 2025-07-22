import os
import json
import time
import finnhub
from datetime import datetime

# Inisialisasi Finnhub client
client = finnhub.Client(api_key=os.getenv("FINNHUB_KEY"))


def date_to_unix(dt_str):
    return int(datetime.fromisoformat(dt_str).timestamp())


def fetch(symbol, resolution, fr, to):
    return client.forex_candles(symbol, resolution, date_to_unix(fr),
                                date_to_unix(to))


if __name__ == "__main__":
    # Ganti tanggal sesuai kebutuhan kamu
    data = fetch("OANDA:XAU_USD", "1", "2025-06-01", "2025-07-20")

    if data.get("s") != "ok":
        print("❌ Gagal ambil data:", data.get("s"))
    else:
        out = {k: data[k] for k in ["o", "h", "l", "c", "v"]}
        with open("historical_data.json", "w") as f:
            json.dump(out, f, indent=2)
        print(
            f"✅ Data berhasil disimpan ke historical_data.json ({len(out['c'])} candle)"
        )
