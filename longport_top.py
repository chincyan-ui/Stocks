import os
import sys
import requests
from longport.openapi import QuoteContext, Config

def get_tsla_turnover():
    # 1. 检查环境变量
    app_key = os.getenv("LONGPORT_APP_KEY")
    app_secret = os.getenv("LONGPORT_APP_SECRET")
    access_token = os.getenv("LB_ACCESS_TOKEN")
    
    if not all([app_key, app_secret, access_token]):
        print("错误: 缺少长桥 API 配置 (Key/Secret/Token)")
        sys.exit(1)

    # 2. 初始化长桥配置
    config = Config(
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
    )
    
    # 3. 获取数据
    with QuoteContext(config) as ctx:
        # 获取 TSLA.US 最近 3 天的日 K 线
        # 成交额字段为 turnover
        candlesticks = ctx.history_candlesticks("TSLA.US", period="day", count=3)
        
        if not candlesticks:
            return "❌ 未能获取到 TSLA 的历史数据，请检查权限或开市状态。"

        msg_lines = ["🚗 **Tesla (TSLA) 最近3天成交额报表**"]
        for candle in candlesticks:
            # 格式化日期和成交额（换算为亿美元）
            date_str = candle.timestamp.strftime('%Y-%m-%d')
            turnover_bn = float(candle.turnover) / 10**8
            msg_lines.append(f"📅 {date_str}: `${turnover_bn:.2f}` 亿")
        
        return "\n".join(msg_lines)

def send_telegram(text):
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not token or not chat_id:
        print("错误: 缺少 Telegram 配置 (Token/Chat ID)")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Telegram 推送成功！")
    except Exception as e:
        print(f"Telegram 推送失败: {e}")

if __name__ == "__main__":
    try:
        report_content = get_tsla_turnover()
        send_telegram(report_content)
    except Exception as e:
        print(f"程序执行异常: {e}")
