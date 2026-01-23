import os
import requests
from longport.openapi import QuoteContext, Config

# 环境配置
APP_KEY = os.getenv("LB_APP_KEY")
APP_SECRET = os.getenv("LB_APP_SECRET")
ACCESS_TOKEN = os.getenv("LB_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def get_top_turnover():
    config = Config(APP_KEY, APP_SECRET, ACCESS_TOKEN)
    ctx = QuoteContext(config)
    
    # 扫描核心大盘股池
    symbols = [
        "AAPL.US", "MSFT.US", "GOOG.US", "AMZN.US", "NVDA.US", "META.US", "TSLA.US",
        "AVGO.US", "V.US", "JPM.US", "UNH.US", "MA.US", "WMT.US", "LLY.US", "XOM.US",
        "JNJ.US", "PG.US", "ORCL.US", "HD.US", "COST.US", "ABBV.US", "MRK.US", "AMD.US",
        "CRM.US", "ADBE.US", "NFLX.US", "BAC.US", "ASML.US", "PDD.US"
    ]
    
    try:
        snapshots = ctx.quote(symbols)
        # 过滤市值 > 2000亿 并 提取数据
        data = [
            {"s": s.symbol, "t": float(s.turnover)} 
            for s in snapshots if float(s.market_val) >= 2000 * 1e8
        ]
        # 按成交额排序取前10
        return sorted(data, key=lambda x: x['t'], reverse=True)[:10]
    except:
        return []

def send_telegram(data):
    if not data: return
    
    # 构建极简文案
    msg = "💰 **美股成交额 Top 10 (市值 > $200B)**\n\n"
    for i, s in enumerate(data, 1):
        # 转换为十亿美元显示，保留两位小数
        msg += f"{i}. `{s['s']}` : **${s['t']/1e9:.2f}B**\n"
    
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                  json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_telegram(get_top_turnover())
