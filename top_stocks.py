import os
import requests
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, Market

def send_tg(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})

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
        print("正在调用 get_trade_rank 获取热度排名...")

        # 2026版 SDK 正确方法名：get_trade_rank
        rankings = client.get_trade_rank(Market.US)

        if not rankings:
            send_tg("⚠️ 未能获取到成交排名数据。")
            return

        # 排名通常按热度/成交额降序，我们取前 3
        top_3 = rankings[:3]
        
        msg = ["🐯 **美股收盘成交额/热度 Top 3**"]
        for i, row in enumerate(top_3, 1):
            # 兼容性读取属性：latest_price, symbol, amount
            symbol = getattr(row, 'symbol', 'N/A')
            price = getattr(row, 'latest_price', 0)
            # 某些版本可能叫 volume_trade 或 amount
            amount = getattr(row, 'amount', getattr(row, 'volume_trade', 0))
            
            # 计算涨跌幅 (如果可用)
            pre_close = getattr(row, 'pre_close', 0)
            change_str = ""
            if pre_close > 0:
                change = ((price - pre_close) / pre_close) * 100
                change_str = f"({change:+.2f}%)"

            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💰 价格: ${price:.2f} {change_str}")
            if amount > 0:
                msg.append(f"   📊 成交额: ${amount/1e8:.2f} 亿")
        
        send_tg("\n".join(msg))
        print("推送成功！")

    except Exception as e:
        send_tg(f"❌ 脚本执行失败: `{str(e)}`")

if __name__ == "__main__":
    main()
