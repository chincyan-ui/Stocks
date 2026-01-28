import yfinance as yf
import requests
import os

# 1. 更新后的监控列表
TICKERS = [
    "IONQ", "MSTR", "CRWV", "CRCL", "HIMS", "NVO", "OKLO", "HOOD",
    "IREN", "BMNR", "ASTS", "RKLB", "APLD", "QBTS", "NBIS", "CRML",
    "ONDS", "NVTS", "ALAB", "CIFR", "RDDT", "SOFI", "RIOT",
    "LLY", "TEM", "MRVL", "BE"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤数据():
    结果列表 = []
    
    for 代码 in TICKERS:
        try:
            标的 = yf.Ticker(代码)
            # auto_adjust=True 对应“前复权”
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

    # --- 核心修改：按回撤幅度从大到小排序 ---
    # 回撤是负数，-50% < -10%，所以从小到大排就是回撤从大到小排
    结果列表.sort(key=lambda x: x['drawdown'])

    # --- 核心修改：仅保留回撤最大的前10个标的 ---
    前10名 = 结果列表[:10]

    # 构建消息
    消息行 = [f"🔔 **核心标的回撤 TOP 10 (共监控 {len(TICKERS)} 只)**", "---"]
    for 项 in 前10名:
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
        response = requests.post(URL, data=参数, timeout=10)
        # 增加一个简单的状态检查
        if response.status_code != 200:
            print(f"TG 返回错误: {response.text}")
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    报告 = 获取回撤数据()
    print(报告)
    推送到TG(报告)
