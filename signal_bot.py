from flask import Flask, request, jsonify
import requests, os
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

DEFAULT_SL_USD = float(os.getenv("DEFAULT_SL_USD","1.50"))
DEFAULT_R_MULTIPLIER_TP = float(os.getenv("DEFAULT_R_MULTIPLIER_TP","2.0"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS","300"))

app = Flask(__name__)
_last = {}

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=10)
    r.raise_for_status()

def fmt(x): 
    return f"{float(x):.2f}"

def cooldown(symbol, side):
    last = _last.get((symbol, side))
    if not last: 
        return False
    return (datetime.now()-last).total_seconds() < COOLDOWN_SECONDS

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol","XAUUSD")
    side = str(data.get("side","")).upper().strip()
    price = data.get("price", None)
    tf = str(data.get("tf","1m"))
    strategy = data.get("strategy","TV Signal")
    note = data.get("note","")

    if side not in ("BUY","SELL") or price is None:
        return jsonify({"ok": False}), 400

    if cooldown(symbol, side):
        return jsonify({"ok": True, "skipped": True}), 200

    price = float(price)
    sl = float(data.get("sl", price-DEFAULT_SL_USD if side=="BUY" else price+DEFAULT_SL_USD))
    r = abs(price-sl)
    tp = float(data.get("tp", price + r*DEFAULT_R_MULTIPLIER_TP if side=="BUY" else price - r*DEFAULT_R_MULTIPLIER_TP))
    rr = abs(tp-price)/max(abs(price-sl),1e-9)

    msg = (
        f"📌 <b>{symbol}</b> | TF: <b>{tf}</b>\n"
        f"🎯 <b>{strategy}</b>\n\n"
        f"🟢 <b>{side}</b>\n"
        f"Entrada: <b>{fmt(price)}</b>\n"
        f"SL: <b>{fmt(sl)}</b>\n"
        f"TP: <b>{fmt(tp)}</b>\n"
        f"R: <b>{fmt(rr)}R</b>\n"
    )
    if note: 
        msg += f"\n📝 {note}"

    send_telegram(msg)
    _last[(symbol, side)] = datetime.now()
    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def home():
    return "OK", 200
