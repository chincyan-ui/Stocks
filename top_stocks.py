import os
import requests
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, Market

# --- 配置 ---
def get_client():
    config = TigerOpenClientConfig(sandbox=False)
    config.tiger_id = os.getenv("TIGER_ID")
    config.private_key = os.getenv("TIGER_PRIVATE_KEY")
    config.language = Language.zh_CN
    return QuoteClient(config)

def send_tg(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})

def main():
    client = get_client()
    
    # 1. 获取美股全榜单（按照成交额排序）
    # 老虎接口：get_market_rankings
    # 这里的参数根据老虎最新SDK调整，获取美股成交额最大的股票
    try:
        # 获美股成交额排名
        rankings = client.get_market_rankings(market=Market.US,排序字段='amount') 
        # 注意：实际SDK调用可能为 get_market_rankings(Market.US, 'amount')
        # 这里演示取前 3 名
        top_3 = rankings[:3]
        
        msg = ["💰 **美股今日成交额 Top 3**"]
        for i, row in enumerate(top_3, 1):
            name = getattr(row, 'name', row.symbol)
            amount = getattr(row, 'amount', 0) / 1e8  # 换算成亿元
            price = getattr(row, 'latest_price', 0)
            change = getattr(row, 'pre_close', 0)
            pc = ((price - change) / change * 100) if change else 0
            
            msg.append(f"{i}. **{name}** ({row.symbol})")
            msg.append(f"   💸 成交额: {amount:.2f} 亿美元")
            msg.append(f"   📈 最新价: ${price} ({pc:+.2f}%)")
        
        send_tg("\n".join(msg))
        print("推送成功")
        
    except Exception as e:
        send_tg(f"❌ 脚本执行错误: {str(e)}")

if __name__ == "__main__":
    main()
