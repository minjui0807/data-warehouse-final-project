import time
import requests
import math
import re
import threading
import random
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from requests.adapters import HTTPAdapter

class Job1111Spider():
    BLUE = '\033[94m'
    RESET = '\033[0m'

    def __init__(self):
        self.abort_signal = False
        self.session = requests.Session()
        # 維持連線池設定
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=3)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.1111.com.tw/search/job',
            'Accept': 'application/json, text/plain, */*'
        })
        
        self.REGION_CODES = {
            '台北市': '100100', '新北市': '100200', '基隆市': '100300', '宜蘭縣': '100400',
            '桃園市': '100500', '新竹縣市': '100600', '苗栗縣': '100700', '台中市': '100800',
            '彰化縣': '100900', '南投縣': '101000', '雲林縣': '101100', '嘉義縣市': '101200',
            '台南市': '101300', '高雄市': '101400', '屏東縣': '101500', '台東縣': '101600',
            '花蓮縣': '101700', '澎湖縣': '101800', '金門縣': '101900', '連江縣': '102000',
            '亞洲': '600000', '美洲': '700000', '歐洲': '800000', '大洋洲': '900000', '非洲': '500000'
        }

        self.SALARY_TASKS = {
            '日薪': {'st': '2'}, '時薪': {'st': '4'}, '年薪': {'st': '8'},
            '承攬': {'st': '16'}, '部分工時': {'st': '32'}, '論件計酬': {'st': '64'},
            '月薪_3萬下': {'st': '1', 'min': 0, 'max': 30000},
            '月薪_3-4萬': {'st': '1', 'min': 30000, 'max': 40000},
            '月薪_4-5萬': {'st': '1', 'min': 40000, 'max': 50000},
            '月薪_5-6萬': {'st': '1', 'min': 50000, 'max': 60000},
            '月薪_6-8萬': {'st': '1', 'min': 60000, 'max': 80000},
            '月薪_8萬上': {'st': '1', 'min': 80000, 'max': None},
        }
        
        self.global_jobs = []      
        self.global_seen_ids = set() 
        self.global_lock = threading.Lock() 
        self.target_num = 0       
        self.api_call_count = 0  # 監控 API 呼叫次數
        self.duplicate_count = 0 # 監控重複次數
        self.last_success_time = 0 # 監控最後一次成功抓到資料的時間

        # 新增監控變數
        self.monitor_timer = 0
        self.monitor_last_count = 0

    def _add_jobs(self, jobs, source_label=""):
        if not jobs: return
        
        with self.global_lock:
            if len(self.global_jobs) >= self.target_num: return

            added_count = 0
            for j in jobs:
                jid = str(j.get('jobId', ''))
                if jid:
                    if jid not in self.global_seen_ids:
                        self.global_seen_ids.add(jid)
                        j['search_range'] = source_label
                        self.global_jobs.append(j)
                        added_count += 1
                        self.last_success_time = time.time() # 更新成功時間
                    else:
                        self.duplicate_count += 1 # 記錄重複
            
    def _fetch_raw(self, page, url, payload):
        p = payload.copy()
        p['page'] = page
        p['_'] = int(time.time() * 1000)
        
        # 模擬人類行為：隨機微幅延遲 0.2 ~ 0.8 秒
        time.sleep(random.uniform(0.2, 0.8))

        if 'searchUrl' in p:
            if 'page=' in p['searchUrl']:
                p['searchUrl'] = re.sub(r'page=\d+', f'page={page}', p['searchUrl'])
            else:
                p['searchUrl'] += f"&page={page}"

        try:
            # 增加一些常見的 Header 偽裝
            r = self.session.get(url, params=p, timeout=15)
            
            with self.global_lock:
                self.api_call_count += 1
                
            if r.status_code == 200:
                data = r.json()
                # 檢查 1111 是否回傳了「空結果」但狀態碼是 200 (常見的軟封鎖)
                if not data.get('result') and not data.get('data'):
                    return 0, []
                
                # ... 原本的 parsing 邏輯 ...
                jobs = []
                total = 0
                if 'result' in data:
                    jobs = data['result'].get('hits', [])
                    total = data['result'].get('pagination', {}).get('totalCount', 0)
                elif 'data' in data:
                    jobs = data.get('data', [])
                    total = data.get('pagination', {}).get('totalCount', 0) if 'pagination' in data else data.get('total', len(jobs))
                return total, jobs
            
            elif r.status_code == 429: # Too Many Requests
                print(f"\n{self.BLUE}[警告] 觸發頻率限制，暫停 5 秒...{self.RESET}")
                time.sleep(5)
            elif r.status_code == 403:
                print(f"\n{self.BLUE}[錯誤] IP 可能被封鎖 (403 Forbidden){self.RESET}")
                self.abort_signal = True 
        except Exception as e:
            pass 
        return 0, []

    def _process_task(self, task_type, params, label):
        if self.abort_signal: return []
        if len(self.global_jobs) >= self.target_num: return []

        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        new_tasks = []

        if task_type == 'fetch_page':
            page = params.get('page', 1)
            payload = params.get('payload')
            total, jobs = self._fetch_raw(page, url, payload)
            self._add_jobs(jobs, label)
            return []

        elif task_type == 'check_split':
            payload = params.get('payload')
            current_level = params.get('level', 'root') 
            
            total, jobs = self._fetch_raw(1, url, payload)
            self._add_jobs(jobs, label)

            # 只有當總數 > 2000 且 還有下一層時才拆分
            if total > 2000:
                if current_level == 'root':
                    for c_name, c_code in self.REGION_CODES.items():
                        sub_payload = payload.copy()
                        sub_payload['city'] = c_code
                        sub_payload['searchUrl'] += f"&city={c_code}"
                        new_tasks.append({
                            'type': 'check_split',
                            'params': {'payload': sub_payload, 'level': 'region'},
                            'label': c_name
                        })
                    return new_tasks

                elif current_level == 'region':
                    for s_name, s_params in self.SALARY_TASKS.items():
                        sub_payload = payload.copy()
                        st = s_params.get('st')
                        sub_payload['salaryType'] = st
                        sub_payload['searchUrl'] += f"&st={st}"
                        
                        if st == '1':
                            sub_payload['isExcludeNegotiable'] = 'true'
                            if s_params.get('min') is not None:
                                sub_payload['salaryFrom'] = str(s_params['min'])
                                sub_payload['searchUrl'] += f"&sa0={s_params['min']}"
                            if s_params.get('max') is not None:
                                sub_payload['salaryTo'] = str(s_params['max'])
                                sub_payload['searchUrl'] += f"&sa1={s_params['max']}"

                        new_tasks.append({
                            'type': 'check_split',
                            'params': {'payload': sub_payload, 'level': 'salary'},
                            'label': f"{label}-{s_name}"
                        })
                    return new_tasks
            
            # 翻頁邏輯
            pages_needed = math.ceil(total / 20)
            safe_limit = 150 
            final_pages = min(pages_needed, safe_limit)

            if final_pages > 1:
                for p in range(2, final_pages + 1):
                    new_tasks.append({
                        'type': 'fetch_page',
                        'params': {'payload': payload, 'page': p},
                        'label': label
                    })
            return new_tasks

        return []

    def search(self, keyword, max_num=5000):
        self.abort_signal = False
        self.target_num = max_num
        self.global_jobs = []
        self.global_seen_ids = set()
        self.api_call_count = 0
        self.duplicate_count = 0
        self.last_success_time = time.time()

        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        
        # 初始化速率監控器
        self.monitor_timer = time.time()
        self.monitor_last_count = 0
        
        safe_keyword = quote(keyword)
        print(f"{self.BLUE}[1111] 啟動搜尋: {keyword} (目標 {max_num} 筆){self.RESET}")

        base_payload = {
            'keyword': keyword, 'page': 1, 'sortBy': 'da', 'sortOrder': 'desc',
            'isSyncedRecommendJobs': 'false', 'fromOffset': 0,
            'searchUrl': f"/search/job?ks={safe_keyword}&col=da&sort=desc"
        }

        total_count, jobs_p1 = self._fetch_raw(1, url, base_payload)
        if self.target_num <= 1 or len(self.global_jobs) >= self.target_num:
            return total_count, self.global_jobs

        # 稍微降速到 30 workers 以求穩定
        executor = ThreadPoolExecutor(max_workers=10)
        futures = set()

        f = executor.submit(self._process_task, 'check_split', {'payload': base_payload, 'level': 'root'}, '全域')
        futures.add(f)

        last_print_time = time.time()

        while futures:
            current_count = len(self.global_jobs)
            current_time = time.time()
            
            # 1. 達標檢查
            if current_count >= self.target_num:
                self.abort_signal = True
                break

            # ==========================================
            # 2. 新增：10秒增加少於10筆 就停止 (智慧停損)
            # ==========================================
            # 修改 search 內的監控邏輯
            # 將 monitor_timer 的判定放寬
            if current_time - self.monitor_timer > 20: # 從 10 秒放寬到 20 秒
                growth = current_count - self.monitor_last_count
                # 只有在完全沒有新資料 (growth == 0) 且請求數已經很大時才考慮停止
                if growth == 0 and self.api_call_count > 100:
                    print(f"\n{self.BLUE}[1111] 資料已達極限，停止抓取。{self.RESET}")
                    self.abort_signal = True
                    break
                            
                # 重置計時器與計數器
                self.monitor_timer = current_time
                self.monitor_last_count = current_count
            # ==========================================

            # 3. 定時 Log (心跳包)
            if current_time - last_print_time > 3:
                percent = (current_count / self.target_num) * 100
                print(f"\r{self.BLUE}[1111] 收集: {current_count}/{self.target_num} ({percent:.1f}%) | "
                      f"重複: {self.duplicate_count} | 請求: {self.api_call_count} | "
                      f"剩餘: {len(futures)} {self.RESET}", end="")
                last_print_time = current_time

            # 等待任務
            done, not_done = wait(futures, return_when=FIRST_COMPLETED, timeout=1)
            
            if not done and not not_done:
                break

            for f in done:
                try:
                    new_task_defs = f.result()
                    if new_task_defs:
                        for t in new_task_defs:
                            if not self.abort_signal and len(self.global_jobs) < self.target_num:
                                new_f = executor.submit(self._process_task, t['type'], t['params'], t['label'])
                                not_done.add(new_f)
                except Exception:
                    pass
            
            futures = not_done
            if not futures: break

        executor.shutdown(wait=True)
        print() 

        # 強制截斷
        final_jobs = self.global_jobs[:max_num]
        final_count = len(final_jobs)

        print("-" * 30)
        print(f"{self.BLUE}[1111] 搜尋結束。共取得: {final_count} 筆 (過濾了 {self.duplicate_count} 筆重複){self.RESET}")
        print("-" * 30)

        return final_count, final_jobs

    def search_job_transform(self, job_data):
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
        
        job = {
            'platform': '1111',
            'search_range': job_data.get('search_range', '一般搜尋'), 
            'update_date': update_date,
            'name': job_data.get('title', ''),
            'company_name': job_data.get('companyName', ''),
            'salary': salary_str,
            'job_url': job_url,
            'location': location
        }
        return job