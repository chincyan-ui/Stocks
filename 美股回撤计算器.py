import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import os

def 获取全量并合并特定标的():
    # 1. 获取全量千亿市值数据
    print("正在从 Nasdaq 接口拉取全量美股名单...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()['data']['rows']
        df_all = pd.DataFrame(data)
        
        # 清洗数据
        df_all['marketCap'] = df_all['marketCap'].str.replace('$', '', regex=False).str.replace(',', '', regex=False).replace('', '0').astype(float)
        
        # 筛选千亿市值
        门槛 = 1000 * 10**8
        df_top = df_all[df_all['marketCap'] >= 门槛].copy()
        api_symbols = df_top['symbol'].tolist()
        print(f"API 扫描完成，发现 {len(api_symbols)} 家千亿市值公司。")
    except Exception as e:
        print(f"API 获取失败: {e}，将仅使用指定标的列表。")
        api_symbols = []

    # 2. 注入你指定的标的
    指定标的字符串 = "AAPL, ABNB, ADBE, ADI, ADP, ADSK, AEP, ALNY, AMAT, AMD, AMGN, AMZN, APP, ARM, ASML, AVGO, AXON, BKNG, BKR, CCEP, CDNS, CEG, CHTR, CMCSA, COST, CPRT, CRWD, CSCO, CSGP, CSX, CTAS, CTSH, DASH, DDOG, DXCM, EA, EXC, FANG, FAST, FER, FTNT, GEHC, GILD, GOOG, GOOGL, HON, IDXX, INSM, INTC, INTU, ISRG, KDP, KHC, KLAC, LIN, LRCX, MAR, MCHP, MDLZ, MELI, META, MNST, MPWR, MRVL, MSFT, MSTR, MU, NFLX, NVDA, NXPI, ODFL, ORLY, PANW, PAYX, PCAR, PDD, PEP, PLTR, PYPL, QCOM, REGN, ROP, ROST, SBUX, SHOP, SNPS, STX, TEAM, TMUS, TRI, TSLA, TTWO, TXN, VRSK, VRTX, WBD, WDAY, WDC, WMT, XEL, ZS"
    custom_symbols = [s.strip() for s in 指定标的字符串.split(',')]
    
    # 3. 合并并去重
    最终名单 = list(set(api_symbols + custom_symbols))
    print(f"合并去重完成，总计分析 {len(最终名单)} 个标的。")
    return 最终名单

def 计算分析(代码列表):
    结果列表 = []
    
    for 代码 in 代码列表:
        try:
            print(f"正在分析: {代码}...")
            股票 = yf.Ticker(代码)
            # 获取历史数据 (auto_adjust=True 自动处理分红拆股)
            历史数据 = 股票.history(period="max", auto_adjust=True)
            
            if 历史数据.empty: continue
            
            # 基础信息获取（用于获取公司名称和实时市值）
            # 注意：这里如果太慢，可以考虑只拿价格
            info = 股票.info
            名称 = info.get('longName', 代码)
            市值 = info.get('marketCap', 0)
            
            盘中历史最高价 = 历史数据['High'].max() 
            当前价 = 历史数据['Close'].iloc[-1] 
            回撤幅度 = (盘中历史最高价 - 当前价) / 盘中历史最高价
            
            结果列表.append({
                '股票代码': 代码,
                '公司名称': 名称,
                '市值(亿美元)': round(市值 / 10**8, 2) if 市值 else "N/A",
                '当前收盘价(前复权)': round(当前价, 2),
                '盘中历史最高价(前复权)': round(盘中历史最高价, 2),
                '距盘中最高回撤幅度': 回撤幅度
            })
        except Exception as e:
            print(f"跳过 {代码}: {e}")
            
    结果表格 = pd.DataFrame(结果列表)
    结果表格 = 结果表格.sort_values(by='距盘中最高回撤幅度', ascending=False)
    结果表格['距盘中最高回撤幅度'] = 结果表格['距盘中最高回撤幅度'].apply(lambda x: f"{round(x * 100, 2)}%")
    
    return 结果表格

if __name__ == "__main__":
    # 第一步：获取合并后的名单
    全部待分析名单 = 获取全量并合并特定标的()
    
    # 第二步：循环分析
    最终结果 = 计算分析(全部待分析名单)
    
    # 第三步：保存
    日期 = datetime.now().strftime('%Y年%m月%d日')
    文件名 = f"美股综合回撤报告_{日期}.xlsx"
    最终结果.to_excel(文件名, index=False)
    print(f"\n报告已生成: {文件名}")
