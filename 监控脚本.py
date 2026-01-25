import yfinance as yf
import requests
import os

# 修改后的监控列表
TICKERS = ["IONQ", "MSTR", "CRWV", "CRCL", "HIMS", "NVO", "OKLO", "HOOD"]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤数据():
    消息行 = ["🔔 **核心标的每日监控报告**", "---"]
    
    for 代码 in TICKERS:
        try:
            标的 = yf.Ticker(代码)
            # 获取历史数据
            数据 = 标的.history(period="max")
            
            if 数据.empty:
                print(f"警告: 无法获取 {代码} 的数据")
                continue
            
            # 计算回撤
            最高价 = 数据['Close'].max()
            当前价 = 数据['Close'].iloc[-1]
            回撤 = (当前价 - 最高价) / 最高价 * 100
            
            # 状态图标：回撤超过 15% 标红 (考虑到这些标的高波动特性)
            状态 = "🔴" if 回撤 < -15 else "🟢"
            
            消息行.append(f"{状态} **{代码}**")
            消息行.append(f"▫️ 当前价格: `${当前价:.2f}`")
            消息行.append(f"▫️ 历史最高: `${最高价:.2f}`")
            消息行.append(f"▫️ 距最高位回撤: **{回撤:.2f}%**")
            消息行.append("")
        except Exception as e:
            print(f"处理 {代码} 时出错: {e}")
            
    return "\n".join(消息行)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("错误: 找不到环境变量 TELEGRAM_TOKEN 或 CHAT_ID")
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        r = requests.post(URL, data=参数, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    报告 = 获取回撤数据()
    # 打印到控制台方便本地调试
    print(报告)
    推送到TG(报告)
