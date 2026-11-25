"""離線示範資料：隨機漫步股價 + 範例新聞，用於測試與預覽版面。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, news

_SAMPLE = {
    "TW": ["台股大漲創新高 外資買超", "台積電營收優於預期", "央行維持利率不變", "關稅疑慮 電子股走弱", "AI 伺服器訂單滿 廣達看好"],
    "US": ["Stocks rally as Fed signals rate cut", "Nvidia beats estimates on AI demand",
           "Tesla shares tumble after delivery miss", "Inflation fears weigh on Wall Street", "Apple upgraded by analysts"],
}


def demo_prices(seed: int = 7) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=260)
    out = {}
    for m in config.MARKETS.values():
        for sym in [m["index"], *m["watchlist"]]:
            drift = rng.normal(0.0004, 0.001)
            rets = rng.normal(drift, 0.018, len(idx))
            close = 100 * np.exp(np.cumsum(rets))
            vol = rng.integers(1_000_000, 5_000_000, len(idx)).astype(float)
            out[sym] = pd.DataFrame({"Close": close, "Volume": vol}, index=idx)
    return out


def demo_news(query: str, lang: dict, limit: int = 10) -> list[dict]:
    market = "TW" if lang["gl"] == "TW" else "US"
    rng = np.random.default_rng(abs(hash(query)) % 2**32)
    titles = rng.choice(_SAMPLE[market], size=3, replace=False)
    return [{
        "title": f"{t}（{query}）", "link": "#", "source": "Demo", "published": "",
        "age_hours": round(float(rng.uniform(0, 48)), 1), "sentiment": round(news.sentiment(t), 3),
    } for t in titles]
