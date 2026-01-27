import yfinance as yf
import pandas as pd
import requests
import os

# 60个标的 (已去重)
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
    print(f"🚀 开始分析 QQQ 年度顶点日的成分股回撤 (2020-2025)...")
    
    # 将 QQQ 加入下载列表
    all_symbols = TICKERS + ["QQQ"]
    
    try:
        # 下载数据 (从2019年底开始，确保2020年初有历史最高价基准)
        data = yf.download(all_symbols, start="2019-10-01", end="2026-01-01", auto_adjust=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何数据，请检查网络或 yfinance 状态。"

    # 处理多层索引 (yfinance 返回结构为 [Price, Ticker])
    # 提取 Close 和 High 矩阵，使列名直接变为 Ticker
    close_df = data['Close']
    high_df = data['High']
    
    # 预计算 60 只股票历史至今的最高价矩阵 (ATH)
    ath_matrix = high_df[TICKERS].expanding().max()

    report_lines = ["🎯 **QQQ 年度顶点日成分股回撤统计**", "---"]

    for year in range(2020, 2026):
        # 筛选当年的数据行
        year_mask = (data.index.year == year)
        if not year_mask.any():
            continue
            
        # 提取当年的 QQQ 最高价序列
        qqq_high_year = high_df.loc[year_mask, 'QQQ']
        
        # 剔除空值，防止无法计算 idxmax
        qqq_high_year = qqq_high_year.dropna()
        if qqq_high_year.empty:
            continue

        # 1. 定位 QQQ 这一年的最高值及发生的日期
        qqq_max_val = qqq_high_year.max()
        peak_date = qqq_high_year.idxmax()
        peak_date_str = peak_date.strftime('%Y-%m-%d')

        # 2. 提取顶点日当天的截面数据
        # prices_at_peak: 60只股在 peak_date 的收盘价
        # aths_at_peak: 60只股在 peak_date 及其之前的历史最高价
        prices_at_peak = close_df.loc[peak_date, TICKERS]
        aths_at_peak = ath_matrix.loc[peak_date, TICKERS]

        # 3. 计算回撤百分比: (收盘价 - 历史最高) / 历史最高 * 100
        drawdowns = (prices_at_peak - aths_at_peak) / aths_at_peak * 100
        
        # 剔除那一天还没上市或数据缺失的股票 (如 DASH, SNOW 等)
        drawdowns = drawdowns.dropna()
        
        if drawdowns.empty:
            continue

        avg_dd = drawdowns.mean()
        med_dd = drawdowns.median()
        
        # 额外统计：回撤超过 10% 的股票数量
        falling_stocks = (drawdowns < -10).sum()
        falling_pct = (falling_stocks / len(drawdowns)) * 100

        # 组装报告
        report_lines.append(f"📅 **{year} 年度**")
        report_lines.append(f"🔝 QQQ 峰值: `{qqq_max_val:.2f}` ({peak_date_str})")
        report_lines.append(f"📊 60强平均回撤: `{avg_dd:.2f}%`")
        report_lines.append(f"⚖️ 60强中位回撤: `{med_dd:.2f}%`")
        report_lines.append(f"📉 回撤 >10% 占比: `{falling_pct:.1f}%` ({falling_stocks}只)")
        report_lines.append("---")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n⚠️ 缺失配置，直接打印结果：\n")
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
        print("✅ 报告已成功发送至 Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    content = 历史回撤分析()
    推送到TG(content)
