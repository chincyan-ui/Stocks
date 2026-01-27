import yfinance as yf
import pandas as pd
import requests
import os
import statistics

# 1. 标的列表
TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALNY", "AMAT", "AMD", 
    "AMGN", "AMZN", "APP", "ARM", "ASML", "AVGO", "AXON", "BKNG", "BKR", "CCEP", 
    "CDNS", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CSX", 
    "CTAS", "CTSH", "DASH", "DDOG", "DXCM", "EA", "EXC", "FANG", "FAST", "FER", 
    "FTNT", "GEHC", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "INSM", "INTC", "INTU", 
    "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "MAR", "MCHP", "MDLZ", "MELI", 
    "META", "MNST", "MPWR", "MRVL", "MSFT", "MSTR", "MU", "NFLX", "NVDA", "NXPI", 
    "ODFL", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM", 
    "REGN", "ROP", "ROST", "SBUX", "SHOP", "SNPS", "STX", "TEAM", "TMUS", "TRI", 
    "TSLA", "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDAY", "WDC", "WMT", "XEL", "ZS"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 历史回撤分析():
    print(f"🚀 开始分析 2020-2025 历史回撤数据...")
    
    # 下载数据（从 2019 开始以确保 2020 年初的 ATH 准确）
    try:
        data = yf.download(TICKERS, start="2019-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 下载失败: {e}"

    report_lines = ["📊 **2020-2025 历史回撤统计**", "---"]
    
    for year in range(2020, 2026):
        year_dates = data.index[data.index.year == year]
        if year_dates.empty: continue
        
        daily_stats = []
        for current_date in year_dates:
            drawdowns = []
            for ticker in TICKERS:
                try:
                    # 获取该股票截止到当前日期的所有历史
                    hist = data[ticker].loc[:current_date].dropna()
                    if len(hist) < 2: continue
                    ath = hist['High'].max()
                    price = hist['Close'].iloc[-1]
                    drawdowns.append((price - ath) / ath * 100)
                except: continue
            
            if drawdowns:
                daily_stats.append({
                    "date": current_date.strftime('%Y-%m-%d'),
                    "avg": statistics.mean(drawdowns),
                    "med": statistics.median(drawdowns)
                })
        
        if daily_stats:
            # 计算每年的极值日期
            max_avg = min(daily_stats, key=lambda x: x['avg'])  # 回撤最大（数值最小）
            min_avg = max(daily_stats, key=lambda x: x['avg'])  # 回撤最小（数值最大）
            max_med = min(daily_stats, key=lambda x: x['med'])
            min_med = max(daily_stats, key=lambda x: x['med'])

            report_lines.append(f"📅 **{year} 年度报告**")
            report_lines.append(f"▫️ 平均最大回撤: `{max_avg['avg']:.2f}%` ({max_avg['date']})")
            report_lines.append(f"▫️ 平均最小回撤: `{min_avg['avg']:.2f}%` ({min_avg['date']})")
            report_lines.append(f"▫️ 中位数最深: `{max_med['med']:.2f}%` ({max_med['date']})")
            report_lines.append(f"▫️ 中位数最浅: `{min_med['med']:.2f}%` ({min_med['date']})")
            report_lines.append("---")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("⚠️ 未找到环境变量，输出到控制台：\n", 文本)
        return
    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        r = requests.post(URL, json=payload, timeout=60)
        r.raise_for_status()
        print("✅ 历史极值报告已发送")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    content = 历史回撤分析()
    推送到TG(content)
