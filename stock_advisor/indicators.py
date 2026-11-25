"""技術指標與技術面評分。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def compute(df: pd.DataFrame) -> dict:
    """輸入含 Close/Volume 的日線資料，回傳最新一筆的指標值。"""
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float) if "Volume" in df else pd.Series(np.nan, index=df.index)

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    std20 = close.rolling(20).std()
    r = rsi(close)
    m_line, m_sig, m_hist = macd(close)

    def last(s):
        v = s.iloc[-1] if len(s) else np.nan
        return None if pd.isna(v) else float(v)

    price = last(close)
    upper = last(sma20 + 2 * std20)
    lower = last(sma20 - 2 * std20)
    vol20 = last(volume.rolling(20).mean())

    return {
        "price": price,
        "change_pct": _pct(close, 1),
        "ret_5d": _pct(close, 5),
        "ret_20d": _pct(close, 20),
        "ret_60d": _pct(close, 60),
        "sma20": last(sma20),
        "sma50": last(sma50),
        "sma200": last(sma200),
        "rsi14": last(r),
        "macd": last(m_line),
        "macd_signal": last(m_sig),
        "macd_hist": last(m_hist),
        "macd_hist_prev": float(m_hist.iloc[-2]) if len(m_hist) > 1 else None,
        "bb_upper": upper,
        "bb_lower": lower,
        "bb_pos": (price - lower) / (upper - lower) if None not in (price, upper, lower) and upper != lower else None,
        "volume_ratio": (last(volume) / vol20) if vol20 else None,
        "volatility_20d": last(close.pct_change().rolling(20).std() * np.sqrt(252) * 100),
    }


def _pct(close: pd.Series, n: int):
    if len(close) <= n:
        return None
    return float((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100)


def score(ind: dict) -> tuple[float, list[str]]:
    """技術面評分，範圍 -1 ~ +1，並附上中文理由。"""
    pts: list[float] = []
    reasons: list[str] = []
    p = ind["price"]

    # 1. 均線排列（趨勢）
    if ind["sma20"] and ind["sma50"]:
        if p > ind["sma20"] > ind["sma50"]:
            pts.append(1.0); reasons.append("股價站上 20/50 日均線，多頭排列")
        elif p < ind["sma20"] < ind["sma50"]:
            pts.append(-1.0); reasons.append("股價跌破 20/50 日均線，空頭排列")
        elif p > ind["sma50"]:
            pts.append(0.3)
        else:
            pts.append(-0.3)

    # 2. 長期趨勢
    if ind["sma200"]:
        if p > ind["sma200"]:
            pts.append(0.5); reasons.append("位於 200 日均線之上（長多）")
        else:
            pts.append(-0.5); reasons.append("位於 200 日均線之下（長空）")

    # 3. RSI（超買超賣 + 動能）
    r = ind["rsi14"]
    if r is not None:
        if r >= 75:
            pts.append(-0.6); reasons.append(f"RSI {r:.0f} 過熱，留意拉回")
        elif r <= 25:
            pts.append(0.6); reasons.append(f"RSI {r:.0f} 超賣，可能反彈")
        elif 50 <= r < 70:
            pts.append(0.4)
        elif 30 < r < 50:
            pts.append(-0.3)

    # 4. MACD
    h, hp = ind["macd_hist"], ind["macd_hist_prev"]
    if h is not None and hp is not None:
        if h > 0 and hp <= 0:
            pts.append(1.0); reasons.append("MACD 黃金交叉")
        elif h < 0 and hp >= 0:
            pts.append(-1.0); reasons.append("MACD 死亡交叉")
        elif h > 0:
            pts.append(0.5 if h > hp else 0.2)
        else:
            pts.append(-0.5 if h < hp else -0.2)

    # 5. 布林通道
    bb = ind["bb_pos"]
    if bb is not None:
        if bb > 1:
            pts.append(-0.3); reasons.append("突破布林上軌，短線乖離大")
        elif bb < 0:
            pts.append(0.3); reasons.append("跌破布林下軌，短線超跌")

    # 6. 20 日動能
    m = ind["ret_20d"]
    if m is not None:
        pts.append(float(np.clip(m / 10, -1, 1)))
        if abs(m) >= 8:
            reasons.append(f"近 20 日{'上漲' if m > 0 else '下跌'} {abs(m):.1f}%")

    # 7. 量能確認
    vr = ind["volume_ratio"]
    if vr and vr > 1.8 and ind["change_pct"] is not None:
        if ind["change_pct"] > 0:
            pts.append(0.4); reasons.append(f"價漲量增（量比 {vr:.1f}x）")
        else:
            pts.append(-0.4); reasons.append(f"價跌量增（量比 {vr:.1f}x）")

    s = float(np.clip(np.mean(pts), -1, 1)) if pts else 0.0
    return s, reasons
