import os, requests
from datetime import datetime
import pytz, yfinance as yf, pandas as pd

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def main():
    raw = yf.download("TQQQ", period="200d", auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    close = raw["Close"].dropna()
    ma5  = float(close.rolling(5).mean().iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma60 = float(close.rolling(60).mean().iloc[-1])
    price = float(close.iloc[-1])
    now = datetime.now(pytz.timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    signal = "매수신호" if ma5 < ma20 < ma60 else "관망"
    msg = now + "\n신호: " + signal + "\nTQQQ: " + str(round(price,2)) + "\nMA5: " + str(round(ma5,2)) + "\nMA20: " + str(round(ma20,2)) + "\nMA60: " + str(round(ma60,2))
    res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    print(res.text)

if __name__ == "__main__":
    main()
