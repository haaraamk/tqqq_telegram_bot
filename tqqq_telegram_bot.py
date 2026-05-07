"""
TQQQ+QQQ 전략 텔레그램 알림 봇
- 매일 미국 장 마감 후 (한국시간 새벽 6:30) 자동 실행
- 매수/손절/익절/관망 신호 텔레그램으로 전송
- GitHub Actions 또는 로컬 cron으로 실행 가능

설치:
    pip install yfinance requests pandas
"""

import os
import pytz
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 전략 파라미터
STOP_LOSS    = -0.40   # 손절 기준
TAKE_PROFIT  =  1.00   # 익절 기준
AVG_PRICE    = 0.0     # ← 실제 보유 중인 TQQQ 평균단가 입력 (없으면 0)
HOLDINGS     = 0.0     # ← 실제 보유 TQQQ 수량 입력 (없으면 0)


# ════════════════════════════════════════════
# ② 텔레그램 전송 함수
# ════════════════════════════════════════════
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


# ════════════════════════════════════════════
# ③ 데이터 수집 및 신호 계산
# ════════════════════════════════════════════
def get_signal():
    # 최근 200일 데이터 다운로드
    tqqq_raw = yf.download("TQQQ", period="200d", auto_adjust=True, progress=False)
    qqq_raw  = yf.download("QQQ",  period="200d", auto_adjust=True, progress=False)

    # 멀티인덱스 처리
    if isinstance(tqqq_raw.columns, pd.MultiIndex):
        tqqq_raw.columns = tqqq_raw.columns.get_level_values(0)
    if isinstance(qqq_raw.columns, pd.MultiIndex):
        qqq_raw.columns = qqq_raw.columns.get_level_values(0)

    tqqq = tqqq_raw["Close"].dropna()
    qqq  = qqq_raw["Close"].dropna()

    # 이평선 계산
    ma5  = tqqq.rolling(5).mean()
    ma20 = tqqq.rolling(20).mean()
    ma60 = tqqq.rolling(60).mean()

    # 최신 값
    today        = tqqq.index[-1]
    price_tqqq   = float(tqqq.iloc[-1])
    price_qqq    = float(qqq.iloc[-1])
    val_ma5      = float(ma5.iloc[-1])
    val_ma20     = float(ma20.iloc[-1])
    val_ma60     = float(ma60.iloc[-1])

    # 전일 대비 등락
    chg_tqqq = (price_tqqq - float(tqqq.iloc[-2])) / float(tqqq.iloc[-2]) * 100
    chg_qqq  = (price_qqq  - float(qqq.iloc[-2]))  / float(qqq.iloc[-2])  * 100

    # ── 신호 판단 ──
    buy_signal  = (val_ma5 < val_ma20) and (val_ma20 < val_ma60)

    # 손절/익절 (보유 중인 경우만)
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


# ════════════════════════════════════════════
# ④ 메시지 생성
# ════════════════════════════════════════════
def build_message(s: dict) -> str:
    now = datetime.now(pytz.timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")

    if s["sl_signal"]:
        signal_line = "🔴 [손절 신호] TQQQ 전량 매도 → QQQ 전환"
    elif s["tp_signal"]:
        signal_line = "⭐ [익절 신호] TQQQ 50% 매도 → QQQ 이동"
    elif s["buy_signal"]:
        signal_line = "🟢 [매수 신호] TQQQ 50만원 분할매수"
    else:
        signal_line = "⚪ [관망] 신호 없음 — QQQ 보유 유지"

    if s["ma5"] < s["ma20"] < s["ma60"]:
        ma_status = "🔽 역배열 (MA5 < MA20 < MA60)"
    elif s["ma5"] > s["ma20"] > s["ma60"]:
        ma_status = "🔼 정배열 (MA5 > MA20 > MA60)"
    else:
        ma_status = "↔️ 혼조"

    tqqq_emoji = "📈" if s["chg_tqqq"] >= 0 else "📉"
    qqq_emoji  = "📈" if s["chg_qqq"]  >= 0 else "📉"

    return (
        f"📊 TQQQ+QQQ 전략 일일 리포트\n"
        f"🕕 {now} (KST)\n"
        f"----------------\n"
        f"{signal_line}\n"
        f"----------------\n"
        f"💹 시세\n"
        f"  {tqqq_emoji} TQQQ: ${s['price_tqqq']:.2f} ({s['chg_tqqq']:+.2f}%)\n"
        f"  {qqq_emoji} QQQ:  ${s['price_qqq']:.2f} ({s['chg_qqq']:+.2f}%)\n"
        f"\n"
        f"📐 이동평균선\n"
        f"  MA5:  ${s['ma5']:.2f}\n"
        f"  MA20: ${s['ma20']:.2f}\n"
        f"  MA60: ${s['ma60']:.2f}\n"
        f"  상태: {ma_status}\n"
        f"----------------\n"
        f"📌 전략 기준\n"
        f"  매수: MA5 < MA20 < MA60\n"
        f"  손절: 평균단가 -40%\n"
        f"  익절: 평균단가 +100% → 50% 매도\n"
        f"----------------\n"
        f"⚠️ 교육용 시뮬레이션 / 투자 권유 아님"
    )


# ════════════════════════════════════════════
# ⑤ 메인 실행
# ════════════════════════════════════════════
def main():
    print("신호 계산 중...")
    try:
        signal = get_signal()
        print(f"날짜: {signal['date']}")
        print(f"TQQQ: ${signal['price_tqqq']:.2f} ({signal['chg_tqqq']:+.2f}%)")
        print(f"MA 상태: MA5={signal['ma5']:.2f} / MA20={signal['ma20']:.2f} / MA60={signal['ma60']:.2f}")
        print(f"매수신호: {signal['buy_signal']} / 손절: {signal['sl_signal']} / 익절: {signal['tp_signal']}")

        msg = build_message(signal)
        print("\n전송할 메시지:")
        print(msg)
        send_telegram(msg)

    except Exception as e:
        err_msg = f"⚠️ TQQQ 봇 오류 발생\n{str(e)}"
        send_telegram(err_msg)
        print(f"오류: {e}")

if __name__ == "__main__":
    main()
