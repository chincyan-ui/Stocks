import os
import requests

# 1. 核心修正：在导入任何 longport 组件之前设置环境变量
# 这样 SDK 在内部初始化时会自动识别并连接到国内节点
os.environ["LONGPORT_REGION"] = "cn"

from longport.openapi import QuoteContext, Config

# 获取环境变量
APP_KEY = os.getenv("LB_APP_KEY")
APP_SECRET = os.getenv("LB_APP_SECRET")
ACCESS_TOKEN = os.getenv("LB_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def get_top_turnover():
    # 2. 移除引发 TypeError 的 region 参数
    config = Config(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        access_token=ACCESS_TOKEN
    )
    
    try:
        # 显式使用 context 管理，确保连接正确关闭
        with QuoteContext(config) as ctx:
            # 定义核心大盘股池
            symbols = [
                "AAPL.US", "MSFT.US", "GOOG.US", "AMZN.US", "NVDA.US", "META.US", "TSLA.US",
                "AVGO.US", "V.US", "JPM.US", "UNH.US", "MA.US", "WMT.US", "LLY.US", "XOM.US",
                "JNJ.US", "PG.US", "ORCL.US", "HD.US", "COST.US", "ABBV.US", "MRK.US", "AMD.US"
            ]
            
            snapshots = ctx.quote(symbols)
            
            # 过滤市值 > 2000亿 并 提取数据
            data = [
                {"s": s.symbol, "t": float(s.turnover)} 
                for s in snapshots if float(s.market_val) >= 2000 * 1e8
            ]
            
            return sorted(data, key=lambda x: x['t'], reverse=True)[:10]
    except Exception as e:
        print(f"执行出错: {e}")
        return []

def send_telegram(data):
    if not data: 
        print("没有符合条件的数据发送")
        return
        
    msg = "💰 **美股成交额 Top 10 (市值 > $200B)**\n\n"
    for i, s in enumerate(data, 1):
        msg += f"{i}. `{s['s']}` : **${s['t']/1e9:.2f}B**\n"
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print("Telegram 推送成功")
    except Exception as e:
        print(f"TG 发送失败: {e}")

if __name__ == "__main__":
    result = get_top_turnover()
    send_telegram(result)
