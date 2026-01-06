import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
import os
import sys

# 設定日期範圍 (設為 5 年)
end_date = datetime.now()
start_date = end_date - timedelta(days=1825)

# 定義需要的基礎貨幣對
tickers_map = {
    "USDTWD": "TWD=X",
    "USDLKR": "LKR=X", 
    "USDCNY": "CNY=X",
    "USDJPY": "JPY=X"
}

def get_data():
    print(f"啟動抓取程序... ({start_date.date()} ~ {end_date.date()})")
    
    # 用來暫存成功抓到的數據
    collected_data = {}
    
    # 1. 逐個抓取 (避免一顆老鼠屎壞了一鍋粥)
    for key, symbol in tickers_map.items():
        try:
            print(f"正在抓取 {symbol} ...")
            ticker = yf.Ticker(symbol)
            # 嘗試抓取數據
            df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
            
            if df.empty:
                print(f"⚠️ 警告: {symbol} 抓不到數據，跳過此貨幣。")
                continue
                
            # 整理數據
            df.reset_index(inplace=True)
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            collected_data[key] = df[['Date', 'Close']].set_index('Date')['Close']
            print(f"✅ {symbol} 抓取成功，共 {len(df)} 筆。")
            
        except Exception as e:
            print(f"❌ 錯誤: 抓取 {symbol} 時發生異常: {e}")
            continue

    # 如果連最重要的台幣都沒抓到，那就真的失敗了
    if "USDTWD" not in collected_data:
        print("❌ 嚴重錯誤: 無法獲取 USDTWD 數據，停止更新。")
        sys.exit(1) # 強制報錯，讓 GitHub 顯示紅色叉叉

    # 2. 數據對齊 (只保留大家都有的日期)
    # 以台幣的日期為基準
    valid_dates = collected_data["USDTWD"].index
    for key in collected_data:
        valid_dates = valid_dates.intersection(collected_data[key].index)
    
    print(f"數據對齊後，剩餘有效天數: {len(valid_dates)}")

    # 3. 計算交叉匯率 (有防呆機制)
    pairs_data = []

    def safe_get_series(key):
        return collected_data.get(key, pd.Series(dtype=float)).loc[valid_dates]

    # 準備基礎數據
    usd_twd = safe_get_series("USDTWD")
    usd_lkr = safe_get_series("USDLKR")
    usd_cny = safe_get_series("USDCNY")
    usd_jpy = safe_get_series("USDJPY")

    # 定義輸出函數
    def format_pair(series, name):
        if series.empty: return None
        history = [{"date": d, "value": round(v, 4)} for d, v in series.items()]
        return {
            "name": name,
            "current_rate": round(series.iloc[-1], 4),
            "history": history
        }

    # --- 組裝數據 ---
    # 只要有數據就加入，沒有就跳過，不會報錯
    
    # 美金系列
    if not usd_twd.empty: pairs_data.append(format_pair(usd_twd, "美金 / 台幣 (USD/TWD)"))
    if not usd_lkr.empty: pairs_data.append(format_pair(usd_lkr, "美金 / 斯里蘭卡盧比 (USD/LKR)"))
    
    # 人民幣系列 (需要同時有 CNY 和 TWD)
    if not usd_cny.empty and not usd_twd.empty:
        pairs_data.append(format_pair(usd_cny, "美金 / 人民幣 (USD/CNY)"))
        pairs_data.append(format_pair(usd_cny / usd_twd, "台幣 / 人民幣 (TWD/CNY)"))
        pairs_data.append(format_pair(1 / usd_cny, "人民幣 / 美金 (CNY/USD)"))
        pairs_data.append(format_pair(usd_twd / usd_cny, "人民幣 / 台幣 (CNY/TWD)"))

    # 日幣系列 (需要同時有 JPY 和 TWD)
    if not usd_jpy.empty and not usd_twd.empty:
        pairs_data.append(format_pair(usd_jpy, "美金 / 日幣 (USD/JPY)"))
        pairs_data.append(format_pair(usd_jpy / usd_twd, "台幣 / 日幣 (TWD/JPY)"))

    # 4. 生成檔案
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": pairs_data
    }
    
    return output

if __name__ == "__main__":
    data = get_data()
    if data and len(data["data"]) > 0:
        with open("rates_data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("🎉 成功生成 rates_data.json")
    else:
        print("❌ 生成失敗: 沒有有效數據")
        sys.exit(1)
