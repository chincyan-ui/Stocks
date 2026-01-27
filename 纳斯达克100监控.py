import yfinance as yf
import pandas as pd
import requests
import os
import statistics  # 新增：用于计算平均值和中位数

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

def 获取回撤报告():
    print(f"🚀 正在下载 {len(TICKERS)} 只股票的历史数据...")
    
    try:
        # 使用 period="max" 下载数据
        data = yf.download(TICKERS, period="max", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 下载失败: {e}"

    结果列表 = []
    
    for ticker in TICKERS:
        try:
            # 兼容多列索引和单列索引的情况
            if isinstance(data.columns, pd.MultiIndex):
                if ticker not in data.columns.levels[0]: continue
                df = data[ticker].dropna()
            else:
                df = data.dropna() # 只有一个股票的情况
                
            if df.empty or len(df) < 5: 
                continue
            
            # 计算回撤：(现价 - 历史最高价) / 历史最高价
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

    # --- 新增功能：统计平均值和中位数 ---
    all_drawdowns = [x['drawdown'] for x in 结果列表]
    avg_drawdown = statistics.mean(all_drawdowns)
    median_drawdown = statistics.median(all_drawdowns)

    # 统计回撤超过 50% 的比例
    total_count = len(结果列表)
    crash_count = len([d for d in all_drawdowns if d <= -50])
    crash_ratio = (crash_count / total_count) * 100

    # 排序：回撤最大的排在前面
    结果列表.sort(key=lambda x: x['drawdown'])
    
    # --- 构建报告内容 ---
    消息 = [
        "📊 **纳斯达克100成分股回撤统计**",
        "---",
        f"📈 统计样本：`{total_count}` 只股票",
        f"📉 平均回撤：**{avg_drawdown:.2f}%**",
        f"⚖️ 回撤中位数：**{median_drawdown:.2f}%**",
        f"⚠️ 回撤 > 50% 占比：**{crash_ratio:.2f}%** ({crash_count}只)",
        "---",
        f"🔥 **深蹲名单 (Top 15)**"
    ]
    
    for i, item in enumerate(结果列表[:15], 1):
        if item['drawdown'] <= -50:
            tag = "🆘"
        elif item['drawdown'] <= -30:
            tag = "🚨"
        else:
            tag = "📉"
            
        消息.append(f"{i}. {tag} **{item['symbol']}**")
        消息.append(f"    ▫️ 距最高位: `{item['drawdown']:.2f}%`")
        消息.append(f"    ▫️ 价格: `{item['current']:.2f}` / ATH: `{item['ath']:.2f}`")
        
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
