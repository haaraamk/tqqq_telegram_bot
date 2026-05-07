import os
import pytz
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

STOP_LOSS    = -0.40
TAKE_PROFIT  =  1.00
AVG_PRICE    = 0.0
HOLDINGS     = 0.0


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("텔레그램 전송 완료")
        else:
            print(f"전송 실패: {res.text}")
    except Exception as e:
        print(f"전송 오류: {e}")


def get_signal():
    tqqq_raw = yf.download("TQQQ", period="200d", auto_adjust=True, progress=False)
    qqq_raw  = yf.download("QQQ",  period="200d", auto_adjust=True, progress=False)

    if isinstance(tqqq_raw.columns, pd.MultiIndex):
        tqqq_raw.columns = tqqq_raw.columns.get_level_values(0)
    if isinstance(qqq_raw.columns, pd.MultiIndex):
        qqq_raw.columns = qqq_raw.columns.get_level_values(0)

    tqqq = tqqq_raw["Close"].dropna()
    qqq  = qqq_raw["Close"].dropna()

    ma5  = tqqq.rolling(5).mean()
    ma20 = tqqq.rolling(20).mean()
    ma60 = tqqq.rolling(60).mean()

    today      = tqqq.index[-1]
    price_tqqq = float(tqqq.iloc[-1])
    price_qqq  = float(qqq.iloc[-1])
    val_ma5    = float(ma5.iloc[-1])
    val_ma20   = float(ma20.iloc[-1])
    val_ma60   = float(ma60.iloc[-1])
    chg_tqqq   = (price_tqqq - float(tqqq.iloc[-2])) / float(tqqq.iloc[-2]) * 100
    chg_qqq    = (price_qqq  - float(qqq.iloc[-2]))  / float(qqq.iloc[-2])  * 100

    buy_signal = (val_ma5 < val_ma20) and (val_ma20 < val_ma60)

    sl_signal = False
    tp_signal = False
    pnl_rate  = 0.0
    if AVG_PRICE > 0 and HOLDINGS > 0:
        pnl_rate  = (price_tqqq - AVG_PRICE) / AVG_PRICE
        sl_signal = pnl_rate <= STOP_LOSS
        tp_signal = pnl_rate >= TAKE_PROFIT

    return {
        "date":       today.strftime("%Y-%m-%d"),
        "price_tqqq": price_tqqq,
        "price_qqq":  price_qqq,
        "chg_tqqq":   chg_tqqq,
        "chg_qqq":    chg_qqq,
        "ma5":        val_ma5,
        "ma20":       val_ma20,
        "ma60":       val_ma60,
        "buy_signal": buy_signal,
        "sl_signal":  sl_signal,
        "tp_signal":  tp_signal,
        "pnl_rate":   pnl_rate * 100,
    }


def build_message(s: dict) -> str:
    now = datetime.now(pytz.timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")

    if s["sl_signal"]:
        signal = "SELL ALL - Stop Loss"
    elif s["tp_signal"]:
        signal = "SELL 50% - Take Profit"
    elif s["buy_signal"]:
        signal = "BUY - 50만원"
    else:
        signal = "WAIT - QQQ 보유"

    tqqq_sign = "+" if s["chg_tqqq"] >= 0 else ""
    qqq_sign  = "+" if s["chg_qqq"]  >= 0 else ""

    return (
        f"[TQQQ Bot] {now}\n"
        f"신호: {signal}\n\n"
        f"TQQQ: ${s['price_tqqq']:.2f} ({tqqq_sign}{s['chg_tqqq']:.2f}%)\n"
        f"QQQ:  ${s['price_qqq']:.2f} ({qqq_sign}{s['chg_qqq']:.2f}%)\n\n"
        f"MA5:  ${s['ma5']:.2f}\n"
        f"MA20: ${s['ma20']:.2f}\n"
        f"MA60: ${s['ma60']:.2f}\n"
    )

def test_send():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "test"
    }, timeout=10)
    print(res.text)

if __name__ == "__main__":
    test_send()

def main():
    print("신호 계산 중...")
    try:
        signal = get_signal()
        print(f"날짜: {signal['date']}")
        print(f"TQQQ: ${signal['price_tqqq']:.2f} ({signal['chg_tqqq']:+.2f}%)")
        print(f"MA5={signal['ma5']:.2f} / MA20={signal['ma20']:.2f} / MA60={signal['ma60']:.2f}")
        print(f"매수={signal['buy_signal']} / 손절={signal['sl_signal']} / 익절={signal['tp_signal']}")
        send_telegram(build_message(signal))
    except Exception as e:
        send_telegram(f"TQQQ 봇 오류: {str(e)}")
        print(f"오류: {e}")

if __name__ == "__main__":
    main()
