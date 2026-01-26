import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import time
import os

def 获取全量并合并特定标的():
    print("正在拉取全量美股名单及特定标的...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    
    api_symbols = []
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()['data']['rows']
        df_all = pd.DataFrame(data)
        # 清洗数据
        df_all['marketCap'] = df_all['marketCap'].str.replace('$', '', regex=False).str.replace(',', '', regex=False).replace('', '0').astype(float)
        # 筛选千亿美金
        门槛 = 1000 * 10**8
        api_symbols = df_all[df_all['marketCap'] >= 门槛]['symbol'].tolist()
    except Exception as e:
        print(f"API 获取受限: {e}")

    # 特定标的
    指定标的字符串 = "AAPL, ABNB, ADBE, ADI, ADP, ADSK, AEP, ALNY, AMAT, AMD, AMGN, AMZN, APP, ARM, ASML, AVGO, AXON, BKNG, BKR, CCEP, CDNS, CEG, CHTR, CMCSA, COST, CPRT, CRWD, CSCO, CSGP, CSX, CTAS, CTSH, DASH, DDOG, DXCM, EA, EXC, FANG, FAST, FER, FTNT, GEHC, GILD, GOOG, GOOGL, HON, IDXX, INSM, INTC, INTU, ISRG, KDP, KHC, KLAC, LIN, LRCX, MAR, MCHP, MDLZ, MELI, META, MNST, MPWR, MRVL, MSFT, MSTR, MU, NFLX, NVDA, NXPI, ODFL, ORLY, PANW, PAYX, PCAR, PDD, PEP, PLTR, PYPL, QCOM, REGN, ROP, ROST, SBUX, SHOP, SNPS, STX, TEAM, TMUS, TRI, TSLA, TTWO, TXN, VRSK, VRTX, WBD, WDAY, WDC, WMT, XEL, ZS"
    custom_symbols = [s.strip() for s in 指定标的字符串.split(',')]
    
    # 2024-2025新面孔名单（仅用于打标签）
    新面孔列表 = ["ALNY", "FER", "INSM", "MPWR", "STX", "WDC", "PLTR", "MSTR", "AXON"]
    
    最终名单 = list(set(api_symbols + custom_symbols))
    return 最终名单, 新面孔列表

def 计算分析(代码列表, 新面孔列表):
    结果列表 = []
    total = len(代码列表)
    for i, 代码 in enumerate(代码列表):
        try:
            print(f"[{i+1}/{total}] 抓取中: {代码}")
            股票 = yf.Ticker(代码)
            历史数据 = 股票.history(period="max", auto_adjust=True)
            if 历史数据.empty: continue
            
            info = 股票.info
            盘中最高 = 历史数据['High'].max()
            当前价 = 历史数据['Close'].iloc[-1]
            回撤 = (盘中最高 - 当前价) / 盘中最高
            
            结果列表.append({
                '距最高回撤': 回撤,
                '股票代码': 代码,
                '状态': "新纳入" if 代码 in 新面孔列表 else "常规",
                '公司名称': info.get('longName', 代码),
                '市值(亿美元)': round(info.get('marketCap', 0) / 10**8, 2) if info.get('marketCap') else 0,
                '当前价': round(当前价, 2),
                '历史最高': round(盘中最高, 2)
            })
            time.sleep(0.1) # 略微缩短延迟
        except Exception as e:
            print(f"跳过 {代码}: {e}")
            
    df = pd.DataFrame(结果列表)
    if not df.empty:
        df = df.sort_values(by='距最高回撤', ascending=False)
    return df

if __name__ == "__main__":
    名单, 新面孔 = 获取全量并合并特定标的()
    最终数据 = 计算分析(名单, 新面孔)
    
    # 直接导出，不再使用样式的 Styler
    if not 最终数据.empty:
        # 格式化百分比：为了不使用 Styler，我们在存入 Excel 前手动转换数据格式
        最终数据['距最高回撤'] = 最终数据['距最高回撤'].apply(lambda x: f"{round(x*100, 2)}%")
        
        报告名 = "美股回撤分析报告.xlsx"
        最终数据.to_excel(报告名, index=False, engine='openpyxl')
        print(f"✅ 报告已生成: {报告名}")
    else:
        print("❌ 未获取到有效数据")
