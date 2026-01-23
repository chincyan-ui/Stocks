import os
import requests
from longport.openapi import QuoteContext, Config

# 从 GitHub Secrets 中读取环境变量
APP_KEY = os.getenv("LB_APP_KEY")
APP_SECRET = os.getenv("LB_APP_SECRET")
ACCESS_TOKEN = os.getenv("LB_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def format_amount(amount):
    """格式化交易金额显示"""
    if amount >= 1e9:
        return f"${amount/1e9:.2f}B (十亿)"
    elif amount >= 1e6:
        return f"${amount/1e6:.2f}M (百万)"
    return f"${amount:,.2f}"

def get_top_turnover():
    # 1. 初始化长桥配置
    config = Config(APP_KEY, APP_SECRET, ACCESS_TOKEN)
    ctx = QuoteContext(config)
    
    # 2. 定义监测的股票池 (美股热门标的)
    # 提示：您可以根据需要增加更多代码，长桥 quote 接口支持批量查询
    symbols = [
        "AAPL.US", "TSLA.US", "NVDA.US", "MSFT.US", "AMZN.US", 
        "GOOG.US", "META.US", "AMD.US", "NFLX.US", "BABA.US",
        "COIN.US", "PLTR.US", "MSTR.US", "SMCI.US", "AVGO.US"
    ]
    
    # 3. 获取实时快照数据
    try:
        snapshots = ctx.quote(symbols)
        
        data_list = []
        for s in snapshots:
            data_list.append({
                "symbol": s.symbol,
                "turnover": float(s.turnover),  # 当日累积成交额
                "last_done": float(s.last_done), # 最新成交价
                "high": float(s.high),           # 当日最高
                "low": float(s.low)              # 当日最低
            })
        
        # 4. 按成交额 (Turnover) 降序排列并取前 10
        top_10 = sorted(data_list, key=lambda x: x['turnover'], reverse=True)[:10]
        return top_10
    except Exception as e:
        print(f"获取长桥数据失败: {e}")
        return []

def send_telegram(data):
    if not data:
        return

    message = "📊 **LongPort 美股今日成交额排行**\n"
    message += "*(基于样本池实时快照统计)*\n\n"
    
    for i, s in enumerate(data, 1):
        message += f"{i}. **{s['symbol']}**\n"
        message += f"   💰 成交额: `{format_amount(s['turnover'])}` \n"
        message += f"   💵 现价: `${s['last_done']}` (H: {s['high']} / L: {s['low']})\n\n"
    
    # Telegram Bot API 调用
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Telegram 消息推送成功")
    else:
        print(f"Telegram 推送失败: {response.text}")

if __name__ == "__main__":
    top_stocks = get_top_turnover()
    send_telegram(top_stocks)
