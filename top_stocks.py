import os
import requests
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, Market

# --- 工具函数：发送 Telegram 消息 ---
def send_tg(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        print("未配置 Telegram Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload).raise_for_status()
    except Exception as e:
        print(f"Telegram 推送失败: {e}")

# --- 核心逻辑：获取老虎 API 客户端 ---
def get_client():
    config = TigerOpenClientConfig()
    config.tiger_id = os.getenv("TIGER_ID")
    config.private_key = os.getenv("TIGER_PRIVATE_KEY")
    config.language = Language.zh_CN
    config.sandbox = False 
    return QuoteClient(config)

def main():
    try:
        client = get_client()
        print("正在获取美股成交额排行榜...")

        # 尝试调用 get_market_rank (新版 SDK 通常去掉 ing)
        # 如果这个还报错，脚本会进入 except 打印出 client 的所有可用方法供排查
        try:
            rankings = client.get_market_rank(
                market=Market.US, 
                field='amount' 
            )
        except AttributeError:
            # 备选方案：如果是非常新的版本，可能会改名为 get_rankings
            rankings = client.get_rankings(market=Market.US, field='amount')

        if not rankings:
            send_tg("⚠️ 未获取到行情数据。")
            return

        top_3 = rankings[:3]
        msg = ["🐯 **美股今日成交额 Top 3**"]
        
        for i, row in enumerate(top_3, 1):
            # 兼容对象属性或字典格式
            symbol = getattr(row, 'symbol', row.get('symbol') if isinstance(row, dict) else 'N/A')
            price = getattr(row, 'latest_price', row.get('latest_price', 0) if isinstance(row, dict) else 0)
            amount = getattr(row, 'amount', row.get('amount', 0) if isinstance(row, dict) else 0)
            pre_close = getattr(row, 'pre_close', row.get('pre_close', 0) if isinstance(row, dict) else 0)
            
            change_pct = ((price - pre_close) / pre_close * 100) if pre_close else 0
            
            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💸 成交额: ${amount/1e8:.2f} 亿")
            msg.append(f"   📈 价格: ${price:.2f} ({change_pct:+.2f}%)")
        
        send_tg("\n".join(msg))

    except Exception as e:
        # 如果再次失败，打印出 client 的所有属性，方便我们精准定位方法名
        methods = [m for m in dir(client) if not m.startswith('_')]
        error_info = f"❌ 脚本运行出错: `{str(e)}`\n\n可用方法列表: `{methods[:10]}...`"
        print(error_info)
        send_tg(error_info)

if __name__ == "__main__":
    main()
