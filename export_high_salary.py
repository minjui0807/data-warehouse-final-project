import pandas as pd
import matplotlib.pyplot as plt
from parse_salary import parse_salary

def export_high_salary(df, threshold=50000):
    """
    功能: 高薪職缺快篩並匯出CSV
    """
    print(f"\n正在篩選月薪 {threshold} 以上的職缺...")
    
    df_filter = df.copy()
    
    # 計算薪資
    df_filter['avg_salary'] = df_filter['salary'].apply(parse_salary)
    
    # 篩選
    high_paying_jobs = df_filter[df_filter['avg_salary'] >= threshold]
    
    if not high_paying_jobs.empty:
        # 排序：由高到低
        high_paying_jobs = high_paying_jobs.sort_values(by='avg_salary', ascending=False)
        
        # 選取要顯示的欄位
        cols = ['platform', 'name', 'company_name', 'salary', 'location', 'job_url']
        result = high_paying_jobs[cols]
        
        print(f"找到 {len(result)} 筆高薪職缺！(前5筆預覽):")
        print(result.head())
        
        filename = "high_salary_jobs.csv"
        result.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"已匯出高薪清單: {filename}")
    else:
        print("沒找到符合條件的高薪職缺(可能都是面議)")