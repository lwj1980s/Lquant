#!/usr/bin/env python3
"""生成 monthly.html（月K线）— 三角逻辑为月线专属版本"""
import json

JSON_FILE = "sse_monthly.json"
TEMPLATE  = "index.html"
OUTPUT    = "monthly.html"
LABEL     = "月K线"

# ── 读取数据，构造 RAW_DATA 块 ─────────────────────────────────────────────────
with open(JSON_FILE, encoding="utf-8") as f:
    data = json.load(f)

lines = []
for i, r in enumerate(data):
    comma = "," if i < len(data) - 1 else ""
    lines.append(
        f'  {{"date":"{r["date"]}","open":{r["open"]},"close":{r["close"]}'
        f',"high":{r["high"]},"low":{r["low"]},"volume":{r["volume"]}}}{comma}'
    )
raw_data_block = "const RAW_DATA = [\n" + "\n".join(lines) + "\n];"

# ── 读取模板 ───────────────────────────────────────────────────────────────────
with open(TEMPLATE, encoding="utf-8") as f:
    content = f.read()

# ── 替换 RAW_DATA ──────────────────────────────────────────────────────────────
start = content.index("const RAW_DATA = [")
end   = content.index("];", start) + len("];")
content = content[:start] + raw_data_block + content[end:]

# ── 替换标题 ───────────────────────────────────────────────────────────────────
content = content.replace("上证指数日K线", f"上证指数{LABEL}")
content = content.replace("上证指数 日K线", f"上证指数 {LABEL}")

# ── 替换橙三角：MA1/MA2/MA4/MA6上穿MA8 → MA5/MA10/MA15上穿MA20 ───────────────
OLD_ORANGE = """  // 橙三角：MA1/MA2/MA4/MA6 同时上穿 MA8，MA8斜率为正
  const fixedMA1 = calcMA(closes, 1);
  const fixedMA2 = calcMA(closes, 2);
  const fixedMA4 = calcMA(closes, 4);
  const fixedMA6 = calcMA(closes, 6);
  const fixedMA8 = calcMA(closes, 8);

  const allAbove = i =>
    fixedMA1[i] !== null && fixedMA2[i] !== null &&
    fixedMA4[i] !== null && fixedMA6[i] !== null && fixedMA8[i] !== null &&
    fixedMA1[i] > fixedMA8[i] &&
    fixedMA2[i] > fixedMA8[i] &&
    fixedMA4[i] > fixedMA8[i] &&
    fixedMA6[i] > fixedMA8[i];"""

NEW_ORANGE = """  // 橙三角：MA5/MA10/MA15 同时上穿 MA20，MA20斜率为正（月线专属）
  const fixedMA5  = calcMA(closes, 5);
  const fixedMA10 = calcMA(closes, 10);
  const fixedMA15 = calcMA(closes, 15);
  const fixedMA20 = calcMA(closes, 20);

  const allAbove = i =>
    fixedMA5[i]  !== null && fixedMA10[i] !== null &&
    fixedMA15[i] !== null && fixedMA20[i] !== null &&
    fixedMA5[i]  > fixedMA20[i] &&
    fixedMA10[i] > fixedMA20[i] &&
    fixedMA15[i] > fixedMA20[i];"""

content = content.replace(OLD_ORANGE, NEW_ORANGE)

# ── 替换斜率判断：ma8Rising → ma20Rising ──────────────────────────────────────
OLD_RISING = """    const ma8Rising = fixedMA8[i] !== null && fixedMA8[i-1] !== null && fixedMA8[i] > fixedMA8[i-1];
    if (allAbove(i) && !allAbove(i-1) && ma8Rising) {"""

NEW_RISING = """    const ma20Rising = fixedMA20[i] !== null && fixedMA20[i-1] !== null && fixedMA20[i] > fixedMA20[i-1];
    if (allAbove(i) && !allAbove(i-1) && ma20Rising) {"""

content = content.replace(OLD_RISING, NEW_RISING)

# ── 替换绿/粉三角逻辑：MA1下穿MA2 → DIF拐点 ──────────────────────────────────
OLD_GREEN = """  // 每个橙三角之后，MA1 和 MA2 同时首次下穿 MA4 → 绿色倒三角；其后一根 → 粉色倒三角
  const greenPoints     = [];
  const nextKlinePoints = [];
  for (const startIdx of orangeIdxs) {
    for (let i = startIdx + 1; i < closes.length; i++) {
      if (fixedMA1[i] == null || fixedMA2[i] == null || fixedMA4[i] == null) continue;
      if (fixedMA1[i-1] == null || fixedMA2[i-1] == null) continue;
      if (fixedMA1[i-1] !== null && fixedMA2[i-1] !== null &&
          fixedMA1[i-1] >= fixedMA2[i-1] && fixedMA1[i] < fixedMA2[i]) {
        greenPoints.push({ value: [dates[i], +(highs[i] * 1.007).toFixed(2)] });
        if (i + 1 < closes.length) {
          nextKlinePoints.push({ value: [dates[i+1], +(highs[i+1] * 1.007).toFixed(2)] });
        }
        break;
      }
    }
  }"""

NEW_GREEN = """  // 每个橙三角之后，DIF线第一个拐点 → 绿色倒三角（K线+MACD）；其后一根 → 粉色倒三角
  const greenKline      = [];
  const greenMACD       = [];
  const nextKlinePoints = [];
  for (const startIdx of orangeIdxs) {
    for (let i = startIdx + 1; i < dif.length - 1; i++) {
      if (dif[i] == null || dif[i-1] == null || dif[i+1] == null) continue;
      const isPeak   = dif[i] > dif[i-1] && dif[i] > dif[i+1];
      const isTrough = dif[i] < dif[i-1] && dif[i] < dif[i+1];
      if (isPeak || isTrough) {
        greenKline.push({ value: [dates[i], +(highs[i] * 1.007).toFixed(2)] });
        greenMACD.push({ value: [dates[i], dif[i]] });
        if (i + 1 < closes.length) {
          nextKlinePoints.push({ value: [dates[i+1], +(highs[i+1] * 1.007).toFixed(2)] });
        }
        break;
      }
    }
  }"""

content = content.replace(OLD_GREEN, NEW_GREEN)

# ── 替换 crossSeries 中的系列名和数据引用 ─────────────────────────────────────
content = content.replace("name: 'MA1/2/4/6同时上穿MA8'", "name: 'MA5/10/15同时上穿MA20'")

OLD_SERIES = """    {
      name: 'MA1&MA2首次下穿MA4',
      type: 'scatter',
      xAxisIndex: 0, yAxisIndex: 0,
      data: greenPoints,
      symbol: 'triangle',
      symbolRotate: 180,
      symbolSize: 12,
      color: '#39ff14',
      itemStyle: { color: '#39ff14', opacity: 1 },
      label: { show: false },
    },"""

NEW_SERIES = """    {
      name: 'DIF拐点(K线)',
      type: 'scatter',
      xAxisIndex: 0, yAxisIndex: 0,
      data: greenKline,
      symbol: 'triangle',
      symbolRotate: 180,
      symbolSize: 12,
      color: '#39ff14',
      itemStyle: { color: '#39ff14', opacity: 1 },
      label: { show: false },
    },
    {
      name: 'DIF拐点(MACD)',
      type: 'scatter',
      xAxisIndex: 1, yAxisIndex: 1,
      data: greenMACD,
      symbol: 'triangle',
      symbolRotate: 180,
      symbolSize: 12,
      color: '#39ff14',
      itemStyle: { color: '#39ff14', opacity: 1 },
      label: { show: false },
    },"""

content = content.replace(OLD_SERIES, NEW_SERIES)

# ── 写出 ───────────────────────────────────────────────────────────────────────
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(content)

print(f"生成完毕 → {OUTPUT}（{len(data)}条月K线数据）")
