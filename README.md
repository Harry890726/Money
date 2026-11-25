# Money — 台美股投資建議小工具

每小時自動抓取 **台灣與美國** 的股價與新聞，依「技術面演算 + 國家／個股新聞情緒」計算分數，產出投資建議（強力買進／買進／持有觀望／減碼／賣出），並發布成網頁儀表板。

> ⚠️ 本工具輸出為演算法自動產生的參考資訊，**不構成投資建議**。投資有風險，請自行判斷。

## 運作方式

| 訊號 | 權重 | 內容 |
|---|---:|---|
| 技術面 | 50% | 20/50/200 日均線排列、RSI(14)、MACD 交叉、布林通道、20 日動能、量價關係 |
| 個股新聞 | 20% | Google News 近 3 日個股新聞，中英文關鍵字情緒分析，24 小時半衰期加權 |
| 國家新聞 | 15% | 台股／台灣經濟／央行、美股／Fed／通膨等總體新聞情緒 |
| 大盤趨勢 | 15% | 加權指數、S&P 500 的技術面分數 |

總分範圍 -1 ~ +1：`≥0.45` 強力買進、`≥0.15` 買進、`≥-0.15` 持有觀望、`≥-0.45` 減碼、其餘賣出。
「信心」依各訊號方向是否一致、新聞數量而定。

## 每小時自動更新（GitHub Actions + Pages）

1. 將此分支合併到 `main`（GitHub 的排程只會在預設分支上執行）。
2. 到 repo **Settings → Pages → Source** 選 **GitHub Actions**。
3. 到 **Actions → 每小時更新投資建議 → Run workflow** 先手動跑一次。

之後每小時第 17 分（UTC）自動執行，結果會：
- 發布到 `https://<你的帳號>.github.io/Money/` 儀表板
- 提交 `docs/data/latest.json`（完整資料）、`docs/data/history.jsonl`（歷史分數，可回測）、`reports/latest.md`（Markdown 報告）

## 本機執行

```bash
pip install -r requirements.txt
python -m stock_advisor            # 執行一次
python -m stock_advisor --loop     # 常駐，每小時更新
python -m stock_advisor --demo     # 離線示範資料
cd docs && python -m http.server   # 開 http://localhost:8000 看儀表板
```

## 自訂

編輯 `stock_advisor/config.py`：
- `watchlist`：追蹤的股票（台股代號加 `.TW`，上櫃加 `.TWO`）
- `news_queries`：國家新聞關鍵字
- `WEIGHTS`、`RATING_THRESHOLDS`：權重與評等門檻

情緒詞典在 `stock_advisor/news.py`，可自行增補關鍵字。

## 測試

```bash
pip install pytest && python -m pytest -q
```
