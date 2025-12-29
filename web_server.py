from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import matplotlib
matplotlib.use('Agg') # 設定後端，避免視窗跳出
import matplotlib.pyplot as plt
import io
import base64
import re
import sqlite3
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor
import matplotlib.ticker as ticker 
import tempfile
from datetime import datetime
import time

# 引用自訂爬蟲模組
from job_spider_104 import Job104Spider
from job_spider_1111 import Job1111Spider

app = Flask(__name__)

# --- 全域設定 ---
CPU_CORES = os.cpu_count() or 4
MAX_WORKERS_TRANSFORM = CPU_CORES * 10 
MAX_WORKERS_SEARCH = 4 

COLUMN_ORDER = ['platform', 'update_date', 'name', 'company_name', 'salary', 'job_url', 'location']

# 設定中文字型與負號顯示
import platform
if platform.system() == "Windows":
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
elif platform.system() == "Darwin": 
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
else:
    plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# [配色方案]
BG_COLOR = '#161616'     
TEXT_COLOR = '#E0E0E0'   
BAR_COLOR = '#C6A96B'    # 金色

PIE_COLORS = [
    '#F6E59E', 
    '#ECD895', 
    '#D8BF84', 
    '#C6A96B', 
    '#B89D60', 
    '#A88F58', 
    '#8F7A4A'  
]

def fig_to_base64(fig):
    img = io.BytesIO()
    # [關鍵] pad_inches=0.05 設得非常小，盡量減少黑邊
    fig.savefig(img, format='png', bbox_inches='tight', facecolor=BG_COLOR, edgecolor='none', pad_inches=0.05)
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

def parse_salary_for_web(salary_str):
    salary_str = str(salary_str).replace(',', '')
    if '面議' in salary_str: return 0
    nums = re.findall(r'(\d+)', salary_str)
    if not nums: return 0
    nums = [int(n) for n in nums]
    avg_salary = sum(nums) / len(nums)
    if avg_salary < 1000: return avg_salary * 160 # 時薪轉月薪
    if avg_salary > 5000000: return avg_salary / 12 # 年薪轉月薪
    if avg_salary > 300000: return avg_salary 
    return avg_salary

def filter_dataframe_by_salary(df, min_salary):
    if df.empty or min_salary is None: return df
    try:
        min_salary = int(min_salary)
        if min_salary <= 0: return df
        df['_temp_avg_salary'] = df['salary'].apply(parse_salary_for_web)
        filtered_df = df[df['_temp_avg_salary'] >= min_salary].copy()
        del filtered_df['_temp_avg_salary']
        return filtered_df
    except Exception as e:
        print(f"Filtering Error: {e}")
        return df

def get_city(addr):
    if isinstance(addr, str) and len(addr) >= 3:
        return addr[:3]
    return "其他"

def fetch_stats_by_keyword_task(keyword):
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    count104, count1111 = 0, 0
    try:
        res104 = spider104.search(keyword, max_num=1)
        if isinstance(res104, tuple): count104 = res104[0]
        elif isinstance(res104, list): count104 = len(res104)
            
        res1111 = spider1111.search(keyword, max_num=1)
        if isinstance(res1111, tuple): count1111 = res1111[0]
        elif isinstance(res1111, list): count1111 = len(res1111)
    except Exception as e:
        print(f"Error fetching stats for {keyword}: {e}")
    return keyword, count104, count1111

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compare_jobs', methods=['POST'])
def compare_jobs():
    data = request.json
    keywords = list(set([k.strip() for k in data.get('keywords', []) if k.strip()]))
    if not keywords: return jsonify({'status': 'error', 'message': '請至少輸入一個職缺關鍵字'})

    results_list = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_stats_by_keyword_task, kw) for kw in keywords]
        for future in futures:
            kw, c104, c1111 = future.result()
            results_list.append({'keyword': kw, '104': c104, '1111': c1111, 'total': c104 + c1111})

    results_list.sort(key=lambda x: x['total'], reverse=True)

    if results_list:
        labels = [item['keyword'] for item in results_list]
        counts_104 = [item['104'] for item in results_list]
        counts_1111 = [item['1111'] for item in results_list]

        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        x = np.arange(len(labels))
        width = 0.35 

        rects1 = ax.bar(x - width/2, counts_104, width, label='104', color='#F08B51', alpha=0.9)
        rects2 = ax.bar(x + width/2, counts_1111, width, label='1111', color='#1C638C', alpha=0.9)

        ax.set_ylabel('職缺數', color=TEXT_COLOR)
        ax.set_title('各職缺平台數量比較', color=TEXT_COLOR, fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color=TEXT_COLOR, fontsize=11)
        ax.tick_params(axis='y', colors=TEXT_COLOR)
        
        for spine in ax.spines.values():
            spine.set_edgecolor('#444')

        legend = ax.legend(facecolor=BG_COLOR, edgecolor='#444')
        plt.setp(legend.get_texts(), color=TEXT_COLOR)

        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{int(height):,}', xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha='center', va='bottom', color=TEXT_COLOR, fontsize=9, fontweight='bold')
        autolabel(rects1)
        autolabel(rects2)

        chart_base64 = fig_to_base64(fig)
        plt.close(fig)
        simple_data = {item['keyword']: item['total'] for item in results_list}
        return jsonify({'status': 'success', 'chart': chart_base64, 'data': simple_data})
    else:
        return jsonify({'status': 'error', 'message': '無法取得數據'})

@app.route('/api/search', methods=['POST'])
def search_jobs():
    data = request.json
    keyword = data.get('keyword', 'Python')
    try: max_num = int(data.get('max_num', 20))
    except: max_num = 20

    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    raw_list_104 = []
    raw_list_1111 = []

    print(f"開始搜尋: {keyword} (目標: {max_num} 筆)")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_SEARCH) as search_executor:
        f1 = search_executor.submit(spider104.search, keyword, max_num)
        f2 = search_executor.submit(spider1111.search, keyword, max_num)
        try:
            res104 = f1.result()
            raw_list_104 = res104[1] if isinstance(res104, tuple) else res104
        except Exception as e: print(f"104 Error: {e}")
        try:
            res1111 = f2.result()
            raw_list_1111 = res1111[1] if isinstance(res1111, tuple) else res1111
        except Exception as e: print(f"1111 Error: {e}")

    jobs_data = []
    def task_104(j): return spider104.search_job_transform(j)
    def task_1111(j): return spider1111.search_job_transform(j)

    if raw_list_104 or raw_list_1111:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_TRANSFORM) as transform_executor:
            futures = []
            for job in raw_list_104: futures.append(transform_executor.submit(task_104, job))
            for job in raw_list_1111: futures.append(transform_executor.submit(task_1111, job))
            
            for f in futures:
                try:
                    res = f.result()
                    if res: jobs_data.append(res)
                except Exception: pass

    if not jobs_data:
        return jsonify({'status': 'error', 'message': '未找到相關職缺'})
    
    # --- 修改點：直接呼叫剛剛寫好的 analyze_jobs ---
    stats, charts = analyze_jobs(jobs_data, keyword)

    return jsonify({
        'status': 'success', 
        'jobs': jobs_data, 
        'charts': charts, 
        'stats': stats
    })

    df = pd.DataFrame(jobs_data)
    charts = {}

    # --- 1. 薪資分佈圖 (長寬比 2:1) ---
    df['avg_salary'] = df['salary'].apply(parse_salary_for_web)
    salary_valid = df[(df['avg_salary'] > 20000) & (df['avg_salary'] < 300000)]['avg_salary']
    
    if not salary_valid.empty:
        # [修改] 寬度設為 10，高度 5 (寬扁型)
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        fig1.patch.set_facecolor(BG_COLOR)
        ax1.set_facecolor(BG_COLOR)
        
        n, bins, patches = ax1.hist(salary_valid, bins=12, color=BAR_COLOR, edgecolor=BG_COLOR, alpha=0.9)
        
        ax1.set_title(f"{keyword} 薪資分佈", color=TEXT_COLOR, fontsize=16, pad=15)
        ax1.set_ylabel("職缺數", color=TEXT_COLOR, fontsize=11)
        ax1.set_xlabel("", color=BG_COLOR) 
        
        # [修正] X軸刻度格式化：40,000
        def salary_formatter(x, pos):
            if x >= 10000: return f'{int(x):,}'
            return str(int(x))
            
        ax1.xaxis.set_major_formatter(ticker.FuncFormatter(salary_formatter))
        
        ax1.tick_params(axis='x', colors=TEXT_COLOR, labelsize=10)
        ax1.tick_params(axis='y', colors=TEXT_COLOR)
        
        for spine in ax1.spines.values():
            spine.set_edgecolor('#444')
        ax1.grid(axis='y', linestyle='--', alpha=0.2, color='white')
        
        # 標示數值
        for i in range(len(patches)):
            if n[i] > 0:
                ax1.text(patches[i].get_x() + patches[i].get_width() / 2, n[i], str(int(n[i])), 
                         ha='center', va='bottom', color=TEXT_COLOR, fontsize=9)

        # [關鍵] 手動調整邊距
        plt.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.1)

        charts['salary_dist'] = fig_to_base64(fig1)
        plt.close(fig1)

    # --- 2. 地區分佈圖 (長寬比 接近 1:1) ---
    city_counts = df['location'].apply(get_city).value_counts()
    
    # 強制只取前 6 名 + 其他
    if len(city_counts) > 7:
        main = city_counts[:6]
        other_sum = city_counts[6:].sum()
        if other_sum > 0:
            other = pd.Series({'其他': other_sum})
            city_counts = pd.concat([main, other])
        else:
            city_counts = main
    
    if not city_counts.empty:
        # [修改] 寬度縮小到 6，高度維持 5 (方正型)
        fig2, ax2 = plt.subplots(figsize=(6, 5))
        fig2.patch.set_facecolor(BG_COLOR)
        
        wedges, texts, autotexts = ax2.pie(
            city_counts, 
            labels=city_counts.index, 
            autopct='%1.1f%%', 
            colors=PIE_COLORS[:len(city_counts)], 
            startangle=90,
            pctdistance=0.7,
            labeldistance=1.1, 
            textprops={'color': TEXT_COLOR, 'fontsize': 10}
        )
        
        for autotext in autotexts:
            autotext.set_color('#161616')
            autotext.set_weight('bold')
            autotext.set_fontsize(10)

        ax2.set_title(f"{keyword} 地區佔比", color=TEXT_COLOR, fontsize=16, pad=40)
        
        # [修正] 圖例更緊湊，放在正下方
        ax2.legend(wedges, city_counts.index,
                  loc="lower center", 
                  bbox_to_anchor=(0.5, -0.28), 
                  ncol=4, 
                  frameon=False, 
                  labelcolor=TEXT_COLOR,
                  fontsize=9)
        
        ax2.axis('equal')  
        # [關鍵] 極限縮減邊界
        plt.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.1)
        
        charts['location_pie'] = fig_to_base64(fig2)
        plt.close(fig2)

    stats = {
        'total': len(df),
        'avg_salary': int(salary_valid.mean()) if not salary_valid.empty else 0,
        'count_104': len(df[df['platform'] == '104']),
        'count_1111': len(df[df['platform'] == '1111'])
    }
    
    for job in jobs_data: 
        job['salary_sort'] = parse_salary_for_web(job.get('salary', ''))

    return jsonify({
        'status': 'success', 
        'jobs': jobs_data, 
        'charts': charts, 
        'stats': stats
    })

@app.route('/api/filter_jobs', methods=['POST'])
def filter_jobs():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        min_salary = data.get('min_salary', 0)
        if not jobs: return jsonify({'status': 'error', 'message': '沒有資料可篩選'})
        df = pd.DataFrame(jobs)
        filtered_df = filter_dataframe_by_salary(df, min_salary)
        return jsonify({
            'status': 'success', 'jobs': filtered_df.to_dict('records'),
            'count': len(filtered_df),
            'message': f'篩選完成，共找到 {len(filtered_df)} 筆月薪高於 {min_salary} 的職缺'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/export_db', methods=['POST'])
def export_db():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        keyword = data.get('keyword', 'jobs')
        min_salary = data.get('min_salary') 
        
        if not jobs: return jsonify({'status': 'error', 'message': '沒有資料可匯出'})

        # 1. 整理資料 (同原本邏輯)
        df = pd.DataFrame(jobs)
        if min_salary:
            df = filter_dataframe_by_salary(df, min_salary)
        
        for col in COLUMN_ORDER:
            if col not in df.columns: df[col] = ''
        df = df[COLUMN_ORDER]
        
        # 2. (新功能) 建立暫存檔
        fd, temp_path = tempfile.mkstemp(suffix='.db')
        os.close(fd) # 關閉檔案描述符，只要路徑

        # 3. (新功能) 寫入 SQLite 到暫存檔
        conn = sqlite3.connect(temp_path)
        df.to_sql('jobs', conn, if_exists='replace', index=False)
        conn.close()
        
        # 4. (新功能) 透過 send_file 讓瀏覽器下載
        return send_file(
            temp_path, 
            as_attachment=True, 
            download_name=f"{keyword}.db", 
            mimetype='application/x-sqlite3'
        )

    except Exception as e:
        print(f"DB Export Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/export_csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        keyword = data.get('keyword', 'data')
        min_salary = data.get('min_salary')
        if not jobs: return jsonify({'status': 'error', 'message': '沒有資料可匯出'})
        df = pd.DataFrame(jobs)
        if min_salary: df = filter_dataframe_by_salary(df, min_salary)
        for col in COLUMN_ORDER:
            if col not in df.columns: df[col] = ''
        df = df[COLUMN_ORDER]
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_buffer.seek(0)
        filename = f"{keyword}_jobs" + (f"_over_{min_salary}" if min_salary else "") + ".csv"
        return send_file(csv_buffer, mimetype='text/csv', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    

# --- 新增：獨立的分析與繪圖函數 (讓搜尋和歷史紀錄共用) ---
def analyze_jobs(jobs_data, keyword):
    if not jobs_data:
        return {}, {}

    df = pd.DataFrame(jobs_data)
    charts = {}

    # --- 1. 薪資分佈圖 (長寬比 2:1) ---
    # 先確保有 avg_salary 欄位
    if 'avg_salary' not in df.columns:
        df['avg_salary'] = df['salary'].apply(parse_salary_for_web)
    
    salary_valid = df[(df['avg_salary'] > 20000) & (df['avg_salary'] < 300000)]['avg_salary']
    
    if not salary_valid.empty:
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        fig1.patch.set_facecolor(BG_COLOR)
        ax1.set_facecolor(BG_COLOR)
        
        n, bins, patches = ax1.hist(salary_valid, bins=12, color=BAR_COLOR, edgecolor=BG_COLOR, alpha=0.9)
        
        ax1.set_title(f"{keyword} 薪資分佈", color=TEXT_COLOR, fontsize=16, pad=15)
        ax1.set_ylabel("職缺數", color=TEXT_COLOR, fontsize=11)
        
        def salary_formatter(x, pos):
            if x >= 10000: return f'{int(x):,}'
            return str(int(x))
            
        ax1.xaxis.set_major_formatter(ticker.FuncFormatter(salary_formatter))
        ax1.tick_params(axis='x', colors=TEXT_COLOR, labelsize=10)
        ax1.tick_params(axis='y', colors=TEXT_COLOR)
        
        for spine in ax1.spines.values():
            spine.set_edgecolor('#444')
        ax1.grid(axis='y', linestyle='--', alpha=0.2, color='white')
        
        for i in range(len(patches)):
            if n[i] > 0:
                ax1.text(patches[i].get_x() + patches[i].get_width() / 2, n[i], str(int(n[i])), 
                         ha='center', va='bottom', color=TEXT_COLOR, fontsize=9)

        plt.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.1)
        charts['salary_dist'] = fig_to_base64(fig1)
        plt.close(fig1)

    # --- 2. 地區分佈圖 ---
    city_counts = df['location'].apply(get_city).value_counts()
    
    if len(city_counts) > 7:
        main = city_counts[:6]
        other_sum = city_counts[6:].sum()
        if other_sum > 0:
            other = pd.Series({'其他': other_sum})
            city_counts = pd.concat([main, other])
        else:
            city_counts = main
    
    if not city_counts.empty:
        fig2, ax2 = plt.subplots(figsize=(6, 5))
        fig2.patch.set_facecolor(BG_COLOR)
        
        wedges, texts, autotexts = ax2.pie(
            city_counts, 
            labels=city_counts.index, 
            autopct='%1.1f%%', 
            colors=PIE_COLORS[:len(city_counts)], 
            startangle=90,
            pctdistance=0.7,
            labeldistance=1.1, 
            textprops={'color': TEXT_COLOR, 'fontsize': 10}
        )
        
        for autotext in autotexts:
            autotext.set_color('#161616')
            autotext.set_weight('bold')
            autotext.set_fontsize(10)

        ax2.set_title(f"{keyword} 地區佔比", color=TEXT_COLOR, fontsize=16, pad=40)
        
        ax2.legend(wedges, city_counts.index,
                   loc="lower center", 
                   bbox_to_anchor=(0.5, -0.28), 
                   ncol=4, 
                   frameon=False, 
                   labelcolor=TEXT_COLOR,
                   fontsize=9)
        
        ax2.axis('equal')  
        plt.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.1)
        
        charts['location_pie'] = fig_to_base64(fig2)
        plt.close(fig2)

    # --- 3. 計算統計數據 ---
    stats = {
        'total': len(df),
        'avg_salary': int(salary_valid.mean()) if not salary_valid.empty else 0,
        'count_104': len(df[df['platform'] == '104']),
        'count_1111': len(df[df['platform'] == '1111'])
    }
    
    # 確保每個 job 都有 salary_sort 供前端排序
    for job in jobs_data: 
        job['salary_sort'] = parse_salary_for_web(job.get('salary', ''))

    return stats, charts

# --- 新增：資料庫初始化函數 ---
def init_history_db():
    # 這裡只做基本檢查，實際建表邏輯在 save_history 內也有，雙重保險
    try:
        with sqlite3.connect('history_jobs.db') as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS history_batches (
                    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT,
                    save_time TEXT,
                    total_count INTEGER,
                    avg_salary INTEGER,
                    count_104 INTEGER,
                    count_1111 INTEGER,
                    chart_salary TEXT,
                    chart_location TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS history_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER,
                    platform TEXT,
                    name TEXT,
                    company_name TEXT,
                    location TEXT,
                    salary TEXT,
                    job_url TEXT,
                    update_date TEXT,
                    FOREIGN KEY(batch_id) REFERENCES history_batches(batch_id) ON DELETE CASCADE
                )
            ''')
            conn.commit()
    except Exception as e:
        print(f"Init DB Warning: {e}")

# 在程式啟動時執行初始化
init_history_db()

# --- 路由 1：儲存搜尋結果 (修正版：自動產圖並存入雙資料表) ---
@app.route('/api/save_history', methods=['POST'])
def save_history():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        keyword = data.get('keyword', '未命名搜尋')
        save_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not jobs:
            return jsonify({'status': 'error', 'message': '沒有資料可儲存'})

        # 1. 直接利用現有的分析函式產生統計數據與圖表字串
        try:
            stats, charts = analyze_jobs(jobs, keyword)
            avg_salary = stats.get('avg_salary', 0)
            count_104 = stats.get('count_104', 0)
            count_1111 = stats.get('count_1111', 0)
            chart_salary = charts.get('salary_dist', '')
            chart_location = charts.get('location_pie', '')
        except Exception as e:
            print(f"Analysis Error during save: {e}")
            avg_salary, count_104, count_1111 = 0, 0, 0
            chart_salary, chart_location = "", ""

        # 2. 寫入資料庫 (使用 with 語法確保連線安全)
        with sqlite3.connect('history_jobs.db') as conn:
            c = conn.cursor()

            # (A) 寫入主表 (Batch)
            c.execute('''
                INSERT INTO history_batches (keyword, save_time, total_count, avg_salary, count_104, count_1111, chart_salary, chart_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (keyword, save_time, len(jobs), avg_salary, count_104, count_1111, chart_salary, chart_location))
            
            batch_id = c.lastrowid

            # (B) 寫入明細表 (Details)
            details_data = []
            for j in jobs:
                details_data.append((
                    batch_id,
                    j.get('platform'),
                    j.get('name'),
                    j.get('company_name'),
                    j.get('location'),
                    j.get('salary'),
                    j.get('job_url'),
                    j.get('update_date')
                ))
            
            c.executemany('''
                INSERT INTO history_details (batch_id, platform, name, company_name, location, salary, job_url, update_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', details_data)
            
            conn.commit()

        return jsonify({'status': 'success', 'message': f'成功儲存 {len(jobs)} 筆資料！'})

    except Exception as e:
        print(f"Save Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# --- 路由 2：取得歷史紀錄列表 (修正版：讀取 history_batches) ---
@app.route('/api/get_history_list', methods=['GET'])
def get_history_list():
    try:
        with sqlite3.connect('history_jobs.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # 讀取主表資訊
            c.execute('''
                SELECT batch_id, keyword, save_time, total_count, avg_salary, count_104, count_1111 
                FROM history_batches 
                ORDER BY batch_id DESC
            ''')
            rows = c.fetchall()

        history_list = []
        for row in rows:
            history_list.append({
                'batch_id': row['batch_id'],
                'keyword': row['keyword'],
                'save_time': row['save_time'],
                'count': row['total_count'],
                'avg_salary': row['avg_salary'],
                'count_104': row['count_104'],
                'count_1111': row['count_1111']
            })
        
        return jsonify({'status': 'success', 'data': history_list})
    except Exception as e:
        print(f"Get List Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 路由 3：讀取某一筆歷史詳細資料 (修正版：關聯讀取並回傳圖表) ---
@app.route('/api/load_history_item', methods=['POST'])
def load_history_item():
    try:
        batch_id = request.json.get('batch_id')
        
        with sqlite3.connect('history_jobs.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # 1. 先讀取主表 (包含原本存好的圖表字串)
            c.execute('SELECT * FROM history_batches WHERE batch_id = ?', (batch_id,))
            batch_row = c.fetchone()
            
            if not batch_row:
                return jsonify({'status': 'error', 'message': '找不到該筆紀錄'})
            
            # 2. 讀取明細表 (職缺列表)
            c.execute('SELECT * FROM history_details WHERE batch_id = ?', (batch_id,))
            details_rows = c.fetchall()

        jobs = []
        for row in details_rows:
            jobs.append({
                'platform': row['platform'],
                'name': row['name'],
                'company_name': row['company_name'],
                'location': row['location'],
                'salary': row['salary'],
                'job_url': row['job_url'],
                'update_date': row['update_date']
            })
            
        # 準備回傳的資料
        # 我們直接使用資料庫存好的圖表，不重新生成，速度會比較快
        charts = {
            'salary_dist': batch_row['chart_salary'],
            'location_pie': batch_row['chart_location']
        }
        
        stats = {
            'total': batch_row['total_count'],
            'avg_salary': batch_row['avg_salary'],
            'count_104': batch_row['count_104'],
            'count_1111': batch_row['count_1111']
        }

        return jsonify({
            'status': 'success', 
            'jobs': jobs,
            'stats': stats,
            'charts': charts
        })

    except Exception as e:
        print(f"Load History Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
def get_db_connection():
    # 這是舊的 helper，為了相容性保留，但建議主要用 with sqlite3.connect
    conn = sqlite3.connect('history_jobs.db') 
    conn.row_factory = sqlite3.Row
    return conn

# --- 路由 4：刪除歷史紀錄 (修正版：正確縮排與連線) ---
@app.route('/api/delete_history', methods=['POST'])
def delete_history():
    batch_id = request.json.get('batch_id')
    try:
        with sqlite3.connect('history_jobs.db') as conn:
            c = conn.cursor()
            # 只要刪除主表，因設定了 ON DELETE CASCADE，明細表會自動刪除
            # 但為了保險，我們顯式刪除兩者
            c.execute('DELETE FROM history_details WHERE batch_id = ?', (batch_id,))
            c.execute('DELETE FROM history_batches WHERE batch_id = ?', (batch_id,))
            conn.commit()
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})