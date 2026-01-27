import yfinance as yf
import pandas as pd
import requests
import os

# 75个标的 (已去重)
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
        # 下载数据，从2019年底开始以获取2020年初的ATH基准
        data = yf.download(all_symbols, start="2019-10-01", end="2026-01-01", auto_adjust=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何数据，请检查 yfinance 状态。"

    close_data = data['Close']
    high_data = data['High']
    
    # 预计算所有标的历史至今的最高价 (ATH) 矩阵
    ath_matrix = high_data[TICKERS].expanding().max()

    report_lines = ["🎯 **QQQ 年度顶点日成分股回撤统计**", "---"]

    for year in range(2020, 2026):
        # 锁定当年的数据
        year_mask = (data.index.year == year)
        if not year_mask.any():
            continue
            
        qqq_year = data.loc[year_mask, 'QQQ']
        
        # 1. 找到 QQQ 这一年的最高值及日期
        qqq_max_val = qqq_year['High'].max()
        peak_date = qqq_year['High'].idxmax()
        peak_date_str = peak_date.strftime('%Y-%m-%d')

        # 2. 获取顶点日当天的截面数据
        # 使用 .loc[peak_date] 提取那一天所有股票的收盘价和当时的历史最高价
        prices_at_peak = close_data.loc[peak_date, TICKERS]
        aths_at_peak = ath_matrix.loc[peak_date, TICKERS]

        # 3. 计算回撤 (Current Close - History High) / History High
        drawdowns = (prices_at_peak - aths_at_peak) / aths_at_peak * 100
        drawdowns = drawdowns.dropna() # 剔除尚未上市或数据缺失的股票
        
        avg_dd = drawdowns.mean()
        med_dd = drawdowns.median()

        # 组装报告
        report_lines.append(f"📅 **{year} 年度**")
        report_lines.append(f"🔝 QQQ 峰值: `{qqq_max_val:.2f}` ({peak_date_str})")
        report_lines.append(f"📊 75强平均回撤: `{avg_dd:.2f}%`")
        report_lines.append(f"⚖️ 75强中位回撤: `{med_dd:.2f}%`")
        report_lines.append("---")

    return "\n".join(report_lines)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n⚠️ 缺失 Telegram 配置，结果如下：\n")
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
        print("✅ 报告已推送到 Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    content = 历史回撤分析()
    推送到TG(content)
