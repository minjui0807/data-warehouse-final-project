import time
import random
import requests

#1111爬蟲類別
class Job1111Spider():
    def search(self, keyword, max_num=10):
        """搜尋 1111 職缺"""
        jobs = []
        total_count = 0
        url = 'https://www.1111.com.tw/api/v1/search/jobs/'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
            'Referer': f'https://www.1111.com.tw/search/job?ks={keyword}',
        }

        page = 1
        
        while len(jobs) < max_num:
            search_url_val = f"/search/job?page={page}&col=ab&sort=desc&ks={keyword}"
            params = {
                'page': page, 'fromOffset': 0, 'sortBy': 'ab', 'sortOrder': 'desc',
                'conditionsText': keyword, 'searchUrl': search_url_val,
                'isSyncedRecommendJobs': 'false', 'keyword': keyword
            }

            try:
                r = requests.get(url, params=params, headers=headers)
                if r.status_code != 200: break

                data = r.json()
                if 'result' not in data: break
                
                result_data = data['result']
                if 'pagination' in result_data:
                    total_count = result_data['pagination'].get('totalCount', 0)
                
                current_jobs = result_data.get('hits', [])
                if not current_jobs: break
                
                jobs.extend(current_jobs)
                
                if len(jobs) >= total_count: break
                page += 1
                if max_num > 50: time.sleep(random.uniform(0.5, 1))

            except Exception as e:
                print(f"[1111] 發生錯誤: {e}")
                break

        return total_count, jobs[:max_num]

    def search_job_transform(self, job_data):
        """資料轉換"""
        job_id = str(job_data.get('jobId', ''))
        job_url = f"https://www.1111.com.tw/job/{job_id}/" if job_id else ""
        
        location = ""
        if 'workCity' in job_data and job_data['workCity']:
            location = job_data['workCity'].get('name', '')

        job = {
            'platform': '1111',
            'name': job_data.get('title', ''),
            'company_name': job_data.get('companyName', ''),
            'salary': job_data.get('salary', '面議'),
            'job_url': job_url,
            'location': location
        }
        return job

    