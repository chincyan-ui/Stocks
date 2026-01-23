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
    config = TigerOpenClientConfig()
    config.tiger_id = os.getenv("TIGER_ID")
    config.private_key = os.getenv("TIGER_PRIVATE_KEY")
    config.language = Language.zh_CN
    config.sandbox = False  # 实盘环境
    return QuoteClient(config)

def main():
    try:
        client = get_client()
        print("正在获取美股成交额排行榜...")

        # 修正点：直接使用字符串 'amount' 代替 MarketRankingField.AMOUNT
        # 如果报错，请尝试将 'amount' 更改为 'Amount' (部分版本区分大小写)
        rankings = client.get_market_rankings(
            market=Market.US, 
            field='amount' 
        )

        if not rankings or len(rankings) == 0:
            send_tg("⚠️ 未获取到行情数据。请确认：\n1. 账户是否有美股行情权限\n2. 当前是否为结算维护时间")
            return

        # 提取前 3 名
        top_3 = rankings[:3]
        
        msg = ["🐯 **美股今日成交额 Top 3**"]
        for i, row in enumerate(top_3, 1):
            # 兼容性处理：部分版本返回对象，部分返回字典
            symbol = getattr(row, 'symbol', row.get('symbol') if isinstance(row, dict) else 'Unknown')
            price = getattr(row, 'latest_price', row.get('latest_price', 0) if isinstance(row, dict) else 0)
            amount = getattr(row, 'amount', row.get('amount', 0) if isinstance(row, dict) else 0)
            pre_close = getattr(row, 'pre_close', row.get('pre_close', 0) if isinstance(row, dict) else 0)
            
            # 计算涨跌幅
            change_pct = ((price - pre_close) / pre_close * 100) if pre_close else 0
            # 成交额换算为亿美元 (老虎 amount 单位通常为元)
            amount_usd = amount / 1e8

            msg.append(f"{i}. **{symbol}**")
            msg.append(f"   💸 成交额: ${amount_usd:.2f} 亿")
            msg.append(f"   📈 价格: ${price:.2f} ({change_pct:+.2f}%)")
        
        msg_text = "\n".join(msg)
        print(msg_text)
        send_tg(msg_text)

    except Exception as e:
        error_msg = f"❌ 脚本运行出错:\n`{str(e)}`"
        print(error_msg)
        # 如果是字段名错误，尝试打印出 row 的所有属性辅助排查
        send_tg(error_msg)

if __name__ == "__main__":
    main()
