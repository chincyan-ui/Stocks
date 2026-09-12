from datetime import datetime
import requests
import yfinance as yf


def get_all_us_tickers():
  tickers = set()

  # 1. 获取 NASDAQ 上市股票列表
  try:
    url_nasdaq = (
        "http://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    )
    res = requests.get(url_nasdaq)
    for line in res.text.splitlines()[1:-1]:
      parts = line.split("|")
      if len(parts) > 0:
        ticker = parts[0]
        # 替换特殊字符（如美股中的 BRK.B 对应 Yahoo 的 BRK-B）
        if "." in ticker:
          ticker = ticker.replace(".", "-")
        # 排除测试股票或优先股等（可选）
        if "^" not in ticker:
          tickers.add(ticker)
  except Exception as e:
    print(f"Error fetching NASDAQ tickers: {e}")

  # 2. 获取其他交易所（NYSE, AMEX 等）上市股票列表
  try:
    url_other = "http://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    res = requests.get(url_other)
    for line in res.text.splitlines()[1:-1]:
      parts = line.split("|")
      # parts[4] 通常为 ETF 标记 ("N" 表示非 ETF)，可根据需要决定是否过滤 ETF
      if len(parts) > 4:
        ticker = parts[0]
        if "." in ticker:
          ticker = ticker.replace(".", "-")
        if "^" not in ticker:
          tickers.add(ticker)
  except Exception as e:
    print(f"Error fetching other listed tickers: {e}")

  return list(tickers)


# 获取全量美股代码
print("正在从 NASDAQ 官方目录下载全量美股代码...")
all_tickers = get_all_us_tickers()
print(f"共获取到 {len(all_tickers)} 个代码，开始遍历筛选市值...")

large_caps = []

# 遍历全量股票检查市值
for ticker in all_tickers:
  try:
    stock = yf.Ticker(ticker)
    # 优先使用 fast_info 加快获取速度，若无则降级使用 info
    market_cap = stock.fast_info.get("market_cap", 0)
    if not market_cap:
      market_cap = stock.info.get("marketCap", 0)

    if market_cap and market_cap > 100e9:
      large_caps.append((ticker, market_cap))
      print(f"[Match] {ticker}: ${market_cap:,.0f}")
  except Exception:
    continue

# 按市值降序排序
large_caps.sort(key=lambda x: x[1], reverse=True)

# 生成 Markdown 内容
date_str = datetime.now().strftime("%Y-%m-%d")
content = f"### 美股市值 > 1000亿美元股票列表 ({date_str})\n\n"
content += "| 股票代码 | 市值 (美元) |\n| :--- | :--- |\n"
for ticker, cap in large_caps:
  content += f"| {ticker} | ${cap:,.0f} |\n"

with open("issue_body.md", "w", encoding="utf-8") as f:
  f.write(content)
