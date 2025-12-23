import time
import random
import requests
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

class Job104Spider():
    def _fetch_page(self, page, base_url, params, headers):
        """
        [內部方法] 專門負責抓取「單一頁面」的資料
        這樣設計是為了讓 ThreadPool 可以獨立呼叫這個函式
        """
        #為了避免多執行緒共用同一個params物件造成衝突，這邊複製一份
        local_params = params.copy()
        local_params['page'] = page
        
        try:
            r = requests.get(base_url, params=local_params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                #確認回傳資料結構正確
                if 'data' in data:
                    jobs = data['data']
                    total = data.get('metadata', {}).get('pagination', {}).get('total', 0)
                    return total, jobs
        except Exception as e:
            print(f"[104] 第 {page} 頁抓取失敗: {e}")
        
        return 0, []

    def search(self, keyword, max_num=10, filter_params=None, sort_type='符合度', is_sort_asc=False):
        """
        搜尋職缺 (使用多執行緒加速版)
        """
        url = 'https://www.104.com.tw/jobs/search/api/jobs'

        #設定參數
        params = {
            'ro': '0',
            'kwop': '7',
            'keyword': keyword,
            'expansionType': 'area,spec,com,job,wf,wktm',
            'mode': 's', 'jobsource': 'index_s',
            'asc': '1' if is_sort_asc else '0',
        }
        if filter_params: params.update(filter_params)

        sort_dict = {'符合度': '1', '日期': '2', '經歷': '3', '學歷': '4', '應徵人數': '7', '待遇': '13'}
        params['order'] = sort_dict.get(sort_type, '1')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
            'Referer': 'https://www.104.com.tw/jobs/search/',
        }

        #計算需要抓幾頁 假設一頁20筆資料
        per_page = 20 
        pages_needed = math.ceil(max_num / per_page)
        
        all_jobs = []
        total_count = 0
        
        # print(f"[104] 預計抓取 {pages_needed} 頁以滿足 {max_num} 筆需求...")

        #啟動多執行緒
        #max_workers=10 代表同時開10個連線 建議不要超過20避免被鎖IP
        with ThreadPoolExecutor(max_workers=10) as executor:
            #建立任務清單：一次發送page 1到page N的請求
            future_to_page = {
                executor.submit(self._fetch_page, page, url, params, headers): page
                for page in range(1, pages_needed + 1)
            }

            #處理回傳結果(誰先回來就先處理誰)
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    count, jobs = future.result()
                    if count > 0:
                        total_count = count #更新總筆數
                        all_jobs.extend(jobs)
                        # print(f"  - 第 {page_num} 頁下載完成 (抓到 {len(jobs)} 筆)")
                    else:
                        # 如果某一頁沒資料，通常代表已經超過最後一頁了
                        pass
                except Exception as exc:
                    print(f"  - 第 {page_num} 頁執行異常: {exc}")

        #回傳結果
        # print(f"[104] 搜尋完成，共抓取 {len(all_jobs)} 筆資料")
        return total_count, all_jobs[:max_num]

    def search_job_transform(self, job_data):
        """資料轉換 (保持不變)"""
        links = job_data.get('link', {})
        job_url = f"{links.get('job', '')}" if links.get('job') else ''
        
        salary_str = job_data.get('salaryDesc', '')
        if not salary_str:
            high = int(job_data.get('salaryHigh', 0))
            low = int(job_data.get('salaryLow', 0))
            if low > 0 and high > 0 and high < 9999999: salary_str = f"{low} - {high}"
            elif low > 0: salary_str = f"{low} 以上"
            else: salary_str = "面議"

        raw_date = str(job_data.get('appearDate', ''))
        update_date = raw_date
        if len(raw_date) == 8:
            update_date = f"{raw_date[:4]}/{raw_date[4:6]}/{raw_date[6:]}"

        job = {
            'platform': '104',
            'update_date': update_date,
            'name': job_data.get('jobName', ''),
            'company_name': job_data.get('custName', ''),
            'salary': salary_str,
            'job_url': job_url,
            'location': f"{job_data.get('jobAddrNoDesc', '')} {job_data.get('jobAddress', '')}"
        }
        return job