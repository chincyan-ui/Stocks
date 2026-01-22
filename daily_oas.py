import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 配置 Telegram 参数
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def main():
    # 1. 直接获取 FRED CSV 数据
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
    
    try:
        df = pd.read_csv(url)
        df.columns = ['date', 'value']
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
    except Exception as e:
        print(f"数据获取失败: {e}")
        return

    # 2. 计算过去一年统计指标
    one_year_ago = datetime.now() - timedelta(days=365)
    df_1y = df[df['date'] >= one_year_ago].copy()
    
    max_val = df_1y['value'].max()
    max_date = df_1y.loc[df_1y['value'].idxmax(), 'date'].strftime('%Y-%m-%d')
    
    min_val = df_1y['value'].min()
    min_date = df_1y.loc[df_1y['value'].idxmin(), 'date'].strftime('%Y-%m-%d')

    # 3. 获取最近 7 天数值
    last_7_days = df.tail(7).iloc[::-1] 
    recent_text = "\n".join([f"· {row['date'].strftime('%Y-%m-%d')}: **{row['value']:.2f}%**" for _, row in last_7_days.iterrows()])

    # 4. 构造消息
    current_val = last_7_days.iloc[0]['value']
    risk_level = "🔴 恐慌" if current_val > 5.0 else ("🟢 贪婪" if current_val < 3.5 else "🟡 中性")

    message = (
        f"📊 **Daily OAS Report**\n"
        f"当前风险评级: {risk_level}\n\n"
        f"🗓 **过去一年统计指标：**\n"
        f"🔝 最高: {max_val:.2f}% ({max_date})\n"
        f"🔙 最低: {min_val:.2f}% ({min_date})\n\n"
        f"📈 **最近 7 个交易日：**\n{recent_text}"
    )

    # 5. 推送至 Telegram
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    res = requests.post(send_url, data=payload)
    print(f"TG 响应结果: {res.text}")

if __name__ == "__main__":
    main()
