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
        print("正在从 DataFrame 获取美股排名...")

        # 获取排名，返回结果通常是 pandas.DataFrame
        rankings = client.get_trade_rank(Market.US)

        # --- 修复点：使用 .empty 判断 DataFrame ---
        if rankings is None or (isinstance(rankings, pd.DataFrame) and rankings.empty):
            send_tg("⚠️ 未能获取到成交排名数据（结果为空）。")
            return

        # 只要前 3 行
        top_3 = rankings.head(3)
        
        msg = ["🐯 **美股收盘成交额/热度 Top 3**"]
        
        # 遍历 DataFrame 的行
        for i, (index, row) in enumerate(top_3.iterrows(), 1):
            # 这里的字段名 'symbol', 'latest_price', 'amount' 是老虎常用的
            # 如果报错 KeyError，说明字段名不同
            symbol = row.get('symbol', 'N/A')
            price = row.get('latest_price', 0)
            amount = row.get('amount', row.get('volume_trade', 0))
            pre_close = row.get('pre_close', 0)
            
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
        # 如果还是报错，打印出列名帮助调试
        column_info = ""
        if 'rankings' in locals() and isinstance(rankings, pd.DataFrame):
            column_info = f"\n\n可用列名: `{list(rankings.columns)}`"
        
        send_tg(f"❌ 脚本执行失败: `{str(e)}`{column_info}")

if __name__ == "__main__":
    main()
