import time
import random
import requests
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util.ssl_ import create_urllib3_context

# --- 定義一個 TLS Adapter 來偽裝指紋 (保留新版邏輯) ---
class TlsAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1') 
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

class Job104Spider():
    ORANGE = '\033[38;5;208m'
    RESET = '\033[0m'

    def __init__(self):
        self.abort_signal = False
        self.is_blocked = False
        self.session = requests.Session()
        adapter = TlsAdapter()
        self.session.mount('https://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.104.com.tw/jobs/search/', 
        })

    def _fetch_page(self, page, base_url, params, headers):
        if self.abort_signal: return 0, []
        local_params = params.copy()
        local_params['page'] = page
        headers['Connection'] = 'close'
        retries = 3
        
        while retries > 0:
            if self.abort_signal: return 0, []
            try:
                self.smart_sleep(random.uniform(0.5, 2.5))
                r = self.session.get(base_url, params=local_params, headers=headers, timeout=5)
                
                if r.status_code == 200:
                    data = r.json()
                    if 'data' in data:
                        jobs = data['data']
                        total = data.get('metadata', {}).get('pagination', {}).get('total', 0)
                        return total, jobs
                
                elif r.status_code == 429:
                    # 429 封鎖提示
                    print(f"{self.ORANGE}    [104封鎖] 第 {page} 頁被 429 限制，暫停 20 秒... (剩餘重試: {retries-1}){self.RESET}")
                    self.smart_sleep(20)
                    retries -= 1
                    if retries == 0:
                        # 致命錯誤提示
                        print(f"{self.ORANGE}    [104致命錯誤] 第 {page} 頁多次重試失敗，IP 可能已被重度封鎖。{self.RESET}")
                        print(f"{self.ORANGE}    [104] 正在啟動緊急煞車，停止後續所有請求...{self.RESET}")
                        self.is_blocked = True
                        self.abort_signal = True
                        return 0, []
                    continue 
                
                else:
                    # 非 200 狀態碼提示
                    print(f"{self.ORANGE}    [104警示] 第 {page} 頁回應碼: {r.status_code}{self.RESET}")
                    retries -= 1
                    self.smart_sleep(3)

            except Exception as e:
                # 連線錯誤提示
                print(f"{self.ORANGE}    [錯誤] 第 {page} 頁連線失敗: {e}{self.RESET}")
                retries -= 1
                self.smart_sleep(3)
        return 0, []

    def search(self, keyword, max_num=10, filter_params=None, sort_type='符合度', is_sort_asc=False):
        self.abort_signal = False 
        self.is_blocked = False 
        
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

        first_total, first_page_jobs = self._fetch_page(1, url, params, headers)
        
        if self.is_blocked:
            print(f"{self.ORANGE}    [104] 首頁即遭封鎖，停止搜尋。{self.RESET}")
            return 0, []
            
        if not first_page_jobs:
            print(f"{self.ORANGE}    [104] 找不到任何資料{self.RESET}")
            return 0, []

        all_jobs.extend(first_page_jobs)
        print(f"{self.ORANGE}    [104] 104 官方顯示總數: {first_total} 筆{self.RESET}")

        real_target_num = min(max_num, first_total)
        pages_needed = math.ceil(real_target_num / 20)
        
        # [Log 還原] 頁數校正提示
        if pages_needed > 1:
            print(f"{self.ORANGE}    [104] 校正後預計抓取: {real_target_num} 筆 (需再抓 {pages_needed - 1} 頁){self.RESET}")
            
            with ThreadPoolExecutor(max_workers=12) as executor:
                future_to_page = {executor.submit(self._fetch_page, page, url, params, headers): page for page in range(2, pages_needed + 1)}
                
                for i, future in enumerate(as_completed(future_to_page)):
                    if self.abort_signal:
                        break
                    
                    # [Log 還原] 資料達標提示
                    if len(all_jobs) >= max_num:
                        print(f"{self.ORANGE}[104] 資料量已達標 ({len(all_jobs)} / {max_num})，提早停止搜尋。{self.RESET}")
                        self.abort_signal = True 
                        break
                    
                    try:
                        _, jobs = future.result()
                        if jobs: 
                            all_jobs.extend(jobs)
                            # 進度提示 (每 50 頁顯示一次，可自行調整)
                            if (i+1) % 50 == 0: 
                                print(f"{self.ORANGE}    [104] 已處理 {i+1} 頁... (目前 {len(all_jobs)} 筆){self.RESET}")
                    except: pass
        
        # 結尾總結
        print(f"{self.ORANGE}" + "-" * 30 + f"{self.RESET}")
        if self.is_blocked:
            print(f"{self.ORANGE}[104] 搜尋因 IP 封鎖而提前終止。共成功抓取 {len(all_jobs)} 筆。{self.RESET}")
        else:
            print(f"{self.ORANGE}[104] 搜尋完成。共成功抓取 {len(all_jobs[:max_num])} 筆。{self.RESET}")
        print(f"{self.ORANGE}" + "-" * 30 + f"{self.RESET}")

        return first_total, all_jobs[:max_num]

    def search_job_transform(self, job_data):
        # --- 保留新版的 Transform 邏輯 (包含 s10 對照表) ---
        links = job_data.get('link', {})
        job_url = f"{links.get('job', '')}" if links.get('job') else ''
        
        s10_map = {
            '10': "面議",
            '20': "論件計酬",
            '30': "時薪",
            '40': "日薪",
            '50': "月薪",
            '60': "年薪",
            '70': "部分工時(月薪)"
        }
        
        s_code = str(job_data.get('s10', ''))
        s_type_str = s10_map.get(s_code, '')

        salary_str = job_data.get('salaryDesc', '')

        # 若代碼是 10，直接顯示面議
        if s_code == '10':
            salary_str = "面議"
        else:
            # 若無描述，組裝數字
            if not salary_str or salary_str == '待遇面議':
                high = int(job_data.get('salaryHigh', 0))
                low = int(job_data.get('salaryLow', 0))
                if low > 0 or high > 0:
                    if low > 0 and high > 0 and high < 9999999:
                        salary_str = f"{low} - {high}"
                    elif low > 0:
                        salary_str = f"{low} 以上"
                    else:
                        salary_str = "面議"
                else:
                    salary_str = "面議"

            # 加上前綴 月薪 等
            if s_type_str and s_type_str not in salary_str:
                salary_str = f"{s_type_str} {salary_str}"

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

    def smart_sleep(self, seconds):
        steps = int(seconds * 10) 
        for _ in range(steps):
            if self.abort_signal: return 
            time.sleep(0.1)
        remaining = seconds - (steps * 0.1)
        if remaining > 0 and not self.abort_signal:
            time.sleep(remaining)