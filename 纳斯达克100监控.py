import yfinance as yf
import pandas as pd
import requests
import os

# 1. 更新后的标的列表 (已根据你的要求精准替换)
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

# 配置 Telegram 环境变量
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤报告():
    print(f"🚀 正在下载 {len(TICKERS)} 只股票的历史数据...")
    
    # 批量下载，threads=True 加速，auto_adjust=True 处理除权息
    try:
        data = yf.download(TICKERS, period="max", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 下载失败: {e}"

    结果列表 = []

    for ticker in TICKERS:
        try:
            # 兼容 yfinance 返回的 MultiIndex 结构
            if ticker not in data.columns.levels[0]:
                continue
                
            df = data[ticker].dropna()
            if df.empty or len(df) < 5: 
                continue
            
            # 计算回撤：基于历史所有交易日的盘中最高价 (ATH)
            ath = df['High'].max()
            current_price = df['Close'].iloc[-1]
            drawdown = (current_price - ath) / ath * 100
            
            结果列表.append({
                "symbol": ticker,
                "current": current_price,
                "ath": ath,
                "drawdown": drawdown
            })
        except:
            continue

    if not 结果列表:
        return "❌ 抱歉，未能获取到有效的股票分析数据。"

    # 按照回撤百分比排序（跌幅最大的在前面）
    结果列表.sort(key=lambda x: x['drawdown'])
    
    # 构建报告内容
    top_n = 15  
    消息 = [f"📊 **回撤观察名单 (Top {top_n})**", "---"]
    
    for i, item in enumerate(结果列表[:top_n], 1):
        if item['drawdown'] < -40:
            tag = "🆘"
        elif item['drawdown'] < -25:
            tag = "🚨"
        else:
            tag = "📉"
            
        消息.append(f"{i}. {tag} **{item['symbol']}**")
        消息.append(f"    ▫️ 距最高位: `{item['drawdown']:.2f}%`")
        消息.append(f"    ▫️ 现价/最高: `{item['current']:.2f}` / `{item['ath']:.2f}`")
        消息.append("")
        
    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("⚠️ 环境变量未配置，仅输出结果：\n")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": 文本,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(URL, json=payload, timeout=20)
        r.raise_for_status()
        print("✅ 报告已发送至 Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    report = 获取回撤报告()
    推送到TG(report)
