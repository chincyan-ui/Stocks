import yfinance as yf
import requests
import os

# 1. 监控列表
# 注意：yfinance 中伯克希尔B股的代码需写为 "BRK-B"，而非 "BRK.B"
TICKERS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSM", "AVGO", 
    "TSLA", "BRK-B", "LLY", "AMD", "APP", "HOOD", "IONQ"
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
                print(f"警告: {代码} 数据为空，跳过")
                continue
            
            # 确保数据中有 High 和 Close 列
            if 'High' not in 数据.columns or 'Close' not in 数据.columns:
                 continue

            最高价 = 数据['High'].max()
            当前价 = 数据['Close'].iloc[-1]
            
            # 防止最高价为0的极端错误情况
            if 最高价 == 0:
                continue

            回撤 = (当前价 - 最高价) / 最高价 * 100
            
            结果列表.append({
                "ticker": 代码.replace("-", "."), # 显示时改回 BRK.B 比较美观
                "current_price": 当前价,
                "ath_price": 最高价,
                "drawdown": 回撤
            })
        except Exception as e:
            print(f"处理 {代码} 时出错: {e}")

    # --- 按回撤幅度从大到小排序 (负值越小代表回撤越大，即跌得越惨的排前面) ---
    # 如果想把表现最好的排前面，可以改为 reverse=True
    结果列表.sort(key=lambda x: x['drawdown'])

    # 构建消息
    消息行 = [f"📊 **科技巨头&热门股回撤监控 (共 {len(结果列表)} 只)**", "排名 | 代码 | 回撤幅度 | 现价", "---"]
    
    for i, 项 in enumerate(结果列表, 1):
        # 视觉反馈：
        # 🔴 深跌 (回撤 > 20%)
        # 🟡 中等回撤 (10% - 20%)
        # 🟢 强势 (回撤 < 10% 或 创新高)
        if 项['drawdown'] < -20:
            状态 = "🔴"
        elif 项['drawdown'] < -10:
            状态 = "🟡"
        else:
            状态 = "🟢"
        
        # 格式化输出
        消息行.append(f"{状态} {i:02d}. **{项['ticker']}**: `{项['drawdown']:.2f}%` (价: `{项['current_price']:.2f}`)")
        
    return "\n".join(消息行)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("错误: 环境变量 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID 未设置")
        # 如果是本地测试，不想报错退出，可以注释掉下面这行
        # return 

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {
        "chat_id": CHAT_ID, 
        "text": 文本, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True 
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
    # 确保安装了必要的库：pip install yfinance requests
    报告 = 获取回撤数据()
    print("------------------------------------------------")
    print(报告)
    print("------------------------------------------------")
    推送到TG(报告)
