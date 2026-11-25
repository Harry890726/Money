import numpy as np
import pandas as pd

from stock_advisor import engine, indicators, news
from stock_advisor.demo import demo_news, demo_prices


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
    r = engine.analyze(prices=demo_prices(), news_fetcher=demo_news)
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
