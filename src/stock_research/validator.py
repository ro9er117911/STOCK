import yfinance as yf
import pandas as pd
import sys

def check_connection(ticker="AAPL"):
    """
    驗證與 Yahoo Finance 的連線並抓取資料。
    """
    print(f"🔍 正在驗證連線：抓取 {ticker}...")
    try:
        data = yf.download(ticker, period="1d", progress=False)
        if not data.empty:
            close_price = float(data['Close'].iloc[-1])
            print(f"✅ 連線成功！{ticker} 最新收盤價: {close_price:.2f}")
            return True
        else:
            print(f"❌ 抓取失敗：{ticker} 資料為空。")
            return False
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        return False

def check_taiwan_support(ticker="2330"):
    """
    驗證台股 (TWSE/TPEx) 支援。
    """
    # 自動處理台股後綴
    if ticker.isdigit() and len(ticker) >= 4:
        full_ticker = f"{ticker}.TW"
    else:
        full_ticker = ticker
        
    print(f"🇹🇼 正在驗證台股支援：抓取 {full_ticker}...")
    return check_connection(full_ticker)

def run_all_checks():
    print("=== STOCK Research OS: Setup Validation ===\n")
    results = {
        "Global Connectivity (AAPL)": check_connection("AAPL"),
        "Taiwan Market (2330.TW)": check_taiwan_support("2330")
    }
    
    print("\n--- 驗證結果摘要 ---")
    all_passed = True
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test}: {status}")
        if not result: all_passed = False
        
    if all_passed:
        print("\n🎉 驗證全數通過！您的 STOCK 環境已就緒，可以由其他人使用。")
        return 0
    else:
        print("\n⚠️ 驗證未全數通過，請檢查網路連線。")
        return 1
