"""
用法：
  python -m stock_advisor            # 執行一次，輸出 docs/data/latest.json 與 reports/latest.md
  python -m stock_advisor --loop     # 本機常駐，每小時更新一次
  python -m stock_advisor --demo     # 離線示範資料（不連網）
  python -m stock_advisor --serve    # 開啟本機網頁 http://localhost:8000 並每 5 分鐘自動更新
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config, engine, news
from .report import to_markdown

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
REPORT_DIR = ROOT / "reports"


def run_once(demo: bool = False) -> dict:
    if demo:
        from .demo import demo_fx, demo_news, demo_prices, demo_quote_time
        result = engine.analyze(prices=demo_prices(), news_fetcher=demo_news, fx_fetcher=demo_fx,
                                quote_time_fetcher=demo_quote_time)
        result["demo"] = True
    else:
        fetcher = news.cached(news.fetch, ROOT / ".cache" / "news.json", config.NEWS_CACHE_MINUTES)
        result = engine.analyze(news_fetcher=fetcher)

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
    if _hours_since_last_history() >= 1:
        with open(DATA_DIR / "history.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")

    (REPORT_DIR / "latest.md").write_text(to_markdown(result), encoding="utf-8")
    print(f"[ok] {result['generated_at']} 已更新 "
          + ", ".join(f"{c}: {len(m['stocks'])} 檔" for c, m in result["markets"].items()))
    return result


def _hours_since_last_history() -> float:
    hist = DATA_DIR / "history.jsonl"
    try:
        last = hist.read_text(encoding="utf-8").strip().splitlines()[-1]
        t = datetime.fromisoformat(json.loads(last)["t"])
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except (OSError, IndexError, ValueError, KeyError):
        return float("inf")


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


def _start_server(port: int) -> None:
    """在背景執行緒提供 docs/ 網頁，主程式繼續定時更新資料。"""
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *a):  # 不要每次瀏覽都印一行
            pass

    handler = functools.partial(QuietHandler, directory=str(ROOT / "docs"))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[web] 網頁已啟動：http://localhost:{port}  （按 Ctrl+C 結束）")


def main():
    ap = argparse.ArgumentParser(description="台美股投資建議工具")
    ap.add_argument("--loop", action="store_true", help="定時自動更新")
    ap.add_argument("--interval", type=int, default=config.UPDATE_MINUTES * 60,
                    help=f"更新間隔秒數（預設 {config.UPDATE_MINUTES * 60}）")
    ap.add_argument("--demo", action="store_true", help="使用離線示範資料")
    ap.add_argument("--serve", action="store_true", help="同時開啟本機網頁並定時自動更新")
    ap.add_argument("--port", type=int, default=8000, help="本機網頁埠號（預設 8000）")
    args = ap.parse_args()

    if args.serve:
        _start_server(args.port)
        args.loop = True
    if not args.loop:
        run_once(args.demo)
        return
    try:
        while True:
            try:
                run_once(args.demo)
            except Exception as e:
                print(f"[error] {datetime.now(timezone.utc)}: {e}")
            print(f"[wait] 下次更新：{args.interval // 60} 分鐘後")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
