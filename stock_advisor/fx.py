"""國泰世華銀行牌告匯率。

資料來源：https://www.cathaybk.com.tw/cathaybk/personal/product/deposit/currency-billboard/
解析網頁上每個幣別卡片中的「即期匯率 / 數位通路優惠匯率 / 現鈔匯率」的銀行買進、賣出價。
網頁改版時若解析失敗，只會印出警告、不會中斷整體更新。
"""
from __future__ import annotations

import html
import re

import requests

URL = "https://www.cathaybk.com.tw/cathaybk/personal/product/deposit/currency-billboard/"
UA = {"User-Agent": "Mozilla/5.0 (stock-advisor)"}

ROW_KEYS = {"即期匯率": "spot", "數位通路優惠匯率": "digital", "現鈔匯率": "cash"}

_TAG = re.compile(r"<[^>]+>")
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", fragment))).strip()


def parse(page: str) -> dict:
    """回傳 {"board_time": str|None, "rates": [{code, name, spot:{buy,sell}, digital:{...}, cash:{...}}]}"""
    m = re.search(r"資料時間[^<]*</span>\s*<span>([^<]+)</span>", page)
    board_time = m.group(1).strip() if m else None

    rates = []
    blocks = page.split('class="cubre-o-table__item currency"')[1:]
    for blk in blocks:
        nm = re.search(r'cubre-m-currency__name">(.*?)</div>', blk, re.S)
        if not nm:
            continue
        label = _text(nm.group(1))
        code_m = re.search(r"([A-Z]{3})", label)
        if not code_m:
            continue
        code = code_m.group(1)
        item = {"code": code, "name": label.replace(code, "").strip()}
        for row in re.findall(r"<tr>(.*?)</tr>", blk, re.S):
            cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) < 3 or cells[0] not in ROW_KEYS:
                continue
            buy, sell = (float(x) if _NUM.match(x) else None for x in cells[1:3])
            item[ROW_KEYS[cells[0]]] = {"buy": buy, "sell": sell}
        if "spot" in item or "cash" in item:
            rates.append(item)
    return {"board_time": board_time, "rates": rates}


def fetch() -> dict:
    try:
        resp = requests.get(URL, headers=UA, timeout=30)
        resp.raise_for_status()
        data = parse(resp.text)
    except Exception as e:
        print(f"[fx] 國泰世華匯率抓取失敗: {e}")
        return {"source": "國泰世華銀行", "url": URL, "board_time": None, "rates": []}
    if not data["rates"]:
        print("[fx] 國泰世華匯率頁面解析不到資料（可能網頁改版）")
    return {"source": "國泰世華銀行", "url": URL, **data}


def usd_rate(fx: dict, kind: str = "spot", side: str = "sell") -> float | None:
    """取美元匯率；買美股要用台幣換美元，所以預設取『銀行賣出』價。"""
    for r in fx.get("rates", []):
        if r["code"] == "USD":
            return (r.get(kind) or {}).get(side)
    return None
