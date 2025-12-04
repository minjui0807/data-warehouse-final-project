import time
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from job_spider_104 import Job104Spider
from job_spider_1111 import Job1111Spider

def run_job_search():
    """功能 1: 整合搜尋(同時查104與1111)"""
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    keyword = input("\n請輸入關鍵字(例如Python): ")
    try:
        max_num = int(input("請輸入各平台要抓取的筆數(例如10): "))
    except:
        max_num = 10

    print("-" * 30)
    
    #執行104
    print(f"[104] 正在搜尋...")
    c104, jobs104 = spider104.search(keyword, max_num=max_num)
    print(f"   => 找到 {c104} 筆，已抓 {len(jobs104)} 筆")
    
    #執行1111
    print(f"[1111] 正在搜尋...")
    c1111, jobs1111 = spider1111.search(keyword, max_num=max_num)
    print(f"   => 找到 {c1111} 筆，已抓 {len(jobs1111)} 筆")
    
    #資料整合
    all_jobs = []
    for job in jobs104:
        all_jobs.append(spider104.search_job_transform(job))
    for job in jobs1111:
        all_jobs.append(spider1111.search_job_transform(job))
        
    #存檔邏輯
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        cols = ['platform', 'name', 'company_name', 'salary', 'location', 'job_url']
        df = df[cols]
        
        print("\n--- 整合搜尋結果預覽 ---")
        print(df.head())
        
        filename = f"combined_jobs_{keyword}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n檔案已儲存: {filename}")
        
        try:
            conn = sqlite3.connect('job_database.db')
            df.to_sql('search_results', conn, if_exists='replace', index=False)
            conn.close()
            print("資料已寫入資料庫 (job_database.db)")
        except:
            print("資料庫寫入失敗")
    else:
        print("\n兩個平台都沒抓到資料")

def run_chart_analysis():
    """功能 2: 程式語言統計圖表"""
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
        
        results.append({
            "Language": lang,
            "104": c104,
            "1111": c1111,
            "Total": c104 + c1111
        })
        time.sleep(0.5)
        
    # 畫圖
    df = pd.DataFrame(results).sort_values(by="Total", ascending=False)
    
    if df['Total'].sum() > 0:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
        plt.rcParams['axes.unicode_minus'] = False
        
        ax = df.plot(x="Language", y=["104", "1111"], kind="bar", 
                     figsize=(10, 6), color=['#F29048', '#4DA6FF'], width=0.8)
        
        plt.title("2025 程式語言職缺比較")
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
        print("無數據可繪圖")