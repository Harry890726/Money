"""新聞抓取（Google News RSS）與中英文關鍵字情緒分析。"""
from __future__ import annotations

import calendar
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (stock-advisor)"}

# ---- 情緒詞典（權重 1~2）----
POS = {
    # 中文
    "大漲": 2, "飆漲": 2, "創新高": 2, "漲停": 2, "強勁": 1.5, "優於預期": 2, "超乎預期": 2,
    "上修": 1.5, "調升": 1, "成長": 1, "上漲": 1, "回升": 1, "反彈": 1, "利多": 2, "買超": 1.5,
    "看好": 1.5, "樂觀": 1.5, "降息": 1, "擴產": 1, "獲利": 1, "營收增": 1.5, "創高": 1.5,
    "增長": 1, "加碼": 1, "強彈": 1.5, "復甦": 1.5, "熱銷": 1.5, "訂單滿": 1.5, "升評": 1.5,
    # 英文
    "surge": 2, "soar": 2, "rally": 1.5, "record high": 2, "beat": 1.5, "beats": 1.5,
    "upgrade": 1.5, "upgraded": 1.5, "growth": 1, "gain": 1, "gains": 1, "rise": 1, "rises": 1,
    "jump": 1.5, "jumps": 1.5, "bullish": 1.5, "strong": 1, "optimism": 1.5, "rate cut": 1,
    "outperform": 1.5, "boost": 1, "rebound": 1, "recovery": 1, "profit": 0.5, "buy": 0.5,
    "暫緩": 1.5, "豁免": 1.5, "休兵": 1.5, "緩和": 1.5, "達成協議": 1.5, "勝訴": 1.5, "需求強": 1.5,
    "truce": 1.5, "exemption": 1.5, "eases": 1, "easing": 1, "deal": 1, "agreement": 1, "wins": 1,
}
NEG = {
    "大跌": 2, "暴跌": 2, "重挫": 2, "跌停": 2, "崩跌": 2, "疲弱": 1.5, "低於預期": 2, "不如預期": 2,
    "下修": 1.5, "調降": 1, "衰退": 1.5, "下跌": 1, "走弱": 1, "利空": 2, "賣超": 1.5,
    "看壞": 1.5, "悲觀": 1.5, "升息": 1, "裁員": 1.5, "虧損": 1.5, "營收減": 1.5, "關稅": 1,
    "制裁": 1.5, "衝突": 1, "通膨": 0.5, "降評": 1.5, "砍單": 2, "警訊": 1.5, "崩盤": 2,
    "plunge": 2, "plunges": 2, "tumble": 2, "tumbles": 2, "crash": 2, "slump": 1.5, "miss": 1.5,
    "misses": 1.5, "downgrade": 1.5, "downgraded": 1.5, "recession": 1.5, "fall": 1, "falls": 1,
    "drop": 1, "drops": 1, "decline": 1, "declines": 1, "bearish": 1.5, "weak": 1, "fears": 1.5,
    "layoffs": 1.5, "loss": 1, "losses": 1, "tariff": 1, "tariffs": 1, "sell-off": 2, "selloff": 2,
    "rate hike": 1, "inflation": 0.5, "lawsuit": 1, "probe": 1, "underperform": 1.5, "slowdown": 1.5,
    "緊張": 1.5, "軍演": 1.5, "封鎖": 1.5, "升溫": 1, "罰款": 1.5, "反壟斷": 1, "禁令": 1.5, "管制": 1,
    "tension": 1.5, "tensions": 1.5, "escalation": 1.5, "escalates": 1.5, "ban": 1.5,
    "fined": 1.5, "antitrust": 1, "sanctions": 1.5, "export controls": 1.5,
}
NEGATORS = ("不", "未", "沒", "無", "not ", "no ", "n't ")


def sentiment(text: str) -> float:
    """回傳 -1 ~ +1 的情緒分數。"""
    t = text.lower()
    s = 0.0
    for lex, sign in ((POS, 1), (NEG, -1)):
        for word, w in lex.items():
            for m in re.finditer(re.escape(word), t):
                # 英文需完整單字
                if word.isascii() and not _word_boundary(t, m.start(), m.end()):
                    continue
                pre = t[max(0, m.start() - 4):m.start()]
                flip = -1 if any(n in pre for n in NEGATORS) else 1
                s += sign * w * flip
    return max(-1.0, min(1.0, s / 3))


def _word_boundary(t: str, a: int, b: int) -> bool:
    return (a == 0 or not t[a - 1].isalnum()) and (b >= len(t) or not t[b].isalnum())


def fetch(query: str, lang: dict, limit: int = 15, max_age_hours: float = 72) -> list[dict]:
    url = (
        f"https://news.google.com/rss/search?q={quote(query)}+when:3d"
        f"&hl={lang['hl']}&gl={lang['gl']}&ceid={lang['ceid']}"
    )
    try:
        resp = requests.get(url, headers=UA, timeout=20)
        resp.raise_for_status()
    except Exception as e:  # 網路錯誤不應中斷整體流程
        print(f"[news] {query!r} 抓取失敗: {e}")
        return []
    feed = feedparser.parse(resp.content)
    now = time.time()
    items = []
    for e in feed.entries[:limit]:
        published = calendar.timegm(e.published_parsed) if getattr(e, "published_parsed", None) else now
        age_h = max(0.0, (now - published) / 3600)
        if age_h > max_age_hours:
            continue
        title = html.unescape(e.get("title", ""))
        source = e.get("source", {}).get("title", "") if isinstance(e.get("source"), dict) else ""
        items.append({
            "title": title,
            "link": e.get("link", ""),
            "source": source,
            "published": time.strftime("%Y-%m-%d %H:%M", time.gmtime(published)) + " UTC",
            "age_hours": round(age_h, 1),
            "ts": int(published),
            "sentiment": round(sentiment(title), 3),
        })
    return items


def cached(fetcher, path: Path, ttl_minutes: float = 30):
    """包裝新聞抓取：同一關鍵字在 ttl 分鐘內重複使用上次結果，避免高頻更新時被 Google 封鎖。
    重複使用時會依發布時間重新計算「幾小時前」。抓取失敗（空結果）不寫入快取。"""
    path = Path(path)
    try:
        store = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        store = {}

    def wrapper(query: str, lang: dict, limit: int = 15) -> list[dict]:
        key = f"{lang['hl']}|{limit}|{query}"
        now = time.time()
        hit = store.get(key)
        if hit and now - hit["fetched_at"] < ttl_minutes * 60:
            items = [dict(it) for it in hit["items"]]
            for it in items:
                if "ts" in it:
                    it["age_hours"] = round(max(0.0, (now - it["ts"]) / 3600), 1)
            return items
        items = fetcher(query, lang, limit)
        if items:
            store[key] = {"fetched_at": now, "items": items}
            # 清掉一天以上沒用到的關鍵字
            for k in [k for k, v in store.items() if now - v["fetched_at"] > 86400]:
                del store[k]
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
            except OSError as e:
                print(f"[news] 無法寫入快取: {e}")
        elif hit:  # 這次失敗就沿用舊資料
            return [dict(it) for it in hit["items"]]
        return items

    return wrapper


def aggregate(items: list[dict]) -> float:
    """以時間衰減加權平均（越新的新聞權重越高，半衰期 24 小時）。"""
    if not items:
        return 0.0
    num = den = 0.0
    for it in items:
        w = 0.5 ** (it["age_hours"] / 24)
        num += it["sentiment"] * w
        den += w
    return num / den if den else 0.0


def heat(items: list[dict]) -> float:
    """新聞熱度 0 ~ 1：近期（時間加權）報導越多越熱，約 8 則當日新聞即為滿分。"""
    return min(1.0, sum(0.5 ** (it["age_hours"] / 24) for it in items) / 8)


def dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\s*-\s*[^-]+$", "", it["title"]).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
