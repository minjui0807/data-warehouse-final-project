import time
import random
import requests
import math
import re
import threading  # <--- 補上這行！
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

class Job1111Spider():
    def __init__(self):
        self.abort_signal = False
        
        # [新增] 1111 的縣市代碼表 (用於突破 4500 筆限制)
        self.CITY_CODES = {
            '台北市': '100100', '新北市': '100200', '基隆市': '100300', '宜蘭縣': '100400',
            '新竹市': '100500', '新竹縣': '100600', '桃園市': '100700', '苗栗縣': '100800',
            '台中市': '100900', '彰化縣': '101000', '南投縣': '101100', '雲林縣': '101200',
            '嘉義市': '101300', '嘉義縣': '101400', '台南市': '101500', '高雄市': '101600',
            '屏東縣': '101700', '台東縣': '101800', '花蓮縣': '101900', '澎湖縣': '102000',
            '金門縣': '102100', '連江縣': '102200'
        }

    def _fetch_page(self, page, base_url, params, headers):
        """ [內部方法] 單頁抓取邏輯 (已優化防止卡死) """
        if self.abort_signal: return 0, []

        local_params = params.copy()
        local_params['page'] = page
        
        # 1111 特有的 URL 參數處理
        if 'searchUrl' in local_params:
             local_params['searchUrl'] = local_params['searchUrl'].replace('page=1', f'page={page}')

        # [修正 1] 強制關閉長連線
        headers['Connection'] = 'close'

        retries = 3
        while retries > 0:
            if self.abort_signal: return 0, []
            
            try:
                # [修正 2] 改用 smart_sleep
                self.smart_sleep(random.uniform(0.5, 1.2)) 
                
                # [修正 3] 加入 timeout=5
                r = requests.get(
                    base_url, 
                    params=local_params, 
                    headers=headers, 
                    timeout=5
                )
                
                if r.status_code == 200:
                    data = r.json()
                    jobs = []
                    total = 0
                    
                    # 1111 的資料結構有兩種可能
                    if 'result' in data:
                        jobs = data['result'].get('hits', [])
                        total = data['result'].get('pagination', {}).get('totalCount', 0)
                    elif 'data' in data:
                        jobs = data.get('data', [])
                    
                    if not jobs: return total, []
                    return total, jobs
                
                elif r.status_code == 429:
                    print(f"    [1111封鎖] IP請求過快 (429)，休息 20 秒...")
                    self.smart_sleep(20) # [修正] smart_sleep
                    retries -= 1
                    if retries == 0: self.abort_signal = True
                    continue

                elif r.status_code == 400:
                    # 1111 翻頁超過範圍有時會回傳 400，視為結束
                    return 0, [] 
                
                else:
                    print(f"    [警示] 第 {page} 頁回應碼: {r.status_code}")
                    retries -= 1
                    self.smart_sleep(3) # [修正] smart_sleep

            # [修正 4] 捕捉 Timeout 錯誤
            except requests.exceptions.Timeout:
                print(f"    [逾時] 第 {page} 頁連線 5 秒無回應，重試中...")
                retries -= 1

            except Exception as e:
                print(f"    [錯誤] 第 {page} 頁連線失敗: {e}")
                retries -= 1
                self.smart_sleep(3) # [修正] smart_sleep
        
        return 0, []

    def search(self, keyword, max_num=100000, city_code=None, sc_code=None):
        """
        [安全版] 只有在「翻頁下載」時才開執行緒，避免 Dummy 無限增生
        """
        self.abort_signal = False
        
        # 1. 基礎參數設定 (這部分不變)
        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        safe_keyword = quote(keyword)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': f'https://www.1111.com.tw/search/job?ks={safe_keyword}',
            'Connection': 'close'
        }
        
        search_url_str = f"/search/job?page=1&col=ab&sort=desc&ks={safe_keyword}"
        params = {
            'page': 1, 'sortBy': 'ab', 'sortOrder': 'desc',
            'conditionsText': keyword, 'searchUrl': search_url_str, 'keyword': keyword
        }

        if city_code:
            params['d0'] = city_code
            params['searchUrl'] += f"&d0={city_code}"
            headers['Referer'] += f"&d0={city_code}"
        
        if sc_code:
            params['sc'] = sc_code
            params['searchUrl'] += f"&sc={sc_code}"
            headers['Referer'] += f"&sc={sc_code}"

        # 2. 先偵測總數
        # ★ 這裡順便加個 try-except 防止網路卡住
        try:
            first_total, first_page_jobs = self._fetch_page(1, url, params, headers)
        except Exception as e:
            print(f" [網路錯誤] 無法連線: {e}")
            return 0, []
        
        if first_total == 0:
            return 0, []

        all_collected_jobs = []
        seen_ids = set()

        # =================================================================
        # ★★★ 改動: 縣市加速版 (同時查 3 個縣市，平衡速度與穩定) ★★★
        # =================================================================
        if city_code is None and first_total > 2000:
            print(f"    [策略] 總數 {first_total} 筆，啟動「縣市平行掃描 (3線程)」...")
            
            # 定義一個內部的 worker 函式來處理單一縣市
            def process_city_task(item):
                c_name, c_code = item
                if self.abort_signal: return []
                # 這裡遞迴呼叫 search，但因為 search 內部還有鎖，所以要小心
                # 這裡設 max_num=0 是為了只抓資料不遞迴列印太多 log，或者依你的邏輯調整
                _, sub_jobs = self.search(keyword, max_num, c_code, None)
                if sub_jobs:
                    print(f"    [進度] {c_name} 完成 | 抓取: {len(sub_jobs)}")
                return sub_jobs

            # 使用 ThreadPoolExecutor 同時跑 3 個縣市
            # 注意：max_workers=3 是安全值。
            # 計算公式：3 (縣市) x 5 (底層翻頁線程) = 同時間最多 15 個連線，這很安全。
            with ThreadPoolExecutor(max_workers=3) as city_executor:
                # 提交所有縣市的任務
                future_to_city = {
                    city_executor.submit(process_city_task, item): item[0] 
                    for item in self.CITY_CODES.items()
                }

                for future in as_completed(future_to_city):
                    if self.abort_signal: break
                    try:
                        city_jobs = future.result()
                        # 彙整資料 (加上 Lock 比較安全，雖然 list append 是 thread-safe 的，但習慣上加一下)
                        for job in city_jobs:
                            jid = str(job.get('jobId', ''))
                            if jid and jid not in seen_ids:
                                seen_ids.add(jid)
                                all_collected_jobs.append(job)
                    except Exception as e:
                        print(f"    [略過] 某縣市掃描失敗: {e}")

            return first_total, all_collected_jobs

        # =================================================================
        # ★★★ 改動 2: 拆薪資 (改成普通 for 迴圈) ★★★
        # =================================================================
        if city_code is not None and sc_code is None and first_total > 2000:
            # print(f"    [細分] {city_code} 資料量大，進行薪資拆分...")
            
            SALARY_RANGES = {
                '3萬以下': '10010', '3萬-4萬': '10020', '4萬-5萬': '10030',
                '5萬-6萬': '10040', '6萬-7萬': '10050', '7萬-8萬': '10060',
                '8萬-9萬': '10070', '9萬-10萬': '10080', '10萬以上': '10090', '面議': '100000'
            }

            for s_name, sc in SALARY_RANGES.items():
                if self.abort_signal: break
                
                # 遞迴呼叫 (單線程)
                _, jobs = self.search(keyword, max_num, city_code, sc)
                
                for job in jobs:
                    jid = str(job.get('jobId', ''))
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        all_collected_jobs.append(job)
            
            return first_total, all_collected_jobs


        # =================================================================
        # ★★★ 改動 3: 只有這裡才開 ThreadPool (真正的下載) ★★★
        # =================================================================
        
        all_jobs = []
        all_jobs.extend(first_page_jobs)
        
        real_target_num = min(max_num, first_total)
        pages_needed = math.ceil(real_target_num / 20)
        if pages_needed > 100: pages_needed = 100 # 強制上限，避免單一區間跑太久

        if pages_needed <= 1:
            return first_total, all_jobs

        # ★ 這裡維持 ThreadPool，但因為上面都是單線程，所以同一時間全電腦只會有這 5 個 Thread 在跑
        # 這樣就不會爆炸了
        with ThreadPoolExecutor(max_workers=5) as page_executor:
            future_to_page = {
                page_executor.submit(self._fetch_page, page, url, params, headers): page
                for page in range(2, pages_needed + 1)
            }

            for future in as_completed(future_to_page):
                if self.abort_signal: break
                try:
                    _, jobs = future.result()
                    if jobs: all_jobs.extend(jobs)
                except Exception: pass

        return first_total, all_jobs
    
    
    def search_job_transform(self, job_data):
        # ... (這部分保持不變) ...
        job_id = str(job_data.get('jobId', ''))
        job_url = f"https://www.1111.com.tw/job/{job_id}/" if job_id else ""
        
        location = ""
        wc = job_data.get('workCity')
        if isinstance(wc, list) and len(wc) > 0:
            location = wc[0].get('name', '')
        elif isinstance(wc, dict):
            location = wc.get('name', '')

        raw_date = str(job_data.get('updateAt', ''))
        update_date = raw_date.split(" ")[0] if raw_date else ""
        
        salary_str = job_data.get('salary', '面議')
        salary_sort = 0
        try:
            nums = re.findall(r'\d+', salary_str.replace(',', ''))
            if nums: salary_sort = int(nums[0])
        except: pass
        
        job = {
            'platform': '1111',
            'update_date': update_date,
            'name': job_data.get('title', ''),
            'company_name': job_data.get('companyName', ''),
            'salary': salary_str,
            'salary_sort': salary_sort,
            'job_url': job_url,
            'location': location
        }
        return job


    def smart_sleep(self, seconds):
        """
        聰明睡覺：會將長時間的睡眠切成小段，
        每 0.1 秒檢查一次是否收到停止訊號 (abort_signal)。
        """
        # 把秒數切成 0.1 秒的片段
        steps = int(seconds * 10) 
        for _ in range(steps):
            if self.abort_signal:
                return # 收到停止訊號，馬上醒來！
            time.sleep(0.1)
        
        # 處理剩下不足 0.1 秒的零頭
        remaining = seconds - (steps * 0.1)
        if remaining > 0 and not self.abort_signal:
            time.sleep(remaining)