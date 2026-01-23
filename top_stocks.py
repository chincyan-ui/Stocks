import os
import requests
import pandas as pd
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, Market

def send_tg(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})
    except Exception as e:
        print(f"Telegram 推送失败: {e}")

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
        
        # 1. 获取热度排名 (只有代码，没价格)
        rankings = client.get_trade_rank(Market.US)
        if rankings is None or (isinstance(rankings, pd.DataFrame) and rankings.empty):
            send_tg("⚠️ 未能获取到成交排名数据。")
            return

        # 取前 3 名的代码
        top_symbols = rankings['symbol'].head(3).tolist()
        
        # 2. 【核心步骤】使用 get_briefs 批量获取这些股票的最新详情 (价格、成交额)
        details = client.get_briefs(top_symbols)
        
        if details is None or details.empty:
            send_tg("⚠️ 无法获取股票详情数据。")
            return

        msg = ["🐯 **美股收盘成交额/热度 Top 3**"]
        
        # 3. 遍历详情数据 (details 包含 latest_price, amount, pre_close)
        for i, (index, row) in enumerate(details.iterrows(), 1):
            symbol = row.get('symbol', 'N/A')
            price = row.get('latest_price', 0)
            amount = row.get('amount', 0)
            pre_close = row.get('pre_close', 0)
            
            # 格式化涨跌幅
            change_str = ""
            if pre_close > 0:
                change = ((price - pre_close) / pre_close) * 100
                change_str = f"({change:+.2f}%)"

            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💰 价格: ${float(price):.2f} {change_str}")
            if amount > 0:
                # 成交额换算为亿美元
                msg.append(f"   📊 成交额: ${float(amount)/1e8:.2f} 亿")
        
        send_tg("\n".join(msg))
        print("推送成功！")

    except Exception as e:
        send_tg(f"❌ 脚本执行失败: `{str(e)}`")

if __name__ == "__main__":
    main()
