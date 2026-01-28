import yfinance as yf
import requests
import os

# 1. 监控列表
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
    
    print(f"开始获取 {len(TICKERS)} 个标的数据...")
    
    for 代码 in TICKERS:
        try:
            标的 = yf.Ticker(代码)
            # 使用 period="max" 确保获取到历史最高点
            数据 = 标的.history(period="max", auto_adjust=True)
            
            if 数据.empty:
                continue
            
            最高价 = 数据['High'].max()
            当前价 = 数据['Close'].iloc[-1]
            回撤 = (当前价 - 最高价) / 最高价 * 100
            
            结果列表.append({
                "ticker": 代码,
                "current_price": 当前价,
                "ath_price": 最高价,
                "drawdown": 回撤
            })
        except Exception as e:
            print(f"处理 {代码} 时出错: {e}")

    # --- 核心修改：按回撤幅度从大到小排序 (负值越小代表回撤越大) ---
    结果列表.sort(key=lambda x: x['drawdown'])

    # 构建消息
    消息行 = [f"📊 **全标的回撤排名 (共 {len(结果列表)} 只)**", "排名 | 代码 | 回撤幅度 | 现价", "---"]
    
    for i, 项 in enumerate(结果列表, 1):
        # 视觉反馈：深跌用🔴，轻微回撤用🟡，持平或创新高用🟢
        if 项['drawdown'] < -20:
            状态 = "🔴"
        elif 项['drawdown'] < -10:
            状态 = "🟡"
        else:
            状态 = "🟢"
        
        # 采用单行紧凑格式，方便手机查看长列表
        消息行.append(f"{状态} {i:02d}. **{项['ticker']}**: `{项['drawdown']:.2f}%` (价: `{项['current_price']:.2f}`)")
        
    return "\n".join(消息行)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("错误: 环境变量 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID 未设置")
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {
        "chat_id": CHAT_ID, 
        "text": 文本, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True # 禁用链接预览，让界面更清爽
    }
    try:
        response = requests.post(URL, data=参数, timeout=15)
        if response.status_code == 200:
            print("推送成功！")
        else:
            print(f"TG 返回错误: {response.text}")
    except Exception as e:
        print(f"推送网络错误: {e}")

if __name__ == "__main__":
    报告 = 获取回撤数据()
    print(报告)
    推送到TG(报告)
