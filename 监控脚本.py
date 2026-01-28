import yfinance as yf
import requests
import os

# 1. 监控列表
# 注意：yfinance 中伯克希尔B股的代码需写为 "BRK-B"
TICKERS = [
    "NVDA", "AAPL", "MSFT", "PLTR","GOOGL", "AMZN", "META", "TSM", "AVGO", 
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
            # period="max" 获取全历史数据以找到绝对最高点
            数据 = 标的.history(period="max", auto_adjust=True)
            
            if 数据.empty:
                print(f"警告: {代码} 数据为空，跳过")
                continue
            
            # 数据清洗：确保列存在
            if 'High' not in 数据.columns or 'Close' not in 数据.columns:
                 continue

            最高价 = 数据['High'].max()
            当前价 = 数据['Close'].iloc[-1]
            
            if 最高价 == 0: continue

            回撤 = (当前价 - 最高价) / 最高价 * 100
            
            结果列表.append({
                "ticker": 代码.replace("-", "."), # 修复显示格式
                "current_price": 当前价,
                "ath_price": 最高价, # 存储历史最高价
                "drawdown": 回撤
            })
        except Exception as e:
            print(f"处理 {代码} 时出错: {e}")

    # 按回撤幅度排序 (跌得最多的排前面)
    结果列表.sort(key=lambda x: x['drawdown'])

    # --- 构建消息 (修改了表头和行格式) ---
    消息行 = [
        f"📊 **科技&热门股回撤监控 (共 {len(结果列表)} 只)**", 
        "排名 | 代码 | 回撤 | 现价 / 历史高", 
        "---"
    ]
    
    for i, 项 in enumerate(结果列表, 1):
        # 状态图标逻辑
        if 项['drawdown'] < -20:
            状态 = "🔴" # 深跌
        elif 项['drawdown'] < -10:
            状态 = "🟡" # 回调
        else:
            状态 = "🟢" # 强势
        
        # 格式化输出：增加了 / 顶: xxx 部分
        # 使用 `code` 格式包裹数字，在 TG 中显示更清晰
        行文本 = (
            f"{状态} {i:02d}. **{项['ticker']}**: `{项['drawdown']:.2f}%` "
            f"(现:`{项['current_price']:.2f}` / 顶:`{项['ath_price']:.2f}`)"
        )
        消息行.append(行文本)
        
    return "\n".join(消息行)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("错误: 环境变量未设置")
        # return # 本地测试可注释

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
    报告 = 获取回撤数据()
    print("------------------------------------------------")
    print(报告)
    print("------------------------------------------------")
    推送到TG(报告)
