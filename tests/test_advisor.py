import numpy as np
import pandas as pd

from stock_advisor import engine, indicators, news
from stock_advisor.demo import demo_fx, demo_news, demo_prices, demo_quote_time


def _series(trend):
    idx = pd.bdate_range("2025-01-01", periods=250)
    close = 100 * np.exp(np.cumsum(np.full(250, trend) + np.random.default_rng(0).normal(0, 0.003, 250)))
    return pd.DataFrame({"Close": close, "Volume": 1e6}, index=idx)


def test_uptrend_scores_positive():
    s, _ = indicators.score(indicators.compute(_series(0.004)))
    assert s > 0.3


def test_downtrend_scores_negative():
    s, _ = indicators.score(indicators.compute(_series(-0.004)))
    assert s < -0.15


def test_sentiment_zh_en():
    assert news.sentiment("台積電營收優於預期 股價大漲") > 0
    assert news.sentiment("外資賣超 台股重挫") < 0
    assert news.sentiment("Nvidia shares surge after earnings beat") > 0
    assert news.sentiment("Stocks tumble on recession fears") < 0
    assert news.sentiment("Company opens new office") == 0
    # "beat" 不應匹配 "beaten" 之外的子字串，如 "upbeat" 內
    assert news.sentiment("upbeaten path") == 0


def test_rating_thresholds():
    assert engine.rate(0.6) == "強力買進"
    assert engine.rate(0.0) == "持有觀望"
    assert engine.rate(-0.9) == "賣出"


def test_full_pipeline_demo():
    r = engine.analyze(prices=demo_prices(), news_fetcher=demo_news, fx_fetcher=demo_fx, quote_time_fetcher=demo_quote_time)
    for m in r["markets"].values():
        assert len(m["stocks"]) == 8
        scores = [s["score"] for s in m["stocks"]]
        assert scores == sorted(scores, reverse=True)
        assert all(-1 <= x <= 1 for x in scores)


def test_theme_score_direction():
    themes = [
        {"id": "a", "name": "A", "signal": 0.8, "count": 5, "exposure": {"X": 1.0, "Y": -0.5}},
        {"id": "b", "name": "B", "signal": -0.6, "count": 5, "exposure": {"X": 0.5}},
        {"id": "c", "name": "C", "signal": 0.9, "count": 0, "exposure": {"X": 1.0}},  # 無新聞不計
    ]
    sx, hits = engine.theme_score("X", themes)
    assert abs(sx - (0.8 - 0.3) / 1.5) < 1e-9
    assert hits[0]["id"] == "a"
    sy, _ = engine.theme_score("Y", themes)
    assert sy < 0  # 反向曝險
    assert engine.theme_score("Z", themes) == (0.0, [])


def test_theme_bias_makes_risk_news_negative():
    # 關稅主題：標題中性但報導很多 -> 訊號偏負
    neutral = lambda q, lang, limit=10: [
        {"title": f"tariff update {i}", "link": "", "source": "", "published": "", "age_hours": 1.0, "sentiment": 0.0}
        for i in range(10)]
    themes = {t["id"]: t for t in engine.analyze_themes(neutral)}
    assert themes["tariff"]["signal"] < 0
    assert themes["semi"]["signal"] == 0


def test_weights_sum_to_one():
    from stock_advisor import config
    assert abs(sum(config.WEIGHTS.values()) - 1) < 1e-9


def test_cathay_fx_parse():
    from pathlib import Path
    from stock_advisor import fx
    page = (Path(__file__).parent / "fixtures" / "cathay_fx_sample.html").read_text(encoding="utf-8")
    d = fx.parse(page)
    assert d["board_time"] and "年" in d["board_time"]
    usd = next(r for r in d["rates"] if r["code"] == "USD")
    assert usd["name"] == "美元"
    assert usd["spot"]["buy"] < usd["spot"]["sell"]
    assert usd["cash"]["buy"] < usd["spot"]["buy"]  # 現鈔買進價較低
    assert fx.usd_rate(d) == usd["spot"]["sell"]
    assert fx.parse("<html>改版</html>")["rates"] == []


def test_us_price_converted_to_twd():
    from stock_advisor.demo import demo_fx
    r = engine.analyze(prices=demo_prices(), news_fetcher=demo_news, fx_fetcher=demo_fx, quote_time_fetcher=demo_quote_time)
    s = r["markets"]["US"]["stocks"][0]
    assert s["price_twd"] and abs(s["price_twd"] - s["price"] * 33.24) < 1
    assert r["markets"]["TW"]["stocks"][0]["price_twd"] is None


def test_news_cache_reuses_and_refreshes(tmp_path):
    calls = []

    def fake(q, lang, limit=10):
        calls.append(q)
        return [{"title": "x", "link": "", "source": "", "published": "", "age_hours": 0.0,
                 "ts": 0, "sentiment": 0.5}] if q != "fail" else []

    lang = {"hl": "zh-TW"}
    f = news.cached(fake, tmp_path / "c.json", ttl_minutes=30)
    a = f("台股", lang, 10)
    b = f("台股", lang, 10)
    assert len(calls) == 1 and a[0]["title"] == b[0]["title"]
    assert b[0]["age_hours"] > 1000  # 依 ts 重新計算新聞年齡
    # 新的實例讀取同一個檔案也能命中
    f2 = news.cached(fake, tmp_path / "c.json", ttl_minutes=30)
    f2("台股", lang, 10)
    assert len(calls) == 1
    # ttl 為 0 時重新抓取
    news.cached(fake, tmp_path / "c.json", ttl_minutes=0)("台股", lang, 10)
    assert len(calls) == 2
    assert f("fail", lang, 10) == []


def test_market_status():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from stock_advisor.market_clock import describe, status
    tp, ny = ZoneInfo("Asia/Taipei"), ZoneInfo("America/New_York")
    wed = lambda h, m, tz: datetime(2026, 11, 25, h, m, tzinfo=tz)  # 週三
    q_today = wed(10, 0, tp)
    assert status("TW", q_today, wed(10, 20, tp)) == "交易中"
    assert status("TW", q_today, wed(8, 45, tp)) == "盤前"
    assert status("TW", wed(13, 30, tp), wed(20, 0, tp)) == "已收盤"
    assert status("TW", q_today, datetime(2026, 11, 28, 10, 0, tzinfo=tp)) == "休市（週末）"
    # 平日開盤後卻沒有當天報價 -> 假日
    assert status("TW", datetime(2026, 11, 24, 13, 30, tzinfo=tp), wed(11, 0, tp)) == "休市（假日）"
    # 美股：台北週四早上 = 美東週三晚上，已收盤
    assert status("US", wed(16, 0, ny), datetime(2026, 11, 26, 8, 0, tzinfo=tp)) == "已收盤"
    assert status("US", wed(10, 0, ny), wed(10, 30, ny)) == "交易中"
    d = describe("US", wed(16, 0, ny), wed(18, 0, ny))
    assert d["time_local"] == "11/25 16:00" and d["time_taipei"] == "11/26 05:00"
    assert describe("TW", None, wed(10, 0, tp))["time"] is None
