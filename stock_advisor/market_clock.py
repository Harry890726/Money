"""股價時間與開收盤狀態。

報價時間取自大盤指數最後一根 1 分鐘 K 線（Yahoo 報價約延遲 15～20 分鐘）；
開收盤狀態依交易所當地時間判斷，若平日已過開盤時間卻沒有當天報價，視為休市（國定假日）。
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")

SESSIONS = {
    #       時區                         盤前開始     開盤          收盤
    "TW": (ZoneInfo("Asia/Taipei"),      time(8, 30), time(9, 0),   time(13, 30)),
    "US": (ZoneInfo("America/New_York"), time(4, 0),  time(9, 30),  time(16, 0)),
}


def status(code: str, quote_time: datetime | None, now: datetime | None = None) -> str:
    """回傳：交易中 / 盤前 / 已收盤 / 休市（週末） / 休市（假日）"""
    tz, pre, open_, close = SESSIONS[code]
    now_l = (now or datetime.now(timezone.utc)).astimezone(tz)
    if now_l.weekday() >= 5:
        return "休市（週末）"
    t = now_l.time()
    has_today = quote_time is not None and quote_time.astimezone(tz).date() == now_l.date()
    if t >= open_ and quote_time is not None and not has_today:
        return "休市（假日）"
    if t < pre:
        return "已收盤"  # 凌晨：仍是前一交易日收盤
    if t < open_:
        return "盤前"
    if t < close:
        return "交易中"
    return "已收盤"


def describe(code: str, quote_time: datetime | None, now: datetime | None = None) -> dict:
    tz = SESSIONS[code][0]
    st = status(code, quote_time, now)
    out = {"status": st, "time": None, "time_taipei": None, "time_local": None}
    if quote_time is not None:
        out["time"] = quote_time.astimezone(timezone.utc).isoformat(timespec="minutes")
        out["time_taipei"] = quote_time.astimezone(TAIPEI).strftime("%m/%d %H:%M")
        out["time_local"] = quote_time.astimezone(tz).strftime("%m/%d %H:%M")
    return out


def last_quote_time(symbol: str) -> datetime | None:
    """抓大盤指數最後一根 1 分鐘 K 線的時間（含延遲）。失敗回傳 None。"""
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="5d", interval="1m")
        if df.empty:
            return None
        ts = df.index[-1].to_pydatetime()
        # 1 分鐘 K 線標記的是開始時間，加 1 分鐘才是該筆報價的結束時間
        from datetime import timedelta
        return ts + timedelta(minutes=1)
    except Exception as e:
        print(f"[quote] {symbol} 報價時間取得失敗: {e}")
        return None
