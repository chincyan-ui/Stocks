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
        rankings = client.get_trade_rank(Market.US)

        if rankings is None or (isinstance(rankings, pd.DataFrame) and rankings.empty):
            send_tg("⚠️ 未能获取到成交排名数据（结果为空）。")
            return

        # --- 调试打印：在 Github 日志中查看所有列名 ---
        print(f"API 返回的列名: {list(rankings.columns)}")

        top_3 = rankings.head(3)
        msg = ["🐯 **美股收盘成交额/热度 Top 3**"]
        
        for i, (index, row) in enumerate(top_3.iterrows(), 1):
            # 1. 自动适配代码 (Symbol)
            symbol = row.get('symbol', row.get('code', 'N/A'))
            
            # 2. 自动适配价格 (尝试所有可能的字段名)
            # 老虎不同版本可能叫 latest_price, last_price, price 或 close
            price = row.get('latest_price') or row.get('last_price') or row.get('price') or row.get('close') or 0
            
            # 3. 自动适配成交额 (amount 或 volume_trade)
            amount = row.get('amount') or row.get('volume_trade') or 0
            
            # 4. 自动适配涨跌幅
            # 如果 API 直接给了涨跌幅字段 pct_chg 或 change_rate 则直接用
            change_val = row.get('pct_chg') or row.get('change_rate')
            if change_val is not None:
                change_str = f"({float(change_val):+.2f}%)"
            else:
                # 否则根据昨收价计算
                pre_close = row.get('pre_close')
                change_str = f"({((float(price)-pre_close)/pre_close*100):+.2f}%)" if pre_close and price else ""

            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💰 价格: ${float(price):.2f} {change_str}")
            if amount > 0:
                msg.append(f"   📊 成交额: ${float(amount)/1e8:.2f} 亿")
        
        send_tg("\n".join(msg))
        print("推送成功！")

    except Exception as e:
        send_tg(f"❌ 脚本执行失败: `{str(e)}`")

if __name__ == "__main__":
    main()
