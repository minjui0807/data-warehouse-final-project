import time
import random
import requests

# 104 爬蟲類別
class Job104Spider():
    def search(self, keyword, max_num=10, filter_params=None, sort_type='符合度', is_sort_asc=False):
        """搜尋職缺"""
        jobs = []
        total_count = 0
        url = 'https://www.104.com.tw/jobs/search/api/jobs'

        params = {
            'ro': '0', 'kwop': '7', 'keyword': keyword,
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

        page = 1
        
        while len(jobs) < max_num:
            params['page'] = page
            try:
                r = requests.get(url, params=params, headers=headers)
                if r.status_code != 200: break
                
                data = r.json()
                if 'metadata' in data and 'pagination' in data['metadata']:
                    total_count = data['metadata']['pagination']['total']
                    last_page = data['metadata']['pagination']['lastPage']
                else: break

                current_jobs = data.get('data', [])
                if not current_jobs: break

                jobs.extend(current_jobs)
                
                if page >= last_page or last_page == 0: break
                page += 1
                if max_num > 50: time.sleep(random.uniform(0.5, 1)) 

            except Exception as e:
                print(f"[104] 解析錯誤: {e}")
                break

        return total_count, jobs[:max_num]

    def search_job_transform(self, job_data):
        """資料轉換"""
        links = job_data.get('link', {})
        job_url = f"https:{links.get('job', '')}" if links.get('job') else ''
        
        salary_str = job_data.get('salaryDesc', '')
        if not salary_str:
            high = int(job_data.get('salaryHigh', 0))
            low = int(job_data.get('salaryLow', 0))
            if low > 0 and high > 0 and high < 9999999: salary_str = f"{low} - {high}"
            elif low > 0: salary_str = f"{low} 以上"
            else: salary_str = "面議"

        job = {
            'platform': '104',
            'name': job_data.get('jobName', ''),
            'company_name': job_data.get('custName', ''),
            'salary': salary_str,
            'job_url': job_url,
            'location': f"{job_data.get('jobAddrNoDesc', '')} {job_data.get('jobAddress', '')}"
        }
        return job
