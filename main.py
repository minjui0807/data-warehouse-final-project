from job_analysis import run_job_search, run_chart_analysis
import webbrowser
import time

if __name__ == "__main__":
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
        print("錯誤: 找不到Flask，請先安裝: pip install flask")
    except Exception as e:
        print(f"啟動失敗: {e}")