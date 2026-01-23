import os
import requests
import pandas as pd
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, Market, MarketRankingField

# --- 工具函数：发送 Telegram 消息 ---
def send_tg(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        print("未配置 Telegram Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id, 
        'text': text, 
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram 推送失败: {e}")

# --- 核心逻辑：获取老虎 API 客户端 ---
def get_client():
    # 修正版：不再在 __init__ 中传 sandbox 参数
    config = TigerOpenClientConfig()
    config.tiger_id = os.getenv("TIGER_ID")
    config.private_key = os.getenv("TIGER_PRIVATE_KEY")
    config.language = Language.zh_CN
    
    # 显式设置环境：False 为实盘，True 为模拟盘
    config.sandbox = False 
    
    return QuoteClient(config)

def main():
    try:
        client = get_client()
        print("正在获取美股成交额排行榜...")

        # 获取美股市场排名（按成交额 AMOUNT 排序）
        # 返回的是一个包含 StockRanking 对象的列表
        rankings = client.get_market_rankings(
            market=Market.US, 
            field=MarketRankingField.AMOUNT
        )

        if not rankings:
            send_tg("⚠️ 未获取到今日行情数据，请检查市场是否开盘。")
            return

        # 提取前 3 名
        top_3 = rankings[:3]
        
        msg = ["🐯 **美股今日成交额 Top 3**"]
        for i, row in enumerate(top_3, 1):
            symbol = row.symbol
            # row 对象属性可能随版本变化，通常包含 latest_price, amount, pre_close
            price = getattr(row, 'latest_price', 0)
            amount = getattr(row, 'amount', 0)
            pre_close = getattr(row, 'pre_close', 0)
            
            # 计算涨跌幅
            change_pct = ((price - pre_close) / pre_close * 100) if pre_close else 0
            # 成交额换算为亿美元
            amount_usd = amount / 1e8

            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💰 成交额: ${amount_usd:.2f} 亿")
            msg.append(f"   📈 价格: ${price:.2f} ({change_pct:+.2f}%)")
        
        msg_text = "\n".join(msg)
        print(msg_text)
        send_tg(msg_text)

    except Exception as e:
        error_msg = f"❌ 脚本运行出错:\n`{str(e)}`"
        print(error_msg)
        send_tg(error_msg)

if __name__ == "__main__":
    main()
