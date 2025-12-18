import time
import sys
import threading, itertools
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import re
from datetime import datetime

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

#程式語言職缺數統計圖
def run_chart_analysis():
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    languages = ['Python', 'Java', 'JavaScript', 'C#', 'PHP', 'Swift', 'Go']
    results = []

    print("\n開始統計各語言職缺數...")
    print(f"{'語言':<12} | {'104':<8} | {'1111':<8}")
    print("-" * 35)
    
    for lang in languages:
        c104, _ = spider104.search(lang, max_num=1)
        c1111, _ = spider1111.search(lang, max_num=1)
        print(f"{lang:<12} | {c104:<8} | {c1111:<8}")
        results.append({"Language": lang, "104": c104, "1111": c1111, "Total": c104 + c1111})
        time.sleep(0.5)
        
    df = pd.DataFrame(results).sort_values(by="Total", ascending=False)
    if df['Total'].sum() > 0:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
        plt.rcParams['axes.unicode_minus'] = False
        
        ax = df.plot(x="Language", y=["104", "1111"], kind="bar", 
                     figsize=(10, 6), color=['#F29048', '#4DA6FF'], width=0.8)
        
        plt.title(f"{datetime.now().strftime('%Y-%m-%d')} 程式語言職缺數比較")
        plt.xlabel("程式語言")
        plt.ylabel("職缺數")
        plt.xticks(rotation=0)
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        for container in ax.containers:
            ax.bar_label(container, padding=3)
            
        plt.tight_layout()
        plt.savefig("job_statistics.png")
        print(f"\n圖表已生成: job_statistics.png")
        plt.show()
    else:
        print("無數據")

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