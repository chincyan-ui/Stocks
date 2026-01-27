import yfinance as yf
import pandas as pd
import requests
import os
import statistics

# 固定纳指市值前 50 名核心资产 (去除了变动较大的小市值，保留了权重的核心)
TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOG", "GOOGL", "AVGO", "TSLA", "COST",
    "NFLX", "ASML", "AMD", "AZN", "LIN", "TMUS", "ADBE", "PEP", "CSCO", "ISRG",
    "TXN", "AMAT", "QCOM", "AMGN", "INTU", "BKNG", "PDD", "HON", "VRTX", "LRCX",
    "PANW", "REGN", "MU", "ADI", "KLAC", "SNPS", "ADP", "CDNS", "MELI", "MDLZ",
    "GILD", "PYPL", "MAR", "CTAS", "ORLY", "CRWD", "CSX", "ADSK", "NXPI", "PCAR"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 历史回撤分析():
    print(f"🚀 开始分析固定 50 只核心标的 (2020-2025)...")
    
    # 稍微多下载一点数据确保 2020 年初有 ATH 基准
    try:
        data = yf.download(TICKERS, start="2019-10-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何数据，请检查网络或 Tickers 列表。"

    report_lines = ["📊 **纳指 50 强历史回撤深度统计**", "---"]
    
    # 遍历 2020 到 2025 年
    for year in range(2020, 2026):
        year_dates = data.index[data.index.year == year]
        if year_dates.empty:
            continue
        
        daily_stats = []
        for current_date in year_dates:
            drawdowns = []
            for ticker in TICKERS:
                try:
                    # 获取该股截止到当前日期的所有收盘价数据
                    subset = data[ticker].loc[:current_date].dropna()
                    if len(subset) < 2:
                        continue
                        
                    # 以该日期前的最高价作为 ATH
                    ath = subset['High'].max()
                    curr_price = subset['Close'].iloc[-1]
                    
                    dd = (curr_price - ath) / ath * 100
                    drawdowns.append(dd)
                except:
                    continue
            
            if drawdowns:
                daily_stats.append({
                    "date": current_date.strftime('%Y-%m-%d'),
                    "avg": statistics.mean(drawdowns),
                    "med": statistics.median(drawdowns)
                })
        
        if daily_stats:
            # 找到回撤数值最小（最深）和最大（最浅）的日期
            max_avg_day = min(daily_stats, key=lambda x: x['avg']) # 例如 -25%
            min_avg_day = max(daily_stats, key=lambda x: x['avg']) # 例如 -2%
            max_med_day = min(daily_stats, key=lambda x: x['med'])
            min_med_day = max(daily_stats, key=lambda x: x['med'])

            report_lines.append(f"📅 **{year} 年度**")
            report_lines.append(f"▫️ 平均最深: `{max_avg_day['avg']:.2f}%` ({max_avg_day['date']})")
            report_lines.append(f"▫️ 平均最浅: `{min_avg_day['avg']:.2f}%` ({min_avg_day['date']})")
            report_lines.append(f"▫️ 中位最深: `{max_med_day['med']:.2f}%` ({max_med_day['date']})")
            report_lines.append(f"▫️ 中位最浅: `{min_med_day['med']:.2f}%` ({min_med_day['date']})")
            report_lines.append("---")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("⚠️ 环境变量缺失，本地直接打印结果：\n")
        print(文本)
        return
        
    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": 文本, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(URL, json=payload, timeout=30)
        r.raise_for_status()
        print("✅ 报告已成功推送到 Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    report_content = 历史回撤分析()
    推送到TG(report_content)
