"""
用法：
  python -m stock_advisor            # 執行一次，輸出 docs/data/latest.json 與 reports/latest.md
  python -m stock_advisor --loop     # 本機常駐，每小時更新一次
  python -m stock_advisor --demo     # 離線示範資料（不連網）
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import engine
from .report import to_markdown

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
REPORT_DIR = ROOT / "reports"


def run_once(demo: bool = False) -> dict:
    if demo:
        from .demo import demo_fx, demo_news, demo_prices
        result = engine.analyze(prices=demo_prices(), news_fetcher=demo_news, fx_fetcher=demo_fx)
        result["demo"] = True
    else:
        result = engine.analyze()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _attach_fx_change(result)
    payload = json.dumps(result, ensure_ascii=False, indent=1)
    (DATA_DIR / "latest.json").write_text(payload, encoding="utf-8")

    # 保留精簡歷史紀錄（每次一行），可用於回測建議準確度
    snap = {
        "t": result["generated_at"],
        **{f"{c}_market": m["market_score"] for c, m in result["markets"].items()},
        "fx": {r["code"]: (r.get("spot") or {}).get("sell") for r in result["fx"]["rates"]},
        "stocks": {s["symbol"]: [s["price"], s["score"]]
                   for m in result["markets"].values() for s in m["stocks"]},
    }
    with open(DATA_DIR / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")

    (REPORT_DIR / "latest.md").write_text(to_markdown(result), encoding="utf-8")
    print(f"[ok] {result['generated_at']} 已更新 "
          + ", ".join(f"{c}: {len(m['stocks'])} 檔" for c, m in result["markets"].items()))
    return result


def _attach_fx_change(result: dict) -> None:
    """與上一次紀錄比較即期賣出匯率，算出漲跌（台幣貶值 = 外幣匯率上升）。"""
    prev = {}
    hist = DATA_DIR / "history.jsonl"
    if hist.exists():
        lines = hist.read_text(encoding="utf-8").strip().splitlines()
        for line in reversed(lines):
            try:
                prev = json.loads(line).get("fx") or {}
            except ValueError:
                continue
            if prev:
                break
    for r in result["fx"]["rates"]:
        now, before = (r.get("spot") or {}).get("sell"), prev.get(r["code"])
        r["prev_sell"] = before
        r["change_pct"] = round((now / before - 1) * 100, 3) if now and before else None


def main():
    ap = argparse.ArgumentParser(description="台美股投資建議工具")
    ap.add_argument("--loop", action="store_true", help="每小時自動更新")
    ap.add_argument("--interval", type=int, default=3600, help="更新間隔秒數（預設 3600）")
    ap.add_argument("--demo", action="store_true", help="使用離線示範資料")
    args = ap.parse_args()

    if not args.loop:
        run_once(args.demo)
        return
    while True:
        try:
            run_once(args.demo)
        except Exception as e:
            print(f"[error] {datetime.now(timezone.utc)}: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
