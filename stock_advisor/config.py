"""觀察清單與參數設定。修改這裡即可調整追蹤的股票與新聞關鍵字。"""

MARKETS = {
    "TW": {
        "name": "台灣股市",
        "index": "^TWII",
        "index_name": "加權指數",
        "currency": "TWD",
        # Google News RSS（國家層級新聞）
        "news_queries": ["台股", "台灣 經濟", "央行 利率 台灣", "外資 台股"],
        "news_lang": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
        "watchlist": {
            "2330.TW": "台積電",
            "2317.TW": "鴻海",
            "2454.TW": "聯發科",
            "2308.TW": "台達電",
            "2382.TW": "廣達",
            "2881.TW": "富邦金",
            "2412.TW": "中華電",
            "0050.TW": "元大台灣50",
        },
    },
    "US": {
        "name": "美國股市",
        "index": "^GSPC",
        "index_name": "S&P 500",
        "currency": "USD",
        "news_queries": ["US stock market", "Federal Reserve", "US economy inflation", "Wall Street"],
        "news_lang": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
        "watchlist": {
            "AAPL": "Apple",
            "MSFT": "Microsoft",
            "NVDA": "NVIDIA",
            "GOOGL": "Alphabet",
            "AMZN": "Amazon",
            "META": "Meta",
            "TSLA": "Tesla",
            "SPY": "S&P 500 ETF",
        },
    },
}

# 綜合分數權重（技術面、個股新聞、國家/總體新聞、大盤趨勢）
WEIGHTS = {
    "technical": 0.50,
    "stock_news": 0.20,
    "macro_news": 0.15,
    "market_trend": 0.15,
}

# 分數門檻 -> 建議
RATING_THRESHOLDS = [
    (0.45, "強力買進"),
    (0.15, "買進"),
    (-0.15, "持有觀望"),
    (-0.45, "減碼"),
    (-1.01, "賣出"),
]

PRICE_HISTORY = "1y"
NEWS_PER_QUERY = 15
