# job_analysis.py
import matplotlib.pyplot as plt
from parse_salary import parse_salary

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False

def plot_salary_distribution(df):
    """功能: 薪資區間分佈圖"""
    print("\n正在生成薪資分佈圖...")
    
    # 確保資料不影響原始 DataFrame，使用 copy
    df_plot = df.copy()

    # 增加一欄 'avg_salary'
    df_plot['avg_salary'] = df_plot['salary'].apply(parse_salary)
    
    # 過濾掉 0 (面議) 和極端值
    salary_data = df_plot[df_plot['avg_salary'] > 20000]['avg_salary']
    
    if salary_data.empty:
        print("有效薪資數據不足，無法畫圖")
        return

    plt.figure(figsize=(10, 6))
    # 畫直方圖 (Histogram)
    plt.hist(salary_data, bins=15, color='#69b3a2', edgecolor='white', alpha=0.7)
    
    plt.title(f"職缺薪資分佈圖 (樣本數: {len(salary_data)})")
    plt.xlabel("平均月薪 (TWD)")
    plt.ylabel("職缺數量")
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    filename = "salary_histogram.png"
    plt.savefig("salary_histogram.png")
    print("圖表已儲存: salary_histogram.png")
    plt.show()

        