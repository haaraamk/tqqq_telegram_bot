import os, requests, pytz, yfinance as yf, pandas as pd
from datetime import datetime

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
STOP_LOSS    = -0.40
TAKE_PROFIT  =  1.00
AVG_PRICE    = 0.0   # 실제 보유 TQQQ 평균단가 (없으면 0)
HOLDINGS     = 0.0   # 실제 보유 TQQQ 수량 (없으면 0)

def main():
    raw = yf.download("TQQQ", period="200d", auto_adjust=True, progress=False)
    rq  = yf.download("QQQ",  period="200d", auto_adjust=True, progress=False)
    for r in [raw, rq]:
        if isinstance(r.columns, pd.MultiIndex):
            r.columns = r.columns.get_level_values(0)

    close = raw["Close"].dropna()
    qqq   = rq["Close"].dropna()
    ma5   = float(close.rolling(5).mean().iloc[-1])
    ma20  = float(close.rolling(20).mean().iloc[-1])
    ma60  = float(close.rolling(60).mean().iloc[-1])
    price = float(close.iloc[-1])
    pqqq  = float(qqq.iloc[-1])
    chgt  = (price - float(close.iloc[-2])) / float(close.iloc[-2]) * 100
    chgq  = (pqqq  - float(qqq.iloc[-2]))  / float(qqq.iloc[-2])  * 100
    now   = datetime.now(pytz.timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")

    if ma5 < ma20 < ma60:
        signal = "🟢 매수신호 - TQQQ 50만원 매수"
        ma_st  = "역배열 (매수구간)"
    elif ma5 > ma20 > ma60:
        signal = "⚪ 관망 - QQQ 보유유지"
        ma_st  = "정배열 (상승추세)"
    else:
        signal = "⚪ 관망 - QQQ 보유유지"
        ma_st  = "혼조"

    pnl = ""
    if AVG_PRICE > 0 and HOLDINGS > 0:
        r = (price - AVG_PRICE) / AVG_PRICE * 100
        if r <= STOP_LOSS * 100:
            signal = "🔴 손절 - TQQQ 전량매도"
        elif r >= TAKE_PROFIT * 100:
            signal = "⭐ 익절 - TQQQ 50% 매도"
        pnl = "\n평균단가: $" + str(round(AVG_PRICE,2)) + "\n평가손익: " + str(round(r,1)) + "%"

    te = "+" if chgt >= 0 else ""
    qe = "+" if chgq >= 0 else ""

    msg = (
        "📊 TQQQ 전략 알림 " + now + "\n"
        "신호: " + signal + "\n"
        "---\n"
        "💹 TQQQ: $" + str(round(price,2)) + " (" + te + str(round(chgt,2)) + "%)\n"
        "💹 QQQ:  $" + str(round(pqqq,2))  + " (" + qe + str(round(chgq,2)) + "%)\n"
        "---\n"
        "MA5:  $" + str(round(ma5,2))  + "\n"
        "MA20: $" + str(round(ma20,2)) + "\n"
        "MA60: $" + str(round(ma60,2)) + "\n"
        "상태: " + ma_st +
        pnl + "\n"
    )

    res = requests.post(
        "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
        timeout=10
    )
    print(res.text)

if __name__ == "__main__":
    main()
