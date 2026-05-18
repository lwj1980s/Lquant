#!/usr/bin/env python3
"""计算橙色三角 x 粉色三角配对（月线），输出 pairs_monthly.html"""
import json

with open("sse_monthly.json", encoding="utf-8") as f:
    records = json.load(f)

dates  = [r["date"]   for r in records]
closes = [r["close"]  for r in records]
highs  = [r["high"]   for r in records]
lows   = [r["low"]    for r in records]
n      = len(records)

def calc_ma(arr, period):
    result = [None] * len(arr)
    for i in range(period - 1, len(arr)):
        result[i] = sum(arr[i - period + 1 : i + 1]) / period
    return result

ma5  = calc_ma(closes, 5)
ma10 = calc_ma(closes, 10)
ma15 = calc_ma(closes, 15)
ma20 = calc_ma(closes, 20)

def calc_ema(arr, period):
    result = [None] * len(arr)
    k = 2 / (period + 1)
    for i, v in enumerate(arr):
        if v is None: continue
        result[i] = v if result[i-1] is None else v * k + result[i-1] * (1 - k)
    return result

ema12 = calc_ema(closes, 12)
ema26 = calc_ema(closes, 26)
dif = [round(ema12[i] - ema26[i], 3) if ema12[i] and ema26[i] else None for i in range(n)]

def all_above(i):
    return (ma5[i] and ma10[i] and ma15[i] and ma20[i] and
            ma5[i] > ma20[i] and ma10[i] > ma20[i] and ma15[i] > ma20[i])

orange_idxs = []
for i in range(1, n):
    ma20_rising = ma20[i] and ma20[i-1] and ma20[i] > ma20[i-1]
    if all_above(i) and not all_above(i-1) and ma20_rising:
        orange_idxs.append(i)

# 粉色：每个橙色后，DIF线第一个拐点（极大或极小）的下一根K线
pink_idxs = []
for oi in orange_idxs:
    for i in range(oi + 1, n - 1):
        if dif[i] is None or dif[i-1] is None or dif[i+1] is None: continue
        is_peak   = dif[i] > dif[i-1] and dif[i] > dif[i+1]
        is_trough = dif[i] < dif[i-1] and dif[i] < dif[i+1]
        if is_peak or is_trough:
            if i + 1 < n:
                pink_idxs.append(i + 1)
            break

events = [("orange", i) for i in orange_idxs] + [("pink", i) for i in pink_idxs]
events.sort(key=lambda x: x[1])

pairs = []
current_orange = None
for kind, idx in events:
    if kind == "orange":
        if current_orange is None:
            current_orange = idx
    else:
        if current_orange is not None:
            oi, pi = current_orange, idx
            diff = round(closes[pi] - closes[oi], 2)
            pct  = round((closes[pi] - closes[oi]) / closes[oi] * 100, 2)
            pairs.append(dict(orange_date=dates[oi], orange_close=closes[oi],
                              pink_date=dates[pi],   pink_close=closes[pi],
                              diff=diff, pct=pct))
            current_orange = None

total_pairs = len(pairs)
win     = sum(1 for p in pairs if p["diff"] > 0)
loss    = total_pairs - win
avg_pct = round(sum(p["pct"] for p in pairs) / total_pairs, 2) if total_pairs else 0

rows = ""
for idx, p in enumerate(pairs, 1):
    cls  = "pos" if p["diff"] >= 0 else "neg"
    sign = "+" if p["diff"] >= 0 else ""
    rows += (
        f'''<tr><td class="center">{idx}</td><td>{p["orange_date"]}</td>'''
        f'''<td class="num">{p["orange_close"]:,.2f}</td><td>{p["pink_date"]}</td>'''
        f'''<td class="num">{p["pink_close"]:,.2f}</td>'''
        f'''<td class="num {cls}">{sign}{p["diff"]:,.2f}</td>'''
        f'''<td class="num {cls}">{sign}{p["pct"]}%</td></tr>'''
    )

win_rate = round(win / total_pairs * 100, 1) if total_pairs else 0
avg_sign = "+" if avg_pct >= 0 else ""
rate_cls = "pos" if win_rate >= 50 else "neg"
avg_cls  = "pos" if avg_pct >= 0 else "neg"

CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: Menlo,Consolas,monospace; font-size: 13px; padding: 24px; }
  h1 { font-size: 18px; margin-bottom: 20px; color: #e6edf3; }
  .summary { display: flex; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 22px; min-width: 140px; }
  .card .label { font-size: 11px; color: #8b949e; margin-bottom: 6px; }
  .card .val { font-size: 22px; font-weight: bold; }
  .card .val.pos { color: #f85149; }
  .card .val.neg { color: #3fb950; }
  .card .val.neu { color: #79c0ff; }
  table { width: 100%; border-collapse: collapse; }
  thead tr { background: #161b22; }
  th { padding: 10px 14px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .8px; border-bottom: 1px solid #30363d; white-space: nowrap; }
  td { padding: 9px 14px; border-bottom: 1px solid #21262d; white-space: nowrap; }
  tr:hover td { background: #1c2128; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .center { text-align: center; color: #8b949e; }
  .pos { color: #f85149; }
  .neg { color: #3fb950; }
  .od { display:inline-block;width:9px;height:9px;background:#ff9800;clip-path:polygon(50% 0%,100% 100%,0% 100%);margin-right:5px; }
  .pd { display:inline-block;width:9px;height:9px;background:#ff1493;clip-path:polygon(50% 100%,0% 0%,100% 0%);margin-right:5px; }
"""

html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<title>配对统计（月线）</title><style>{CSS}</style></head><body>
<h1>上证指数（月线）· 橙色三角 x 粉色三角 配对收益统计</h1>
<div class="summary">
  <div class="card"><div class="label">配对总数</div><div class="val neu">{total_pairs}</div></div>
  <div class="card"><div class="label">盈利次数</div><div class="val pos">{win}</div></div>
  <div class="card"><div class="label">亏损次数</div><div class="val neg">{loss}</div></div>
  <div class="card"><div class="label">胜率</div><div class="val {rate_cls}">{win_rate}%</div></div>
  <div class="card"><div class="label">平均收益</div><div class="val {avg_cls}">{avg_sign}{avg_pct}%</div></div>
</div>
<table><thead><tr>
  <th>#</th><th><span class="od"></span>橙色三角日期</th><th>收盘价</th>
  <th><span class="pd"></span>粉色三角日期</th><th>收盘价</th>
  <th>差值（点）</th><th>涨跌幅</th>
</tr></thead><tbody>{rows}</tbody></table></body></html>"""

with open("pairs_monthly.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"生成完毕 -> pairs_monthly.html（共 {total_pairs} 对）")
