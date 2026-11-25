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
