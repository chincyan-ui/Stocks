import yfinance as yf
import requests
import os

# 监控列表
TICKERS = ["IONQ", "MSTR", "CRWV", "CRCL", "HIMS", "NVO", "OKLO", "HOOD"]
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤数据():
    结果列表 = []
    
    for 代码 in TICKERS:
        try:
            标的 = yf.Ticker(代码)
            # auto_adjust=True 对应“前复权”，能保持当前价格不变，回推历史价格
            数据 = 标的.history(period="max", auto_adjust=True)
            
            if 数据.empty:
                continue
            
            # 1. 获取历史盘中最高价 (High)
            最高价 = 数据['High'].max()
            # 2. 获取最新收盘价 (Close)
            当前价 = 数据['Close'].iloc[-1]
            # 3. 计算回撤
            回撤 = (当前价 - 最高价) / 最高价 * 100
            
            结果列表.append({
                "ticker": 代码,
                "current_price": 当前价,
                "ath_price": 最高价,
                "drawdown": 回撤
            })
        except Exception as e:
            print(f"处理 {代码} 时出错: {e}")

    # --- 核心修改：按回撤幅度从大到小排序 (回撤是负数，所以越小代表回撤越大) ---
    结果列表.sort(key=lambda x: x['drawdown'])

    # 构建消息
    消息行 = ["🔔 **核心标的每日监控 (前复权排序)**", "---"]
    for 项 in 结果列表:
        # 根据回撤深度给予视觉反馈
        状态 = "🔴" if 项['drawdown'] < -15 else "🟢"
        
        消息行.append(f"{状态} **{项['ticker']}**")
        消息行.append(f"▫️ 当前价格: `{项['current_price']:.2f}`")
        消息行.append(f"▫️ 盘中最高: `{项['ath_price']:.2f}`")
        消息行.append(f"▫️ 距最高位回撤: **{项['drawdown']:.2f}%**")
        消息行.append("")
        
    return "\n".join(消息行)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("环境变量缺失")
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        requests.post(URL, data=参数, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    报告 = 获取回撤数据()
    print(报告)
    推送到TG(报告)
