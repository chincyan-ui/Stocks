import os
import requests
from longport.openapi import QuoteContext, Config

def get_tsla_turnover():
    # 配置长桥 SDK
    config = Config(
        app_key=os.getenv("LONGPORT_APP_KEY"),
        app_secret=os.getenv("LONGPORT_APP_SECRET"),
        access_token=os.getenv("LONGPORT_ACCESS_TOKEN"),
    )
    
    with QuoteContext(config) as ctx:
        # 获取 TSLA.US 最近 3 天的日 K 线
        # 这里的 count=3 代表取最近 3 个交易日
        candlesticks = ctx.history_candlesticks("TSLA.US", period="day", count=3)
        
        msg_lines = ["🚗 **Tesla (TSLA) 最近3天成交额报表**"]
        for candle in candlesticks:
            date = candle.timestamp.strftime('%Y-%m-%d')
            # 成交额通常单位较大，这里转换为“亿美元”更直观
            turnover_bn = float(candle.turnover) / 10**8
            msg_lines.append(f"📅 {date}: ${turnover_bn:.2f} 亿")
        
        return "\n".join(msg_lines)

def send_telegram(text):
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    try:
        content = get_tsla_turnover()
        send_telegram(content)
        print("推送成功！")
    except Exception as e:
        print(f"执行失败: {e}")
