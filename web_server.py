from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import matplotlib
# 設定 Matplotlib 後端為 Agg，避免在無 GUI 環境下報錯
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import re
import sqlite3
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from concurrent.futures import ThreadPoolExecutor

# 引用自訂爬蟲模組
from job_spider_104 import Job104Spider
from job_spider_1111 import Job1111Spider

app = Flask(__name__)

COLUMN_ORDER = [
    'platform', 
    'update_date', 
    'name', 
    'company_name', 
    'salary', 
    'job_url', 
    'location'
]

# --- 1. 設定區 ---
# 設定中文字型 (依據系統環境自動選擇)
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 輔助函式 ---

def fig_to_base64(fig):
    """將 Matplotlib 圖表轉換為 Base64 字串供網頁顯示"""
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight', transparent=True)
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

def parse_salary_for_web(salary_str):
    """網頁版專用的薪資解析"""
    salary_str = str(salary_str).replace(',', '')
    if '面議' in salary_str: return 0
    nums = re.findall(r'(\d+)', salary_str)
    if not nums: return 0
    nums = [int(n) for n in nums]
    avg_salary = sum(nums) / len(nums)
    # 簡單過濾極端值 (轉換時薪或年薪)
    if avg_salary < 1000: return avg_salary * 160
    if avg_salary > 300000: return avg_salary / 13
    return avg_salary

def get_city(addr):
    """從地址中提取城市名稱"""
    if isinstance(addr, str) and len(addr) >= 3:
        return addr[:3]
    return "其他"

# --- 3. 核心邏輯: 取得職缺總數 ---

def fetch_stats_by_keyword_task(keyword):
    """
    針對單一關鍵字，呼叫 Spider 取得 104 與 1111 的個別筆數。
    """
    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    
    count104 = 0
    count1111 = 0

    try:
        # 104
        res104 = spider104.search(keyword, max_num=1)
        if isinstance(res104, tuple):
            count104 = res104[0]
        elif isinstance(res104, list):
            count104 = len(res104)
            
        # 1111
        res1111 = spider1111.search(keyword, max_num=1)
        if isinstance(res1111, tuple):
            count1111 = res1111[0]
        elif isinstance(res1111, list):
            count1111 = len(res1111)

    except Exception as e:
        print(f"Error fetching stats for {keyword}: {e}")
    
    # [修改] 這裡不再相加，而是回傳個別數字
    return keyword, count104, count1111

# --- 4. 頁面路由 ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

# --- 5. API 路由: 職缺趨勢比較 (新功能) ---

@app.route('/api/compare_jobs', methods=['POST'])
def compare_jobs():
    data = request.json
    keywords = data.get('keywords', [])
    
    # 資料清洗
    keywords = list(set([k.strip() for k in keywords if k.strip()]))
    
    if not keywords:
        return jsonify({'status': 'error', 'message': '請至少輸入一個職缺關鍵字'})

    results_list = []

    # 平行處理
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_stats_by_keyword_task, kw) for kw in keywords]
        for future in futures:
            kw, c104, c1111 = future.result() # [修改] 接收三個值
            results_list.append({
                'keyword': kw,
                '104': c104,
                '1111': c1111,
                'total': c104 + c1111
            })

    # 排序：依據「總數」由高到低排序，這樣圖表比較整齊
    results_list.sort(key=lambda x: x['total'], reverse=True)

    # 準備繪圖資料
    if results_list:
        labels = [item['keyword'] for item in results_list]
        counts_104 = [item['104'] for item in results_list]
        counts_1111 = [item['1111'] for item in results_list]

        # --- 開始繪圖 (分組長條圖) ---
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 設定深色背景
        fig.patch.set_facecolor('#161616')
        ax.set_facecolor('#161616')

        # 設定長條圖位置
        x = np.arange(len(labels))  # 標籤位置
        width = 0.35  # 長條寬度

        # 繪製兩組長條 (104: 橘色, 1111: 藍色)
        # x - width/2 讓 104 往左偏，x + width/2 讓 1111 往右偏
        rects1 = ax.bar(x - width/2, counts_104, width, label='104', color='#f29045', alpha=0.9)
        rects2 = ax.bar(x + width/2, counts_1111, width, label='1111', color='#5ca1e6', alpha=0.9)

        # 設定標籤與標題
        ax.set_ylabel('職缺數', color='white')
        ax.set_title('各職缺平台數量比較', color='white', fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color='white', fontsize=11)
        ax.tick_params(axis='y', colors='white')

        # 設定圖例 (Legend)
        legend = ax.legend()
        plt.setp(legend.get_texts(), color='black') # 圖例文字設為黑色(預設背景白)或自訂

        # 輔助函式：在長條圖上方標示數字
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{int(height):,}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 垂直偏移 3 points
                            textcoords="offset points",
                            ha='center', va='bottom', color='white', fontsize=9, fontweight='bold')

        autolabel(rects1)
        autolabel(rects2)

        chart_base64 = fig_to_base64(fig)
        plt.close(fig)
        
        # 為了回傳給前端列表顯示，我們轉一下格式
        # 前端原本是 {kw: total}，現在我們可以在前端顯示更細，但為了相容舊版JS，
        # 這裡的 data 還是回傳總數字典，或者您可以修改前端 JS 來顯示細項。
        # 為了簡單起見，這裡 data 回傳總數 (用於列表排序)，圖表則顯示詳細比較。
        simple_data = {item['keyword']: item['total'] for item in results_list}

        return jsonify({
            'status': 'success',
            'chart': chart_base64,
            'data': simple_data 
        })
    else:
        return jsonify({'status': 'error', 'message': '無法取得數據'})

# --- 6. API 路由: 傳統詳細搜尋 (舊功能保留) ---

@app.route('/api/search', methods=['POST'])
def search_jobs():
    data = request.json
    keyword = data.get('keyword', 'Python')
    try: max_num = int(data.get('max_num', 20))
    except: max_num = 20

    spider104 = Job104Spider()
    spider1111 = Job1111Spider()
    jobs_data = []

    # 平行搜尋兩個平台
    with ThreadPoolExecutor(max_workers=2) as executor:
        future104 = executor.submit(spider104.search, keyword, max_num)
        future1111 = executor.submit(spider1111.search, keyword, max_num)
        
        # 這裡假設 search 回傳 (count, list)，我們取 [1] 是列表
        try:
            res104 = future104.result()
            list104 = res104[1] if isinstance(res104, tuple) else res104
            for job in list104: jobs_data.append(spider104.search_job_transform(job))
        except Exception as e:
            print(f"104 Search Error: {e}")

        try:
            res1111 = future1111.result()
            list1111 = res1111[1] if isinstance(res1111, tuple) else res1111
            for job in list1111: jobs_data.append(spider1111.search_job_transform(job))
        except Exception as e:
            print(f"1111 Search Error: {e}")

    if not jobs_data:
        return jsonify({'status': 'error', 'message': '未找到相關職缺'})

    df = pd.DataFrame(jobs_data)
    
    # --- 開始繪圖 (已修改為黑底風格) ---
    charts = {}
    
    # A. 薪資分佈圖 (黑底 + 金色長條)
    df['avg_salary'] = df['salary'].apply(parse_salary_for_web)
    salary_valid = df[df['avg_salary'] > 20000]['avg_salary']
    
    if not salary_valid.empty:
        # 設定畫布大小與背景色
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        fig1.patch.set_facecolor('#161616')  # 圖片背景黑
        ax1.set_facecolor('#161616')        # 座標軸背景黑
        
        # 繪製直方圖
        n, bins, patches = ax1.hist(salary_valid, bins=15, color='#c6a96b', edgecolor='#161616', alpha=0.9)
        
        # 設定標題與文字顏色 (白色)
        ax1.set_title(f"{keyword} 職缺薪資分佈圖 (樣本數: {len(salary_valid)})", color='white', fontsize=16, pad=15)
        ax1.set_xlabel("平均月薪 (新台幣)", color='white', fontsize=12)
        ax1.set_ylabel("職缺數量", color='white', fontsize=12)
        
        # 設定刻度顏色
        ax1.tick_params(colors='white', axis='both', which='major', labelsize=10)
        
        # 設定格線 (白色虛線)
        ax1.grid(axis='y', linestyle='--', alpha=0.3, color='white')
        
        # 在柱狀圖上方標示數字
        for i in range(len(patches)):
            if n[i] > 0:
                ax1.text(patches[i].get_x() + patches[i].get_width() / 2, n[i], 
                         str(int(n[i])), 
                         ha='center', va='bottom', color='white', fontsize=10)

        charts['salary_dist'] = fig_to_base64(fig1)
        plt.close(fig1)

    # B. 地區分佈圖 (修正: 外部文字白，內部數字黑)
    city_counts = df['location'].apply(get_city).value_counts()
    if len(city_counts) > 6:
        main = city_counts[:6]
        other = pd.Series({'其他': city_counts[6:].sum()})
        city_counts = pd.concat([main, other])
    
    if not city_counts.empty:
        # 設定畫布大小與背景色
        fig2, ax2 = plt.subplots(figsize=(8, 8))
        fig2.patch.set_facecolor('#161616') # 圖片背景黑
        ax2.set_facecolor('#161616')        # 座標軸背景黑
        
        # 繪製圓餅圖，並接收回傳的三個物件：patches(扇形), texts(外部標籤), autotexts(內部百分比)
        patches, texts, autotexts = ax2.pie(
            city_counts, 
            labels=city_counts.index, 
            autopct='%1.1f%%', 
            startangle=140,
            colors=plt.cm.Pastel1.colors
            # 注意: 這裡移除了原本的 textprops={'color': 'white'}
        )
        
        # --- 分開設定文字顏色 ---
        
        # 1. 設定外部標籤 (縣市名稱) 為白色，並加大字體
        for text in texts:
            text.set_color('white')
            text.set_fontsize(12)
            
        # 2. 設定內部標籤 (百分比數字) 為黑色，以便在淺色扇形上閱讀
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold') # 加粗讓它更明顯

        # 設定標題為白色
        ax2.set_title(f"{keyword} 職缺地區分佈", color='white', fontsize=16, pad=10)
        
        charts['location_pie'] = fig_to_base64(fig2)
        plt.close(fig2)

    stats = {
        'total': len(df),
        'avg_salary': int(salary_valid.mean()) if not salary_valid.empty else 0,
        'count_104': len(df[df['platform'] == '104']),
        'count_1111': len(df[df['platform'] == '1111'])
    }

    return jsonify({'status': 'success', 'jobs': jobs_data, 'charts': charts, 'stats': stats})

# --- 7. 匯出與儲存功能 ---

@app.route('/api/save_db', methods=['POST'])
def save_db():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        
        if not jobs:
            return jsonify({'status': 'error', 'message': '沒有資料可儲存'})

        df = pd.DataFrame(jobs)
        
        # [關鍵修改] 強制重新排列欄位順序 (這會自動過濾掉不在列表中的欄位)
        df = df.reindex(columns=COLUMN_ORDER)
        
        # 連接資料庫
        conn = sqlite3.connect('job_database.db')
        
        # 寫入資料庫
        # 注意: if_exists='replace' 會刪除舊表重建，這樣欄位順序才會更新
        # 如果改用 'append'，且舊資料庫欄位順序不同，可能會報錯
        df.to_sql('search_results', conn, if_exists='replace', index=False)
        
        conn.close()
        return jsonify({'status': 'success', 'message': f'已成功將 {len(df)} 筆資料寫入 job_database.db'})
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/export_csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        jobs = data.get('jobs', [])
        keyword = data.get('keyword', 'data')
        
        if not jobs:
            return jsonify({'status': 'error', 'message': '沒有資料可匯出'})

        df = pd.DataFrame(jobs)
        
        # [關鍵修改] 強制重新排列欄位順序
        df = df.reindex(columns=COLUMN_ORDER)
        
        csv_buffer = io.BytesIO()
        # 轉成 CSV
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_buffer.seek(0)
        
        filename = f"{keyword}_jobs.csv"
        return send_file(csv_buffer, mimetype='text/csv', as_attachment=True, download_name=filename)
    except Exception as e:
        print(f"CSV Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})