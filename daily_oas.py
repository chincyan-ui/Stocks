import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 配置 Telegram 参数
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def main():
    # 1. 直接从 FRED 官方下载 CSV 数据 (不需要 API Key)
    # 系列 ID: BAMLH0A0HYM2 (ICE BofA US High Yield Index OAS)
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
    
    try:
        # 读取数据，FRED 的 CSV 第一列是 DATE，第二列是 BAMLH0A0HYM2
        df = pd.read_csv(url)
        df.columns = ['date', 'value']
        # 转换日期，并处理无效值（FRED 有时会用 '.' 表示节假日无数据）
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        print(f"成功获取数据，最新日期: {df.iloc[-1]['date']}")
    except Exception as e:
        print(f"获取 FRED 数据失败: {e}")
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
    # 简易风险评估
    risk_level = "🔴 恐慌" if current_val > 5.0 else ("🟢 贪婪" if current_val < 3.5 else "🟡 中性")

    message = (
        f"📊 **Daily OAS Report (FRED源)**\n"
        f"当前风险评级: {risk_level}\n\n"
        f"🗓 **过去一年统计指标：**\n"
        f"🔝 最高: {max_val:.2f}% ({max_date})\n"
        f"🔙 最低: {min_val:.2f}% ({min_date})\n\n"
        f"📈 **最近 7 个交易日：**\n{recent_text}\n\n"
        f"🔗 [查看 FRED 详情页面](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)"
    )

    # 5. 推送至 Telegram
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    res = requests.post(send_url, data=payload)
    print(f"TG 响应: {res.text}")

if __name__ == "__main__":
    main()
