import yfinance as yf
import pandas as pd
import requests
import os

# 75个标的
TICKERS = list(set([
    "AAPL", "MSFT", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ADBE", "COST", 
    "PEP", "CSCO", "NFLX", "CMCSA", "AMD", "TMUS", "TXN", "AMAT", "QCOM", "INTC", 
    "ISRG", "AMGN", "HON", "LRCX", "BKNG", "MU", "VRTX", "REGN", "ADP", "KLAC", 
    "MDLZ", "PANW", "SNPS", "CDNS", "PYPL", "ADI", "ASML", "MAR", "CSX", "ORLY", 
    "MNST", "CTAS", "INTU", "ROP", "ADSK", "PAYX", "DXCM", "IDXX", "KDP", "GILD", 
    "LULU", "CHRW", "EA", "PCAR", "EBAY", "ROST", "FAST", "CPRT", "VRSK", "ANSS", 
    "KHC", "BIIB", "ALGN", "WDC", "MCHP", "NTES", "MELI", "ZS", "FTNT", "NXPI", 
    "EXPE", "JD", "VRSN", "CHTR"
]))

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def 历史回撤分析():
    print(f"🚀 开始分析 QQQ 年度顶点日的成分股回撤 (2020-2025)...")
    
    all_symbols = TICKERS + ["QQQ"]
    
    try:
        # 下载数据
        data = yf.download(all_symbols, start="2019-10-01", end="2026-01-01", auto_adjust=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何数据。"

    # 核心修复：显式提取 Close 和 High 矩阵
    # 这样得到的 close_df 列名直接就是 Ticker，不再有 MultiIndex 烦恼
    close_df = data['Close']
    high_df = data['High']
    
    # 预计算 75 只股票历史至今的最高价
    ath_matrix = high_df[TICKERS].expanding().max()

    report_lines = ["🎯 **QQQ 年度顶点日成分股回撤统计**", "---"]

    for year in range(2020, 2026):
        # 筛选当年的数据
        year_mask = (data.index.year == year)
        if not year_mask.any():
            continue
            
        # 修复点：直接从 high_df 中提取 QQQ 列
        qqq_high_year = high_df.loc[year_mask, 'QQQ']
        
        if qqq_high_year.isnull().all():
            continue

        # 1. 找到 QQQ 这一年的最高值及日期
        qqq_max_val = qqq_high_year.max()
        peak_date = qqq_high_year.idxmax()
        peak_date_str = peak_date.strftime('%Y-%m-%d')

        # 2. 获取顶点日当天的截面数据
        prices_at_peak = close_df.loc[peak_date, TICKERS]
        aths_at_peak = ath_matrix.loc[peak_date, TICKERS]

        # 3. 计算回撤
        drawdowns = (prices_at_peak - aths_at_peak) / aths_at_peak * 100
        drawdowns = drawdowns.dropna()
        
        avg_dd = drawdowns.mean()
        med_dd = drawdowns.median()
        # 统计回撤超过 10% 的股票占比
        bear_count = (drawdowns < -10).sum()
        bear_pct = (bear_count / len(drawdowns)) * 100

        # 组装报告
        report_lines.append(f"📅 **{year} 年度**")
        report_lines.append(f"🔝 QQQ 峰值: `{qqq_max_val:.2f}` ({peak_date_str})")
        report_lines.append(f"📊 75强平均回撤: `{avg_dd:.2f}%`")
        report_lines.append(f"⚖️ 75强中位回撤: `{med_dd:.2f}%`")
        report_lines.append(f"📉 回撤 >10% 比例: `{bear_pct:.1f}%` ({bear_count}只)")
        report_lines.append("---")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print(文本)
        return
        
    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        requests.post(URL, json=payload, timeout=30).raise_for_status()
        print("✅ 报告已推送到 Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    content = 历史回撤分析()
    推送到TG(content)
