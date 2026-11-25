"""主流程：抓股價 + 新聞 -> 評分 -> 產出建議。"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, indicators, news


def fetch_prices(symbols: list[str]) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = yf.Ticker(sym).history(period=config.PRICE_HISTORY, interval="1d", auto_adjust=True)
            df = df.dropna(subset=["Close"])
            if len(df) >= 30:
                out[sym] = df
            else:
                print(f"[price] {sym} 資料不足（{len(df)} 筆）")
        except Exception as e:
            print(f"[price] {sym} 抓取失敗: {e}")
    return out


def rate(score: float) -> str:
    for th, label in config.RATING_THRESHOLDS:
        if score >= th:
            return label
    return config.RATING_THRESHOLDS[-1][1]


def news_query_for(symbol: str, name: str, market: str) -> str:
    if market == "TW":
        return f"{name} {symbol.split('.')[0]}"
    return f"{name} stock" if name.upper() != symbol else f"{symbol} stock"


def analyze(prices: dict | None = None, news_fetcher=news.fetch) -> dict:
    """prices 可傳入預先準備好的資料（測試/離線用），否則即時抓取。"""
    w = config.WEIGHTS
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "markets": {},
    }

    all_syms = []
    for m in config.MARKETS.values():
        all_syms += [m["index"], *m["watchlist"].keys()]
    if prices is None:
        prices = fetch_prices(all_syms)

    for code, m in config.MARKETS.items():
        # --- 國家 / 總體新聞 ---
        macro_items = []
        for q in m["news_queries"]:
            macro_items += news_fetcher(q, m["news_lang"], config.NEWS_PER_QUERY)
        macro_items = news.dedupe(macro_items)
        macro_score = news.aggregate(macro_items)

        # --- 大盤趨勢 ---
        idx_df = prices.get(m["index"])
        if idx_df is not None:
            idx_ind = indicators.compute(idx_df)
            idx_score, idx_reasons = indicators.score(idx_ind)
        else:
            idx_ind, idx_score, idx_reasons = {}, 0.0, ["大盤資料缺失"]

        market_score = 0.6 * idx_score + 0.4 * macro_score
        mk = {
            "name": m["name"],
            "currency": m["currency"],
            "index": {
                "symbol": m["index"], "name": m["index_name"],
                "price": idx_ind.get("price"), "change_pct": idx_ind.get("change_pct"),
                "ret_20d": idx_ind.get("ret_20d"),
                "trend_score": round(idx_score, 3), "reasons": idx_reasons,
            },
            "macro_sentiment": round(macro_score, 3),
            "market_score": round(market_score, 3),
            "market_view": _market_view(market_score),
            "headlines": sorted(macro_items, key=lambda x: x["age_hours"])[:12],
            "stocks": [],
        }

        # --- 個股 ---
        for sym, name in m["watchlist"].items():
            df = prices.get(sym)
            if df is None:
                continue
            ind = indicators.compute(df)
            tech, reasons = indicators.score(ind)
            s_items = news.dedupe(news_fetcher(news_query_for(sym, name, code), m["news_lang"], 10))
            s_news = news.aggregate(s_items)

            total = (w["technical"] * tech + w["stock_news"] * s_news
                     + w["macro_news"] * macro_score + w["market_trend"] * idx_score)
            total = float(np.clip(total, -1, 1))

            if s_news >= 0.25:
                reasons.append(f"個股新聞偏正面（{s_news:+.2f}）")
            elif s_news <= -0.25:
                reasons.append(f"個股新聞偏負面（{s_news:+.2f}）")
            if macro_score >= 0.2:
                reasons.append("國家總體新聞氣氛偏多")
            elif macro_score <= -0.2:
                reasons.append("國家總體新聞氣氛偏空")

            mk["stocks"].append({
                "symbol": sym, "name": name,
                "price": _r(ind["price"], 2), "change_pct": _r(ind["change_pct"], 2),
                "ret_5d": _r(ind["ret_5d"], 2), "ret_20d": _r(ind["ret_20d"], 2),
                "rsi14": _r(ind["rsi14"], 1), "volatility": _r(ind["volatility_20d"], 1),
                "sma20": _r(ind["sma20"], 2), "sma50": _r(ind["sma50"], 2),
                "technical_score": round(tech, 3), "news_score": round(s_news, 3),
                "score": round(total, 3), "rating": rate(total),
                "confidence": _confidence(tech, s_news, macro_score, len(s_items)),
                "reasons": reasons[:6],
                "news": sorted(s_items, key=lambda x: x["age_hours"])[:5],
                "spark": [round(float(x), 2) for x in df["Close"].iloc[-60:]],
            })
        mk["stocks"].sort(key=lambda s: s["score"], reverse=True)
        result["markets"][code] = mk
    return result


def _r(v, n):
    return None if v is None else round(v, n)


def _market_view(s: float) -> str:
    if s >= 0.3:
        return "偏多：可適度提高持股"
    if s >= 0.05:
        return "中性偏多：逢回分批布局"
    if s > -0.05:
        return "中性：維持現有部位"
    if s > -0.3:
        return "中性偏空：控制持股、設好停損"
    return "偏空：降低持股、保留現金"


def _confidence(tech: float, news_s: float, macro: float, n_news: int) -> str:
    """各訊號方向一致且有足夠新聞時，信心較高。"""
    signs = [np.sign(x) for x in (tech, news_s, macro) if abs(x) > 0.05]
    agree = abs(sum(signs)) == len(signs) and len(signs) >= 2
    if agree and abs(tech) > 0.4 and n_news >= 3:
        return "高"
    if agree or abs(tech) > 0.5:
        return "中"
    return "低"
