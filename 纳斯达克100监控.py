import yfinance as yf
import pandas as pd
import requests
import os

# 1. 纳指 100 最新成分股列表 (包含双重股权)
TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN", 
    "AMZN", "ANSS", "APP", "ASML", "AVGO", "AXON", "AZN", "BKR", "BKNG", "BIIB", 
    "CDNS", "CEG", "CHTR", "CPRT", "CSCO", "CSX", "CTAS", "CTSH", "DASH", "DDOG", 
    "DXCM", "EA", "EXC", "FANG", "FAST", "FTNT", "GEHC", "GILD", "GOOG", "GOOGL", 
    "HON", "IDXX", "ILMN", "INTC", "INTU", "ISRG", "KDP", "KHC", "KLAC", "LRCX", 
    "LIN", "LULU", "MAR", "MCHP", "MDB", "MELI", "META", "MNST", "MRNA", "MRVL", 
    "MSFT", "MU", "NFLX", "NVDA", "NXPI", "ODFL", "OKTA", "ORLY", "PANW", "PAYX", 
    "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM", "REGN", "ROP", "ROST", "SBUX", 
    "SIRI", "SNPS", "TEAM", "TMUS", "TSLA", "TTD", "TXN", "VRSK", "VRTX", "WBA", 
    "WBD", "WDC", "WDAY", "XEL", "ZSC"
]

# 配置 Telegram 环境变量 (请确保已在系统中设置)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤报告():
    print(f"🚀 正在获取 {len(TICKERS)} 只成分股的历史数据...")
    
    # 批量下载数据：auto_adjust=True 实现前复权，threads=True 开启多线程
    # 取 period="max" 以获得真正的历史最高点 (ATH)
    try:
        data = yf.download(TICKERS, period="max", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    结果列表 = []

    for ticker in TICKERS:
        try:
            # 提取单只股票数据
            df = data[ticker].dropna()
            if df.empty or len(df) < 2:
                continue
            
            # 核心计算：盘中最高价 (High) vs 最新收盘价 (Close)
            历史最高 = df['High'].max()
            当前价 = df['Close'].iloc[-1]
            回撤 = (当前价 - 历史最高) / 历史最高 * 100
            
            结果列表.append({
                "symbol": ticker,
                "current": 当前价,
                "ath": 历史最高,
                "drawdown": 回撤
            })
        except:
            continue

    # 按回撤幅度从大到小排序 (数值越小代表跌得越多)
    结果列表.sort(key=lambda x: x['drawdown'])
    
    # 取前 10 名
    Top10 = 结果列表[:10]

    # 构建 Markdown 消息内容
    消息 = ["📊 **纳指 100 回撤最大 Top 10**", "*(基于前复权历史盘中最高点)*", "---"]
    for i, 项 in enumerate(Top10, 1):
        # 回撤超过 30% 标记为警报
        标志 = "🚨" if 项['drawdown'] < -30 else "📉"
        消息.append(f"{i}. {标志} **{项['symbol']}**")
        消息.append(f"   ▫️ 距最高位: **{项['drawdown']:.2f}%**")
        消息.append(f"   ▫️ 当前/最高: `{项['current']:.2f}` / `{项['ath']:.2f}`")
        消息.append("")
        
    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("⚠️ 环境变量 TOKEN 或 CHAT_ID 缺失，仅在控制台打印结果：")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {
        "chat_id": CHAT_ID,
        "text": 文本,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(URL, data=参数, timeout=15)
        r.raise_for_status()
        print("✅ 报告已推送到 Telegram")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    报告 = 获取回撤报告()
    推送到TG(报告)
