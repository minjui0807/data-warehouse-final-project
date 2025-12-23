from job_analysis import run_job_search, run_chart_analysis
import webbrowser
import time


def run_terminal_mode():
    """執行終端機模式"""
    while True:
        print("\n==================================")
        print("   職缺分析器(本系統會同時查找104和1111平台資料)   ")
        print("==================================")
        print("1. 職缺查詢")
        print("2. 程式語言統計圖表")
        print("q. 離開程式")
        
        choice = input("請輸入選項: ")
        
        if choice == '1':
            run_job_search()
        elif choice == '2':
            run_chart_analysis()
        elif choice.lower() == 'q':
            print("退出成功!")
            break
        else:
            print("輸入錯誤，請重試。")


def run_web_mode():
    """執行網頁模式"""
    print("\n==================================")
    print("   啟動網頁版職缺分析器   ")
    print("==================================")
    print("正在啟動Web伺服器...\n")
    
    try:
        from web_server import app
        
        # 等待0.5秒後自動打開瀏覽器
        def open_browser():
            time.sleep(1.5)
            webbrowser.open('http://localhost:5000')
            print("\n✓ 瀏覽器已打開，如未打開請手動訪問: http://localhost:5000")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        print("→ 伺服器運行在 http://localhost:5000")
        print("→ 按 Ctrl+C 停止伺服器\n")
        
        app.run(debug=False, port=5000)
        
    except ImportError:
        print("✗ 錯誤: 找不到Flask，請先安裝: pip install flask")
    except Exception as e:
        print(f"✗ 啟動失敗: {e}")


if __name__ == "__main__":
    while True:
        print("\n╔════════════════════════════════════╗")
        print("║    職缺分析器 - 介面選擇           ║")
        print("║ (本系統會同時查找104和1111平台資料)║")
        print("╚════════════════════════════════════╝\n")
        
        print("請選擇使用介面:")
        print("1. 終端機模式 (Terminal)")
        print("2. 網頁模式 (Web Browser)")
        print("q. 離開程式")
        
        mode_choice = input("\n請輸入選項: ").strip()
        
        if mode_choice == '1':
            run_terminal_mode()
        elif mode_choice == '2':
            run_web_mode()
        elif mode_choice.lower() == 'q':
            print('退出成功')
            break
        else:
            print("輸入錯誤，請輸入 1 或 2")