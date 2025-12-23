import time
import random
import requests
import math
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

class Job1111Spider():
    def _fetch_page(self, page, base_url, params, headers):
        """
        [內部方法] 抓取單頁
        """
        local_params = params.copy()
        local_params['page'] = page
        
        if 'searchUrl' in local_params:
             local_params['searchUrl'] = local_params['searchUrl'].replace('page=1', f'page={page}')

        try:
            time.sleep(random.uniform(0.1, 0.5))
            
            r = requests.get(base_url, params=local_params, headers=headers, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                if 'result' in data:
                    result_data = data['result']
                    jobs = result_data.get('hits', [])
                    total = result_data.get('pagination', {}).get('totalCount', 0)
                    return total, jobs
                else:
                    return 0, []
            
            #加入防呆：遇到error:400(超過150頁限制)
            elif r.status_code == 400:
                return 0, []
            
            else:
                print(f"[1111] 第 {page} 頁請求失敗 code: {r.status_code}")

        except Exception as e:
            print(f"[1111] 第 {page} 頁抓取失敗: {e}")
        
        return 0, []

    def search(self, keyword, max_num=10):
        """
        搜尋 1111 職缺
        """
        url = 'https://www.1111.com.tw/api/v1/search/jobs/'

        safe_keyword = quote(keyword)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
            'Referer': f'https://www.1111.com.tw/search/job?ks={safe_keyword}',
        }

        search_url_val = f"/search/job?page=1&col=ab&sort=desc&ks={keyword}"
        
        params = {
            'page': 1, 'fromOffset': 0, 'sortBy': 'ab', 'sortOrder': 'desc',
            'conditionsText': keyword, 'searchUrl': search_url_val,
            'isSyncedRecommendJobs': 'false', 'keyword': keyword
        }

        per_page = 20 
        pages_needed = math.ceil(max_num / per_page)
        
        #限制最大頁數避免報錯
        if pages_needed > 150: pages_needed = 150
        
        all_jobs = []
        total_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_page = {
                executor.submit(self._fetch_page, page, url, params, headers): page
                for page in range(1, pages_needed + 1)
            }

            for future in as_completed(future_to_page):
                try:
                    count, jobs = future.result()
                    if jobs:
                        if count > total_count: total_count = count
                        all_jobs.extend(jobs)
                except Exception:
                    pass

        return total_count, all_jobs[:max_num]

    def search_job_transform(self, job_data):
        """
        資料轉換 - 依照指定欄位順序輸出
        欄位: 編號, 日期, 職位名稱, 職業類型, 公司名稱, 薪資, 地點, 平台, 連結
        """
        job_id = str(job_data.get('jobId', ''))
        job_url = f"https://www.1111.com.tw/job/{job_id}/" if job_id else ""
        
        location = ""
        wc = job_data.get('workCity')
        if isinstance(wc, list) and len(wc) > 0:
            location = wc[0].get('name', '')
        elif isinstance(wc, dict):
            location = wc.get('name', '')
            

        raw_date = str(job_data.get('updateAt', ''))
        update_date = raw_date.split(" ")[0]
        
        
        job = {
            'platform': '1111',
            'update_date': update_date,
            'name': job_data.get('title', ''),
            'company_name': job_data.get('companyName', ''),
            'salary': job_data.get('salary', '面議'),
            'job_url': job_url,
            'location': location
        }
        return job