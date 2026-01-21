import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_FILE = "last_list.txt"

import pandas as pd
import pandas_datareader.data as web
import datetime

def get_oas_history(days_count=7):
    """
    获取并显示美银美林高收益债利差最近 N 个交易日的数据
    """
    try:
        # 为了确保能凑够 7 个【交易日】，我们需要抓取大约 15 天的【自然日】数据
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=15)
        
        # 获取数据
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        
        # 清洗：去空值
        df = df.dropna()
        
        # 计算每日变动 (Difference)
        df['Daily_Change'] = df['BAMLH0A0HYM2'].diff()
        
        # 只取最近的 7 行
        recent_7_days = df.tail(days_count).copy()
        
        # 格式化日期索引，只保留年月日
        recent_7_days.index = recent_7_days.index.strftime('%Y-%m-%d')
        
        # 重命名列名以便阅读
        recent_7_days.columns = ['OAS_Spread(%)', 'Daily_Change']
        
        return recent_7_days

    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None

# 执行并打印结果
df_oas = get_oas_history(7)
if df_oas is not None:
    print("--- 最近7个交易日美银美林高收益债利差(OAS) ---")
    print(df_oas)

def get_qualified_list():
    """监控池扫描：250日成交额 > 10亿"""
    tickers = ["SOXL", "NVDA", "AMD", "TSM", "AVGO", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]
    qualified = []
    threshold = 1e9
    for s in tickers:
        try:
            df = yf.download(s, period="260d", progress=False)
            if len(df) < 250: continue
            df['Amt'] = df['Close'] * df['Volume']
            if (df['Amt'].tail(250) > threshold).all():
                qualified.append(s)
        except: continue
    return set(qualified)

def main():
    # 1. 获取宏观数据
    oas, oas_change = get_oas_data()
    oas_status = "🟢 风险低" if oas and oas < 5.0 else ("🟡 风险抬升" if oas and oas < 6.5 else "🔴 衰退警报")
    
    # 2. 获取名单变动
    current_set = get_qualified_list()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_list = set(f.read().splitlines())
    else:
        last_list = set()

    added = current_set - last_list
    removed = last_list - current_set
    stayed = sorted(list(current_set & last_list))

    # 3. 构造 Markdown 报告
    msg = f"📊 *美股量化复盘简报*\n"
    msg += f"--------------------------------\n"
    
    # 宏观板块
    if oas:
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"利差水平: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        msg += f"风险评估: {oas_status}\n\n"

    # 变动板块
    msg += f"🚀 *250日/10亿量能榜*\n"
    if added:
        for s in added: msg += f"➕ *新晋:* `{s}` [NEW]\n"
    if removed:
        for s in removed: msg += f"➖ *掉出:* ~{s}~ (注意缩量)\n"
    
    # 存量板块
    if stayed:
        msg += f"\n✅ *持续在榜名单:*\n"
        msg += f"`{', '.join(stayed)}`"
    
    msg += f"\n--------------------------------\n"
    
    # 综合建议
    suggestion = "🚀 *建议策略：积极持有*" if oas < 5.0 and "SOXL" in current_set else "⚠️ *建议策略：谨慎观望*"
    msg += f"💡 {suggestion}"

    # 4. 发送并保存
    send_msg(msg)
    with open(DB_FILE, "w") as f:
        f.write("\n".join(current_set))

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
