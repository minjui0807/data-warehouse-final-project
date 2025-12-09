import time
import random
import requests
from pyquery import PyQuery as pq

# 1111 爬蟲類別
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

    def search_html(self, keyword, max_num=10):
        """HTML 爬蟲方式搜尋職缺 (使用 PyQuery)"""
        jobs = []
        base_url = f'https://www.1111.com.tw/search/job?ks={keyword}'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
            'Referer': 'https://www.1111.com.tw/search/job',
        }
        
        page = 1
        while len(jobs) < max_num:
            try:
                params = {'page': page}
                r = requests.get(base_url, params=params, headers=headers, timeout=10)
                r.encoding = 'utf-8'
                
                if r.status_code != 200:
                    break
                
                # 使用 PyQuery 進行 HTML 解析
                doc = pq(r.text)
                
                # PyQuery 選擇器定位職缺清單 (使用 jQuery 語法)
                job_items = doc('.job-item, .job-list-item, [data-job-id]')
                
                if not job_items:
                    # 備用選擇器
                    job_items = doc('div[class*="job"]')
                
                if not job_items:
                    break
                
                for item in job_items:
                    if len(jobs) >= max_num:
                        break
                    
                    try:
                        item_pq = pq(item)
                        
                        # PyQuery 提取各欄位資料
                        job_name = item_pq('.job-name, .js-job-link, h2').eq(0).text()
                        company_name = item_pq('.company-name, .js-company-link, h3').eq(0).text()
                        salary = item_pq('.salary, .job-salary, span[class*="salary"]').eq(0).text()
                        location = item_pq('.location, .job-location, span[class*="location"]').eq(0).text()
                        
                        # 提取職缺連結
                        job_url = item_pq('a').attr('href') or ''
                        if not job_url.startswith('http'):
                            job_url = f"https://www.1111.com.tw{job_url}" if job_url else ""
                        
                        # 過濾空資料
                        if job_name:
                            job_obj = {
                                'platform': '1111',
                                'name': job_name.strip(),
                                'company_name': company_name.strip() or '未知公司',
                                'salary': salary.strip() or '面議',
                                'location': location.strip() or '未知地點',
                                'job_url': job_url,
                            }
                            jobs.append(job_obj)
                    
                    except Exception as e:
                        print(f"[1111] 單筆解析錯誤: {e}")
                        continue
                
                if len(jobs) < max_num:
                    page += 1
                    time.sleep(random.uniform(0.5, 1.5))
                else:
                    break
            
            except Exception as e:
                print(f"[1111] HTML 爬蟲錯誤: {e}")
                break
        
        return len(jobs), jobs[:max_num]