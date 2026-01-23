import os
import requests
from longbridge.openapi import QuoteContext, Config

# 1. 配置环境
APP_KEY = os.getenv("LB_APP_KEY")
APP_SECRET = os.getenv("LB_APP_SECRET")
ACCESS_TOKEN = os.getenv("LB_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def get_top_10_turnover():
    config = Config(APP_KEY, APP_SECRET, ACCESS_TOKEN)
    ctx = QuoteContext(config)
    
    # 2. 获取美股热门股票池 (这里以美股主要科技股为例，或使用长桥的证券候选池)
    # 长桥目前没有直接的 "全市场成交额排行" 接口，通常做法是获取预设的板块快照
    # 我们可以获取纳斯达克100或热门股票的快照
    symbols = ["AAPL.US", "TSLA.US", "NVDA.US", "MSFT.US", "AMZN.US", 
               "GOOG.US", "META.US", "AMD.US", "NFLX.US", "BABA.US", 
               "COIN.US", "PLTR.US", "MARA.US", "MSTR.US", "SMCI.US"]
    
    snapshots = ctx.quote(symbols)
    
    # 3. 提取数据并按成交额排序
    data_list = []
    for s in snapshots:
        data_list.append({
            "symbol": s.symbol,
            "turnover": float(s.turnover),  # 成交金额
            "last_done": float(s.last_done), # 最新价
            "change_rate": float(s.pre_close_price) # 用于计算涨跌幅
        })
    
    # 按成交额降序排列
    top_10 = sorted(data_list, key=lambda x: x['turnover'], reverse=True)[:10]
    return top_10

def format_amount(amount):
    if amount >= 1e8:
        return f"${amount/1e8:.2f}亿"
    return f"${amount/1e4:.2f}万"

def send_telegram(data):
    message = "🏛 **长桥美股成交额 Top 10**\n\n"
    for i, s in enumerate(data, 1):
        message += f"{i}. **{s['symbol']}**\n"
        message += f"   成交额: `{format_amount(s['turnover'])}` | 现价: `${s['last_done']}`\n"
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    try:
        top_data = get_top_10_turnover()
        send_telegram(top_data)
    except Exception as e:
        print(f"Error: {e}")
