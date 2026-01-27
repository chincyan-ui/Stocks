import yfinance as yf
import pandas as pd
import requests
import os

# 60个标的
TICKERS = list(set([
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX",
    "ASML", "AMD", "LIN", "TMUS", "PEP", "CSCO", "ADBE", "INTU", "QCOM", "ISRG",
    "TXN", "AMAT", "AMGN", "HON", "PLTR", "BKNG", "INTC", "GILD", "ADI", "ADP",
    "SNPS", "CDNS", "MAR", "CRWD", "PANW", "CSX", "REGN", "ORLY", "KLAC", "MNST",
    "ADSK", "MELI", "CTAS", "FTNT", "PYPL", "MCHP", "LRCX", "VRTX", "PDD", "DASH",
    "CDW", "ROP", "AEP", "DXCM", "APP", "CEG", "KDP", "SNOW", "WDAY", "IDXX"
]))

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def 历史回撤分析():
    print(f"🚀 开始分析数据...")
    all_symbols = TICKERS + ["QQQ"]
    
    try:
        # 下载从 2019 年至今的所有数据
        data = yf.download(all_symbols, start="2019-10-01", auto_adjust=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何数据。"

    close_df = data['Close']
    high_df = data['High']
    ath_matrix = high_df[TICKERS].expanding().max()

    report_lines = ["🎯 **QQQ 顶点日及最新回撤统计**", "---"]

    # --- 第一部分：2020-2025 历史年度顶点分析 ---
    for year in range(2020, 2026):
        year_mask = (data.index.year == year)
        if not year_mask.any(): continue
            
        qqq_high_year = high_df.loc[year_mask, 'QQQ'].dropna()
        if qqq_high_year.empty: continue

        qqq_max_val = qqq_high_year.max()
        peak_date = qqq_high_year.idxmax()
        
        # 计算该日 60 强回撤
        prices_at_peak = close_df.loc[peak_date, TICKERS]
        aths_at_peak = ath_matrix.loc[peak_date, TICKERS]
        drawdowns = (prices_at_peak - aths_at_peak) / aths_at_peak * 100
        drawdowns = drawdowns.dropna()
        
        report_lines.append(f"📅 **{year} 年度顶点**")
        report_lines.append(f"🔝 QQQ 峰值: `{qqq_max_val:.2f}` ({peak_date.strftime('%Y-%m-%d')})")
        report_lines.append(f"📊 平均回撤: `{drawdowns.mean():.2f}%` | 中位: `{drawdowns.median():.2f}%`指标")
        report_lines.append("---")

    # --- 第二部分：最新交易日实时快照 ---
    latest_date = close_df.index[-1]
    qqq_latest_price = close_df.loc[latest_date, 'QQQ']
    
    prices_latest = close_df.loc[latest_date, TICKERS]
    aths_latest = ath_matrix.loc[latest_date, TICKERS]
    
    latest_dd = (prices_latest - aths_latest) / aths_latest * 100
    latest_dd = latest_dd.dropna()

    report_lines.append(f"🔔 **最新收盘快照 ({latest_date.strftime('%Y-%m-%d')})**")
    report_lines.append(f"📈 QQQ 当前价格: `{qqq_latest_price:.2f}`")
    report_lines.append(f"📊 60强平均回撤: `{latest_dd.mean():.2f}%`")
    report_lines.append(f"⚖️ 60强中位回撤: `{latest_dd.median():.2f}%`")
    
    # 统计最新破位情况
    bear_10 = (latest_dd < -10).sum()
    bear_20 = (latest_dd < -20).sum()
    report_lines.append(f"⚠️ 回撤 >10%: `{bear_10}` 只 | >20%: `{bear_20}` 只")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print(文本); return
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
