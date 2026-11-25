"""產生 Markdown 報告。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TW_TZ = timezone(timedelta(hours=8))


def _f(v, fmt="{:+.2f}%"):
    return "—" if v is None else fmt.format(v)


def to_markdown(r: dict) -> str:
    t = datetime.fromisoformat(r["generated_at"]).astimezone(TW_TZ)
    lines = [
        "# 台美股投資建議報告",
        "",
        f"更新時間：{t:%Y-%m-%d %H:%M}（台北時間）" + ("　⚠️ 示範資料" if r.get("demo") else ""),
        "",
        "> 本報告由演算法依技術指標與新聞情緒自動產生，僅供參考，不構成投資建議。投資有風險，請自行判斷。",
        "",
    ]
    for m in r["markets"].values():
        idx = m["index"]
        lines += [
            f"## {m['name']}",
            "",
            f"- **大盤**：{idx['name']} {_f(idx['price'], '{:,.2f}')}（今日 {_f(idx['change_pct'])}，20 日 {_f(idx['ret_20d'])}）",
            f"- **市場看法**：{m['market_view']}（市場分數 {m['market_score']:+.2f}，新聞情緒 {m['macro_sentiment']:+.2f}）",
            "",
            "| 代號 | 名稱 | 價格 | 今日 | 20日 | RSI | 主題 | 分數 | 建議 | 信心 | 主要理由 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for s in m["stocks"]:
            lines.append(
                f"| {s['symbol']} | {s['name']} | {_f(s['price'], '{:,.2f}')} | {_f(s['change_pct'])} "
                f"| {_f(s['ret_20d'])} | {_f(s['rsi14'], '{:.0f}')} | {s['theme_score']:+.2f} | {s['score']:+.2f} | **{s['rating']}** "
                f"| {s['confidence']} | {'；'.join(s['reasons'][:3]) or '—'} |"
            )
        lines += ["", "### 時事主題", "", "| 主題 | 訊號 | 熱度 | 相關個股 |", "|---|---:|---:|---|"]
        for t in m.get("themes", []):
            stocks = "、".join(f"{x['name']}{'(反向)' if x['exposure'] < 0 else ''}" for x in t["stocks"][:5])
            lines.append(f"| {t['name']} | {t['signal']:+.2f} | {t['heat']:.0%} | {stocks} |")
        lines += ["", "### 國家重點新聞", ""]
        for h in m["headlines"][:8]:
            mark = "🟢" if h["sentiment"] > 0.1 else "🔴" if h["sentiment"] < -0.1 else "⚪"
            lines.append(f"- {mark} [{h['title']}]({h['link']})")
        lines.append("")
    return "\n".join(lines)
