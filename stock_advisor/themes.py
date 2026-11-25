"""時事主題 -> 產業 / 個股對應表。

每個主題會用中英文關鍵字各搜尋一次新聞，算出「主題訊號」(-1 ~ +1)：
  主題訊號 = 主題新聞情緒（時間加權） + 基準偏向 × 新聞熱度

個股的主題分數 = Σ(曝險 × 主題訊號) / Σ|曝險|
  曝險 > 0：主題新聞是好消息時受惠（例如 AI 需求強 -> 廣達加分）
  曝險 < 0：主題新聞是好消息時反而受壓
  數字大小代表影響程度（0.3 輕微、1.0 直接相關）

基準偏向 bias：有些主題「一被大量報導」本身就是風險（例如關稅、兩岸緊張），
即使標題用字中性，也會給予負向偏移；新聞越多，偏移越大。

不在觀察清單裡的代號會自動忽略，可放心增減。
"""

THEMES = [
    {
        "id": "ai",
        "name": "AI 伺服器與算力",
        "queries": {"TW": "AI 伺服器 需求", "US": "AI data center spending"},
        "bias": 0.05,
        "exposure": {
            "2382.TW": 1.0, "2330.TW": 0.9, "2317.TW": 0.8, "2308.TW": 0.7, "2454.TW": 0.4,
            "0050.TW": 0.5, "NVDA": 1.0, "MSFT": 0.6, "GOOGL": 0.6, "AMZN": 0.6, "META": 0.6, "SPY": 0.3,
        },
    },
    {
        "id": "semi",
        "name": "半導體景氣",
        "queries": {"TW": "半導體 景氣 晶片", "US": "semiconductor chip demand"},
        "bias": 0.0,
        "exposure": {
            "2330.TW": 1.0, "2454.TW": 1.0, "0050.TW": 0.6, "2308.TW": 0.3, "NVDA": 0.9, "SPY": 0.2,
        },
    },
    {
        "id": "tariff",
        "name": "關稅與貿易戰",
        "queries": {"TW": "關稅 貿易戰 台灣", "US": "tariffs trade war"},
        "bias": -0.2,
        "exposure": {
            "2317.TW": 1.0, "2382.TW": 0.8, "2330.TW": 0.6, "2308.TW": 0.6, "2454.TW": 0.5, "0050.TW": 0.5,
            "AAPL": 1.0, "TSLA": 0.6, "AMZN": 0.5, "NVDA": 0.4, "SPY": 0.4,
        },
    },
    {
        "id": "geo",
        "name": "兩岸與地緣政治",
        "queries": {"TW": "兩岸 局勢", "US": "Taiwan China tensions"},
        "bias": -0.15,
        "exposure": {
            "2330.TW": 1.0, "0050.TW": 1.0, "2317.TW": 0.6, "2454.TW": 0.6, "2382.TW": 0.6, "2308.TW": 0.5,
            "2881.TW": 0.6, "2412.TW": 0.2, "NVDA": 0.3, "AAPL": 0.4,
        },
    },
    {
        "id": "rates",
        "name": "利率與央行政策",
        "queries": {"TW": "央行 利率 降息", "US": "Fed interest rate decision"},
        "bias": 0.0,
        # 降息屬正面用語：成長股、高估值股受惠；金融股利差可能收窄
        "exposure": {
            "TSLA": 0.8, "NVDA": 0.5, "AMZN": 0.5, "META": 0.4, "GOOGL": 0.4, "MSFT": 0.4, "AAPL": 0.4,
            "SPY": 0.7, "0050.TW": 0.5, "2330.TW": 0.3, "2881.TW": -0.3, "2412.TW": 0.3,
        },
    },
    {
        "id": "ev",
        "name": "電動車",
        "queries": {"TW": "電動車 供應鏈", "US": "electric vehicle sales"},
        "bias": 0.0,
        "exposure": {"TSLA": 1.0, "2308.TW": 0.7, "2317.TW": 0.4},
    },
    {
        "id": "iphone",
        "name": "iPhone 與消費電子",
        "queries": {"TW": "蘋果 iPhone 銷售", "US": "iPhone sales Apple demand"},
        "bias": 0.0,
        "exposure": {"AAPL": 1.0, "2317.TW": 0.9, "2330.TW": 0.3, "2454.TW": 0.3},
    },
    {
        "id": "fin",
        "name": "金融與壽險",
        "queries": {"TW": "金控 獲利 壽險", "US": "bank earnings financial sector"},
        "bias": 0.0,
        "exposure": {"2881.TW": 1.0, "0050.TW": 0.2, "SPY": 0.2},
    },
    {
        "id": "antitrust",
        "name": "科技巨頭監管",
        "queries": {"TW": "科技巨頭 反壟斷", "US": "big tech antitrust regulation"},
        "bias": -0.1,
        "exposure": {"GOOGL": 1.0, "META": 1.0, "AAPL": 0.6, "AMZN": 0.6, "MSFT": 0.4},
    },
]
