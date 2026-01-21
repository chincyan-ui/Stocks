import pandas as pd
import pandas_datareader.data as web
import datetime
import os

def get_oas_history(days_count=7):
    try:
        # 获取足够长的时间范围
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=20)
        
        print(f"正在从 FRED 获取数据 ({start.date()} 至 {end.date()})...")
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        
        if df.empty:
            raise ValueError("未能获取到数据，请检查网络或 FRED 状态。")
            
        df = df.dropna()
        df['Daily_Change'] = df['BAMLH0A0HYM2'].diff()
        
        result = df.tail(days_count)
        
        print("\n--- 最近7个交易日美银美林高收益债利差(OAS) ---")
        print(result)
        return True
        
    except Exception as e:
        print(f"运行出错: {e}")
        return False

if __name__ == "__main__":
    success = get_oas_history()
    if not success:
        exit(1) # 如果失败，向 GitHub 发送错误信号
