import time
import sys
import threading, itertools
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from job_spider_104 import Job104Spider
from job_spider_1111 import Job1111Spider

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False

#功能1: 整合搜尋(同時查104與1111)
def run_job_search():
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    
    global keyword 
    keyword = input("\n請輸入關鍵字(例如 Python): ")
    if keyword == "":
        keyword = 'Python'

    try:
        max_num = int(input("請輸入各平台要抓取的筆數: "))
    except:
        print('格式錯誤，使用預設參數20')
        max_num = 20

    print("-" * 30)
    #防呆
    if max_num <= 0:
        print(">> 筆數設定為 0，略過搜尋，返回主選單。")
        time.sleep(1)
        return [], []
    
    #執行搜尋
    _, jobs104 = loading(f"[104] 正在搜尋 {keyword}", lambda: spider104.search(keyword, max_num=max_num))
    if len(jobs104) >= max_num:
        print(f"[104] 已搜尋{max_num}筆資料")
    else:
        print(f"[104] 資料不足，僅找到: {len(jobs104)}筆")
    
    _, jobs1111 = loading(f"[1111] 正在搜尋 {keyword}", lambda: spider1111.search(keyword, max_num=max_num))
    if len(jobs1111) >= max_num:
        print(f"[1111] 已搜尋{max_num}筆資料")
    else:
        print(f"[1111] 資料不足，僅找到: {len(jobs1111)}筆")

    #資料整合
    all_jobs = []
    for job in jobs104: all_jobs.append(spider104.search_job_transform(job))
    for job in jobs1111: all_jobs.append(spider1111.search_job_transform(job))
        
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        filename = f"combined_jobs_{keyword}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n原始資料已儲存: {filename}")

        try:
            conn = sqlite3.connect('job_database.db')
            df.to_sql('search_results', conn, if_exists='replace', index=False)
            conn.close()
            print("資料已寫入資料庫 job_database.db")
        except:
            print("資料庫寫入失敗")

        #進階功能
        print("\n是否要進行進階分析? \n1.繪製薪資分佈圖 \n2.繪製地區佔比圖 \n3.篩選高薪職缺 \n4.全部都做 \nEnter 跳過")
        do_analyze = input("\n請輸入選項: ")
        
        if do_analyze in ['1', '4']:
            plot_salary_distribution(df)
            
        if do_analyze in ['2', '4']:
            plot_location_pie(df)
            
        if do_analyze in ['3', '4']:
            try:
                money_str = input("請輸入你心中的高薪門檻(預設 50000): ")
                threshold = int(money_str) if money_str.isdigit() else 50000
            except:
                threshold = 50000
                
            export_high_salary(df, threshold)
            
    else:
        print("\n兩個平台都沒抓到資料")

#將薪資字串 (如 '30000-50000') 轉換為平均數值
def parse_salary(salary_str):
    salary_str = str(salary_str).replace(',', '')
    
    if '面議' in salary_str:
        return 0
        
    #抓取所有數字
    nums = re.findall(r'(\d+)', salary_str)
    if not nums:
        return 0
        
    #轉成整數並計算平均
    nums = [int(n) for n in nums]
    avg_salary = sum(nums) / len(nums)
    
    #排除明顯異常的數字(例如時薪180或年薪200萬，這裡簡單過濾月薪範圍)
    if avg_salary < 1000: #可能是時薪，簡單乘以160小時估算
        return avg_salary * 160
    if avg_salary > 300000: #可能是年薪，簡單除以13個月估算
        return avg_salary / 13
        
    return avg_salary

#繪製地區職缺佔比圖
def plot_location_pie(df):
    print("\n正在生成地區佔比圖...")
    
    #抓取前三個字(例如"台北市")
    def get_city(addr):
        if isinstance(addr, str) and len(addr) >= 3:
            return addr[:3]
        return "其他"
        
    city_counts = df['location'].apply(get_city).value_counts()
    
    #只取前6名，剩下的歸類為「其他」
    if len(city_counts) > 6:
        main_cities = city_counts[:6]
        other_count = city_counts[6:].sum()
        main_cities['其他'] = other_count
        city_counts = main_cities

    plt.figure(figsize=(8, 8)).canvas.manager.set_window_title('地區職缺佔比圖')
    plt.pie(city_counts, labels=city_counts.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.Pastel1.colors)
    plt.title(f"{keyword}職缺地區分佈")
    
    filename = f"{keyword}_location_pie.png"
    plt.savefig(filename)
    print(f"圖表已儲存: {filename}")
    plt.show()

#繪製薪資分佈圖
def plot_salary_distribution(df):
    """功能: 薪資區間分佈圖"""
    print("\n正在生成薪資分佈圖...")
    
    df_plot = df.copy()
    df_plot['avg_salary'] = df_plot['salary'].apply(parse_salary)
    
    #過濾掉0(面議)和極端值
    salary_data = df_plot[df_plot['avg_salary'] > 20000]['avg_salary']
    
    if salary_data.empty:
        print("有效薪資數據不足，無法畫圖")
        return

    plt.figure(figsize=(10, 6)).canvas.manager.set_window_title('職缺薪資分佈圖')
    #畫直方圖(Histogram)
    plt.hist(salary_data, bins=15, color='#69b3a2', edgecolor='white', alpha=0.7)
    plt.title(f"{keyword}職缺薪資分佈圖(樣本數: {len(salary_data)})(已拿掉面議和極端值)")
    plt.xlabel("平均月薪 (新台幣)")
    plt.ylabel("職缺數量")
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.savefig(f"{keyword}_salary_histogram.png")
    print(f"圖表已儲存: {keyword}_salary_histogram.png")
    plt.show()

#高薪職缺快篩並匯出CSV
def export_high_salary(df, threshold=50000):
    print(f"\n正在篩選月薪 {threshold} 以上的職缺...")
    df_filter = df.copy()
    
    #計算薪資
    df_filter['avg_salary'] = df_filter['salary'].apply(parse_salary)
    
    #篩選
    high_paying_jobs = df_filter[df_filter['avg_salary'] >= threshold]
    
    if not high_paying_jobs.empty:
        high_paying_jobs = high_paying_jobs.sort_values(by='avg_salary', ascending=False)
        
        #選取要顯示的欄位
        cols = ['platform', 'name', 'company_name', 'salary', 'job_url', 'location']
        result = high_paying_jobs[cols]
        
        print(f"找到 {len(result)} 筆高薪{keyword}職缺！(前5筆預覽):")
        print(result.head())
        
        filename = f"{keyword}_high_salary_jobs.csv"
        result.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"已匯出高薪清單: {filename}")
    else:
        print("沒找到符合條件的高薪職缺(可能都是面議)")

def fetch_stats_by_keyword(keyword):
    """
    [工作函式] 負責查詢單一關鍵字在兩個平台的數據
    """
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    try:
        # 只抓 1 筆是為了快速取得 Total Count
        count104, _ = spider104.search(keyword, max_num=1)
        count1111, _ = spider1111.search(keyword, max_num=1)
        return {"Keyword": keyword, "104": count104, "1111": count1111}
    except Exception as e:
        print(f"查詢 {keyword} 時發生錯誤: {e}")
        return {"Keyword": keyword, "104": 0, "1111": 0}

def run_chart_analysis():
    targets = [] # 存放要搜尋的目標清單
    chart_title = ""
    x_label = ""

    print("\n" + "="*30)
    print("請選擇分析模式：")
    print("1. 程式語言統計 (預設清單)")
    print("2. 自訂職缺分析 (自行輸入)")
    mode = input("請輸入選項 (1 或 2): ")

    if mode == '2':
        # --- 模式二：自訂輸入 ---
        print("\n>> 請依序輸入要比較的關鍵字 (例如: 行政, 會計, 業務)")
        print(">> 輸入完畢請直接按 [Enter] 鍵結束輸入")
        
        while True:
            user_input = input(f"請輸入第 {len(targets)+1} 個關鍵字: ").strip()
            if user_input == "":
                break
            if user_input in targets:
                print("這個關鍵字已經輸入過了")
                continue
            targets.append(user_input)
            
        if not targets:
            print("未輸入任何關鍵字，回到主選單。")
            return
            
        chart_title = "自訂職缺熱度比較"
        x_label = "職缺關鍵字"
        
    else:
        # --- 模式一：預設程式語言 ---
        # 預設為模式 1 (包含輸入錯誤時)
        targets = ['Python', 'Java', 'JavaScript', 'C#', 'PHP', 'Swift', 'Go', 'C++', 'Ruby']
        chart_title = "程式語言職缺數比較"
        x_label = "程式語言"

    # --- 開始執行多執行緒統計 (共用邏輯) ---
    results = []

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 開始分析下列項目: {targets}")
    print(f"{'關鍵字':<12} | {'104':<8} | {'1111':<8} | {'狀態'}")
    print("-" * 50)

    # 開啟執行緒池
    with ThreadPoolExecutor(max_workers=min(len(targets), 10)) as executor:
        # 送出任務
        future_to_kw = {executor.submit(fetch_stats_by_keyword, kw): kw for kw in targets}
        
        # 接收結果
        for future in as_completed(future_to_kw):
            data = future.result()
            kw = data['Keyword']
            
            # 存入結果
            total = data['104'] + data['1111']
            data['Total'] = total
            results.append(data)
            
            # 印出進度
            # 處理中文字串對齊問題(簡單處理)
            display_kw = kw if len(kw) < 8 else kw[:6]+".."
            print(f"{display_kw:<12} | {data['104']:<8} | {data['1111']:<8} | 完成")

    # --- 畫圖 ---
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 統計完成，開始製圖...")
    
    df = pd.DataFrame(results).sort_values(by="Total", ascending=False)
    
    if df['Total'].sum() > 0:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
        plt.rcParams['axes.unicode_minus'] = False
        
        # 根據數量動態調整圖表大小，避免字擠在一起
        fig_width = max(10, len(targets) * 1.2)
        
        ax = df.plot(x="Keyword", y=["104", "1111"], kind="bar", 
                     figsize=(fig_width, 6), color=['#F29048', '#4DA6FF'], width=0.8)
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        plt.title(f"{today_str} {chart_title}", fontsize=16, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel("職缺數", fontsize=12)
        plt.xticks(rotation=0) # 轉正文字
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.legend(title="平台")
        
        # 在柱狀圖上標示數字
        for container in ax.containers:
            ax.bar_label(container, padding=3, fmt='%d')
            
        plt.tight_layout()
        filename = f"stats_chart_{today_str}.png"
        plt.savefig(filename)
        print(f"圖表已生成: {filename}")
        plt.show()
    else:
        print("沒有抓到任何數據。")

#讀條動畫
def loading(msg, task_func):
    stop_event = threading.Event() # 使用Event控制停止更穩健
    def animate():
        for c in itertools.cycle(['.', '..', '...']):
            if stop_event.is_set(): break
            sys.stdout.write(f'\r{msg}{c}   ')
            sys.stdout.flush()
            time.sleep(0.5)
    
    t = threading.Thread(target=animate, daemon=True)
    t.start()
    
    try:
        return task_func() #執行爬蟲
    finally:
        stop_event.set()   #1. 通知動畫停止
        t.join()           #2. 等待動畫真的停下來(解決文字殘留問題)
        sys.stdout.write('\r' + ' '*(len(msg)+10) + '\r') # 3. 清除文字
        sys.stdout.flush()