# job_analysis.py
import time
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import re # 新增 regex 用來處理薪資字串

from job_spider_104 import Job104Spider
from job_spider_1111 import Job1111Spider
from export_high_salary import export_high_salary
from plot_location_pie import plot_location_pie
from plot_salary_distribution import plot_salary_distribution


# ==============================================================================
# 原本的功能函式 (run_job_search, run_chart_analysis) 
# 我稍微修改 run_job_search 讓它最後詢問是否要執行進階分析
# ==============================================================================

def run_job_search():
    """功能 1: 整合搜尋 (同時查 104 與 1111)"""
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    keyword = input("\n請輸入關鍵字 (例如 Python): ")
    try:
        max_num = int(input("請輸入各平台要抓取的筆數 (建議 50 筆以上分析才準): "))
    except:
        max_num = 20 # 預設多一點，不然圖很難看

    print("-" * 30)
    
    # 執行搜尋
    print(f"[104] 正在搜尋...")
    c104, jobs104 = spider104.search(keyword, max_num=max_num)
    
    print(f"[1111] 正在搜尋...")
    c1111, jobs1111 = spider1111.search(keyword, max_num=max_num)
    
    # 資料整合
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
            print("資料已寫入資料庫 (job_database.db)")
        except:
            print("資料庫寫入失敗")
        
        # === 這裡呼叫新的分析功能 ===
        print("\n是否要進行進階分析 (薪資分佈、地區佔比、高薪快篩)?")
        do_analyze = input("輸入 y 開始分析，其他鍵跳過: ")
        
        if do_analyze.lower() == 'y':
            #薪資分佈圖
            plot_salary_distribution(df)
            
            #地區佔比圖
            plot_location_pie(df)
            
            #高薪快篩
            try:
                money = int(input("\n請輸入高薪定義 (例如 50000): "))
            except:
                money = 50000
            export_high_salary(df, threshold=money)
            
    else:
        print("\n兩個平台都沒抓到資料")

def run_chart_analysis():
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    languages = ['Python', 'Java', 'JavaScript', 'C#', 'PHP', 'Swift', 'Go']
    results = []

    print("\n開始統計各語言職缺數 (API 模式)...")
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
        ax = df.plot(x="Language", y=["104", "1111"], kind="bar", figsize=(10, 6), color=['#F29048', '#4DA6FF'], width=0.8)
        plt.title("2025 程式語言職缺比較 (API 統計)")
        plt.tight_layout()
        plt.savefig("job_statistics.png")
        print(f"\n圖表已生成: job_statistics.png")
        plt.show()
    else:
        print("無數據")