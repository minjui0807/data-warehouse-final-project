import time
import random
import requests
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

class Job104Spider():
    def __init__(self):
        # [新增] 緊急煞車開關
        # 只要變成 True，所有執行緒都會立刻停止工作
        self.abort_signal = False

    def _fetch_page(self, page, base_url, params, headers):
        """
        [內部方法] 包含 Retry 與 緊急煞車機制 (已優化防止卡死)
        """
        # 1. 檢查是否已經啟動煞車
        if self.abort_signal:
            return 0, []

        local_params = params.copy()
        local_params['page'] = page
        
        # [修正 1] 強制關閉長連線，避免 Socket 卡住無法結束
        headers['Connection'] = 'close'
        
        # 設定單頁最大重試次數
        retries = 3
        
        while retries > 0:
            # 再次檢查煞車
            if self.abort_signal:
                return 0, []

            try:
                # [修正 2] 改用 smart_sleep 取代 time.sleep
                # 這樣你按停止時，它不用睡完就能馬上醒來
                self.smart_sleep(random.uniform(0.5, 1.8))
                
                # [修正 3] 加入 timeout=5
                # 如果 5 秒對方沒傳完資料，強制報錯斷開，不要傻等
                r = requests.get(
                    base_url, 
                    params=local_params, 
                    headers=headers, 
                    timeout=5 
                )
                
                if r.status_code == 200:
                    data = r.json()
                    if 'data' in data:
                        jobs = data['data']
                        total = data.get('metadata', {}).get('pagination', {}).get('total', 0)
                        return total, jobs
                
                elif r.status_code == 429:
                    print(f"    [封鎖] 第 {page} 頁被 429 限制，暫停 20 秒... (剩餘重試: {retries-1})")
                    self.smart_sleep(20) # [修正] 這裡也要用 smart_sleep
                    retries -= 1
                    
                    if retries == 0:
                        print(f"    [致命錯誤] 第 {page} 頁多次重試失敗，IP 可能已被重度封鎖。")
                        print(f"    [系統] 正在啟動緊急煞車，停止後續所有請求...")
                        self.abort_signal = True
                        return 0, []
                    
                    continue 

                else:
                    print(f"    [警示] 第 {page} 頁回應碼: {r.status_code}")
                    retries -= 1
                    self.smart_sleep(3) # [修正] 這裡也要用 smart_sleep

            # [修正 4] 專門處理逾時 (Timeout)
            # 這樣當 requests.get 超過 5 秒被切斷時，會進來這裡而不是報錯崩潰
            except requests.exceptions.Timeout:
                print(f"    [逾時] 第 {page} 頁連線超過 5 秒未回應，重試中...")
                retries -= 1
                # 逾時通常是網路卡住，不用睡太久，稍微喘口氣重試即可
                
            except Exception as e:
                print(f"    [錯誤] 第 {page} 頁連線失敗: {e}")
                retries -= 1
                self.smart_sleep(3) # [修正] 這裡也要用 smart_sleep
        
        return 0, []

    def search(self, keyword, max_num=10, filter_params=None, sort_type='符合度', is_sort_asc=False):
        """
        搜尋職缺 (支援煞車機制)
        """
        # 每次新搜尋都要重置煞車與變數
        self.abort_signal = False 
        
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.104.com.tw/jobs/search/',
        }

        all_jobs = []
        total_count = 0
        
        print(f"    [系統] 正在進行首頁偵測...")

        # --- 第一步：抓第 1 頁 ---
        first_total, first_page_jobs = self._fetch_page(1, url, params, headers)
        
        # 如果第一頁就觸發煞車或沒資料
        if self.abort_signal:
            print("    [系統] 首頁即遭封鎖，停止搜尋。")
            return 0, []

        if not first_page_jobs:
            print("    [系統] 找不到任何資料")
            return 0, []

        total_count = first_total
        all_jobs.extend(first_page_jobs)
        print(f"    [系統] 104 官方顯示總數: {total_count} 筆")

        # --- 第二步：校正 ---
        real_target_num = min(max_num, total_count)
        per_page = 20
        pages_needed = math.ceil(real_target_num / per_page)
        
        if pages_needed <= 1:
            return total_count, all_jobs[:max_num]

        print(f"    [系統] 校正後預計抓取: {real_target_num} 筆 (需再抓 {pages_needed - 1} 頁)")

        # --- 第三步：多執行緒 ---
        # 建議 max_workers 設為 5，雖然慢但比較不容易觸發煞車
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {
                executor.submit(self._fetch_page, page, url, params, headers): page
                for page in range(2, pages_needed + 1)
            }

            for i, future in enumerate(as_completed(future_to_page)):
                # 如果煞車被拉下，直接跳出迴圈，不再等待其他結果
                if self.abort_signal:
                    break 

                if len(all_jobs) >= max_num:
                    print(f"    [系統] 資料量已達標 ({len(all_jobs)} / {max_num})，提早停止搜尋。")
                    self.abort_signal = True  # 拉下煞車，通知其他執行緒不要再抓了
                    break

                try:
                    count, jobs = future.result()
                    if jobs:
                        all_jobs.extend(jobs)
                        if (i+1) % 50 == 0:
                            print(f"    [104 進度] 已處理 {i+1} 頁... (目前 {len(all_jobs)} 筆)")
                except Exception:
                    pass
        
        if self.abort_signal:
            print(f"    [系統] 搜尋因 IP 封鎖而提前終止。共成功抓取 {len(all_jobs)} 筆。")
        else:
            print(f"    [系統] 搜尋完成。共成功抓取 {len(all_jobs)} 筆。")

        return total_count, all_jobs[:max_num]

    def search_job_transform(self, job_data):
        # (這裡保持不變，照抄舊的即可)
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
        
        salary_sort = 0
        try:
             salary_sort = int(job_data.get('salaryLow', 0))
        except:
             pass

        job = {
            'platform': '104',
            'update_date': update_date,
            'name': job_data.get('jobName', ''),
            'company_name': job_data.get('custName', ''),
            'salary': salary_str,
            'salary_sort': salary_sort,
            'job_url': job_url,
            'location': f"{job_data.get('jobAddrNoDesc', '')} {job_data.get('jobAddress', '')}"
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