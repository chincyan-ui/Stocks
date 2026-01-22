import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 从 GitHub Secrets 获取环境变量
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def main():
    # 1. 使用 yfinance 获取高收益债 OAS 数据
    # ^ICEBAMLY 是 ICE BofA US High Yield Index Option-Adjusted Spread 的代号
    ticker = "^ICEBAMLY"
    data = yf.Ticker(ticker)
    
    # 获取过去 2 年的数据以确保计算“过去一年”时数据充足
    df = data.history(period="2y")
    
    if df.empty:
        print("错误：未能获取到数据，请检查网络或代号是否有效。")
        return

    # 数据清洗
    df = df.reset_index()[['Date', 'Close']]
    df.columns = ['date', 'value']
    # 统一日期格式，移除时区信息以便计算
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)

    # 2. 计算过去一年（365天）内的统计指标
    one_year_ago = datetime.now() - timedelta(days=365)
    df_1y = df[df['date'] >= one_year_ago].copy()
    
    if df_1y.empty:
        print("错误：过去一年内没有有效数据。")
        return

    max_val = df_1y['value'].max()
    max_date = df_1y.loc[df_1y['value'].idxmax(), 'date'].strftime('%Y-%m-%d')
    
    min_val = df_1y['value'].min()
    min_date = df_1y.loc[df_1y['value'].idxmin(), 'date'].strftime('%Y-%m-%d')

    # 3. 获取最近 7 条记录（通常为最近 7 个交易日）
    last_7_days = df.tail(7).iloc[::-1] 
    recent_text = "\n".join([f"· {row['date'].strftime('%Y-%m-%d')}: **{row['value']:.2f}%**" for _, row in last_7_days.iterrows()])

    # 4. 构造 Telegram 消息
    # 添加简单的风险提示逻辑
    current_val = last_7_days.iloc[0]['value']
    status = "🔴 市场恐慌 (利差走高)" if current_val > 4.5 else "🟢 风险偏好强 (利差走低)"
    if 3.5 <= current_val <= 4.5: status = "🟡 市场观望"

    message = (
        f"📋 **Daily OAS Report**\n"
        f"状态: {status}\n\n"
        f"🗓 **过去一年极值：**\n"
        f"🔝 最高: {max_val:.2f}% ({max_date})\n"
        f"🔙 最低: {min_val:.2f}% ({min_date})\n\n"
        f"📈 **最近 7 个交易日数值：**\n{recent_text}\n\n"
        f"ℹ️ *数据源: Yahoo Finance (^ICEBAMLY)*"
    )

    # 5. 发送 Telegram 推送
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(send_url, data=payload)
        response.raise_for_status()
        print("推送成功！")
    except Exception as e:
        print(f"推送出错: {e}")

if __name__ == "__main__":
    main()
