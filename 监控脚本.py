import yfinance as yf
import requests
import os

# 股票列表
TICKERS = ["TSLL", "TQQQ"]
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取回撤数据():
    消息行 = ["🔔 **杠杆 ETF 每日监控报告**", "---"]
    
    for 代码 in TICKERS:
        标的 = yf.Ticker(代码)
        # 获取所有历史数据
        数据 = 标的.history(period="max")
        if 数据.empty: continue
        
        # 获取历史最高收盘价 (ATH)
        最高价 = 数据['Close'].max()
        # 获取最新收盘价
        当前价 = 数据['Close'].iloc[-1]
        # 计算回撤幅度
        回撤 = (当前价 - 最高价) / 最高价 * 100
        
        状态 = "🔴" if 回撤 < -10 else "🟢"
        
        消息行.append(f"{状态} **{代码}**")
        消息行.append(f"▫️ 当前价格: `${当前价:.2f}`")
        消息行.append(f"▫️ 历史最高: `${最高价:.2f}`")
        消息行.append(f"▫️ 距最高位回撤: **{回撤:.2f}%**")
        消息行.append("")
        
    return "\n".join(消息行)

def 推送到TG(文本):
    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    参数 = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        requests.post(URL, data=参数)
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    报告 = 获取回撤数据()
    推送到TG(报告)
