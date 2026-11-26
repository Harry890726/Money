# Money — 台美股投資建議小工具

約每 5 分鐘自動抓取 **台灣與美國** 的股價與新聞，依「技術面演算 + 國家／個股新聞情緒」計算分數，產出投資建議（強力買進／買進／持有觀望／減碼／賣出），並發布成網頁儀表板。

> ⚠️ 本工具輸出為演算法自動產生的參考資訊，**不構成投資建議**。投資有風險，請自行判斷。

## 運作方式

| 訊號 | 權重 | 內容 |
|---|---:|---|
| 技術面 | 45% | 20/50/200 日均線排列、RSI(14)、MACD 交叉、布林通道、20 日動能、量價關係 |
| 個股新聞 | 20% | Google News 近 3 日個股新聞，中英文關鍵字情緒分析，24 小時半衰期加權 |
| 時事主題 | 15% | AI、半導體、關稅、兩岸、利率、電動車、iPhone、金融、科技監管等主題新聞，依產業曝險對應到個股 |
| 國家新聞 | 10% | 台股／台灣經濟／央行、美股／Fed／通膨等總體新聞情緒 |
| 大盤趨勢 | 10% | 加權指數、S&P 500 的技術面分數 |

### 時事主題如何影響個股

每個主題（`stock_advisor/themes.py`）會搜尋中英文新聞，算出主題訊號（-1 ~ +1）。
個股的主題分數 = Σ(曝險 × 主題訊號) / Σ|曝險|。例如「AI 伺服器」新聞偏正面時，曝險 1.0 的廣達加分最多、曝險 0.4 的聯發科加分較少。
關稅、兩岸等風險主題設有負向「基準偏向」：即使標題用字中性，報導量越大也越偏空。

總分範圍 -1 ~ +1：`≥0.45` 強力買進、`≥0.15` 買進、`≥-0.15` 持有觀望、`≥-0.45` 減碼、其餘賣出。
「信心」依各訊號方向是否一致、新聞數量而定。

## 國泰世華匯率

每次更新會抓取[國泰世華銀行牌告匯率](https://www.cathaybk.com.tw/cathaybk/personal/product/deposit/currency-billboard/)（16 種外幣的即期、數位通路優惠、現鈔買進／賣出價），
顯示在儀表板的「國泰匯率」分頁與報告中，並與上一次更新比較漲跌。美股個股另以美元即期賣出匯率換算每股台幣價格。

## 自動更新（GitHub Actions + Pages）

1. 將此分支合併到 `main`（GitHub 的排程只會在預設分支上執行）。
2. 到 repo **Settings → Pages → Source** 選 **GitHub Actions**。
3. 到 **Actions → 每小時更新投資建議 → Run workflow** 先手動跑一次。

之後約每 5 分鐘自動執行：每一輪結束後自動觸發下一輪（GitHub 的排程常常不觸發，只當備援）。要停止時到 Actions → 每小時更新投資建議 → 「…」→ Disable workflow。股價、匯率每次重新抓取；新聞快取 30 分鐘以免被 Google 封鎖。結果會：
- 發布到 `https://<你的帳號>.github.io/Money/` 儀表板
- 每小時存回 repo 一次：`docs/data/latest.json`（完整資料）、`docs/data/history.jsonl`（歷史分數，可回測）、`reports/latest.md`（Markdown 報告）

## 本機執行

```bash
pip install -r requirements.txt
python -m stock_advisor            # 執行一次
python -m stock_advisor --loop     # 常駐，每 5 分鐘更新
python -m stock_advisor --demo     # 離線示範資料
python -m stock_advisor --serve    # 開啟 http://localhost:8000 並每 5 分鐘自動更新（推薦）
```

## 自訂

編輯 `stock_advisor/config.py`：
- `watchlist`：追蹤的股票（台股代號加 `.TW`，上櫃加 `.TWO`）
- `news_queries`：國家新聞關鍵字
- `themes.py`：新增／修改時事主題、搜尋關鍵字與各股曝險
- `WEIGHTS`、`RATING_THRESHOLDS`：權重與評等門檻

情緒詞典在 `stock_advisor/news.py`，可自行增補關鍵字。

## 測試

```bash
pip install pytest && python -m pytest -q
```
