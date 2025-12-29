import time
import requests
import math
import re
import threading
import random
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, as_completed
from requests.adapters import HTTPAdapter

class Job1111Spider():
    BLUE = '\033[94m'
    RED = '\033[91m'
    RESET = '\033[0m'

    def __init__(self):
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=3)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.1111.com.tw/search/job',
            'Accept': 'application/json, text/plain, */*'
        })
        
        # 暴力模式需要的設定
        self.REGION_CODES = {
            '台北市': '100100', '新北市': '100200', '基隆市': '100300', '宜蘭縣': '100400',
            '桃園市': '100500', '新竹縣市': '100600', '苗栗縣': '100700', '台中市': '100800',
            '彰化縣': '100900', '南投縣': '101000', '雲林縣': '101100', '嘉義縣市': '101200',
            '台南市': '101300', '高雄市': '101400', '屏東縣': '101500', '台東縣': '101600',
            '花蓮縣': '101700', '澎湖縣': '101800', '金門縣': '101900', '連江縣': '102000',
            '亞洲': '600000', '美洲': '700000', '歐洲': '800000', '大洋洲': '900000', '非洲': '500000'
        }
        self.BIG_CITIES = ['100100', '100200', '100500', '100800', '101300', '101400']
        self.SALARY_TASKS = {
            '日薪': {'st': '2'}, '時薪': {'st': '4'}, '年薪': {'st': '8'},
            '承攬': {'st': '16'}, '部分工時': {'st': '32'}, '論件計酬': {'st': '64'},
            '月薪_3萬下': {'st': '1', 'min': 0, 'max': 30000},
            '月薪_3-4萬': {'st': '1', 'min': 30000, 'max': 40000},
            '月薪_4-5萬': {'st': '1', 'min': 40000, 'max': 50000},
            '月薪_5-6萬': {'st': '1', 'min': 50000, 'max': 60000},
            '月薪_6-8萬': {'st': '1', 'min': 60000, 'max': 80000},
            '月薪_8萬上': {'st': '1', 'min': 80000, 'max': None}
        }

        # 狀態變數
        self.global_jobs = []      
        self.global_seen_ids = set() 
        self.global_lock = threading.Lock() 
        self.abort_signal = False
        self.target_num = 0
        self.duplicate_count = 0

    def _get_districts(self, city_code):
        base = int(city_code)
        districts = []
        for i in range(1, 41): 
            districts.append(str(base + i))
        return districts

    def _fetch_raw(self, page, url, payload):
        """ 通用的 API 請求函式 (含重試機制) """
        p = payload.copy()
        p['page'] = page
        if 'searchUrl' in p:
             p['searchUrl'] = re.sub(r'page=\d+', f'page={page}', p['searchUrl'])
        p['_'] = int(time.time() * 1000)

        # 隨機延遲
        time.sleep(random.uniform(0.5, 1.2))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = self.session.get(url, params=p, timeout=20)
                
                if r.status_code == 200:
                    data = r.json()
                    jobs = []
                    total = 0
                    if 'result' in data:
                        jobs = data['result'].get('hits', [])
                        total = data['result'].get('pagination', {}).get('totalCount', 0)
                    elif 'data' in data:
                        jobs = data.get('data', [])
                        total = data.get('total', len(jobs))
                    return total, jobs
                
                elif r.status_code == 429:
                    print(f"{self.RED}[1111] 429 Too Many Requests (Page {page}). Retrying...{self.RESET}")
                    time.sleep(3 + attempt * 2)
                    continue
                else:
                    print(f"{self.RED}[1111] Error {r.status_code} on Page {page}. Retrying...{self.RESET}")
            
            except Exception as e:
                print(f"{self.RED}[1111] Exception on Page {page}: {e}. Retrying...{self.RESET}")
            
            time.sleep(2)
        
        return 0, []

    # ==========================================
    # 策略 1: 簡單模式 (Simple Paging)
    # ==========================================
    def _strategy_simple_paging(self, keyword, total_count):
        print(f"{self.BLUE}[1111] 進入「簡單翻頁模式」 (總數 {total_count} < 3000){self.RESET}")
        
        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        safe_keyword = quote(keyword)
        
        base_payload = {
            'keyword': keyword,
            'conditionsText': keyword, 
            'sortBy': 'da', 
            'sortOrder': 'desc',
            'isSyncedRecommendJobs': 'false', 
            'fromOffset': 0,
            'searchUrl': f"/search/job?ks={safe_keyword}&col=da&sort=desc&page=1"
        }

        # [關鍵修復] 
        # 計算實際需要的頁數：取「總頁數」與「目標頁數」的最小值
        # 如果 target_num=1，這裡算出來 pages_needed 就會是 1，不會去跑 50 頁
        
        pages_by_total = math.ceil(total_count / 20)
        pages_by_target = math.ceil(self.target_num / 20)
        
        # 最終頁數取三者最小：(總資料頁數, 目標頁數, 150頁上限)
        max_pages = min(pages_by_total, pages_by_target, 150)
        
        if max_pages == 0: max_pages = 1 # 至少抓一頁

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {
                executor.submit(self._fetch_raw, page, url, base_payload): page
                for page in range(1, max_pages + 1)
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    _, jobs = future.result()
                    if jobs:
                        self._add_jobs(jobs, "一般搜尋")
                        print(f"\r{self.BLUE}[1111] 簡單模式: 已收集 {len(self.global_jobs)}/{self.target_num} 筆...{self.RESET}", end="")
                        
                        # 如果已經達標，可以提早結束 (雖然 ThreadPool 不易中斷，但至少停止 print)
                        if len(self.global_jobs) >= self.target_num:
                            break
                except Exception as e:
                    pass

    # ==========================================
    # 策略 2: 暴力切割模式 (Deep Search)
    # ==========================================
    def _create_salary_tasks(self, payload, label):
        tasks = []
        for s_name, s_params in self.SALARY_TASKS.items():
            sub_payload = payload.copy()
            st = s_params.get('st')
            sub_payload['salaryType'] = st
            
            url_append = f"&st={st}"
            if st == '1':
                if s_params.get('min') is not None: 
                    sub_payload['salaryFrom'] = str(s_params['min'])
                    url_append += f"&sa0={s_params['min']}"
                if s_params.get('max') is not None: 
                    sub_payload['salaryTo'] = str(s_params['max'])
                    url_append += f"&sa1={s_params['max']}"
            
            sub_payload['searchUrl'] += url_append
            tasks.append({'type': 'check_split', 'params': {'payload': sub_payload, 'level': 'salary'}, 'label': f"{label}-{s_name}"})
        return tasks

    def _process_deep_task(self, task_type, params, label):
        if self.abort_signal or len(self.global_jobs) >= self.target_num: return []
        # [防爆機制] 如果任務數暴增但資料沒增加，強制停止
        with self.global_lock:
            self.deep_mode_task_count += 1
            # 每執行 500 個任務檢查一次
            if self.deep_mode_task_count % 500 == 0:
                current_jobs = len(self.global_jobs)
                # 如果過去 500 個任務只抓到不到 20 筆資料 -> 判定為 C# 無限迴圈 Bug
                if current_jobs - self.deep_mode_fail_count < 20:
                    print(f"\n{self.RED}[1111] 偵測到無限裂變 (資料未增加)，可能是關鍵字 '{params.get('payload', {}).get('keyword')}' 導致篩選失效。{self.RESET}")
                    print(f"{self.RED}[1111] 強制切換回「簡單模式」嘗試抓取...{self.RESET}")
                    self.abort_signal = True # 停止深度模式
                    return []
                self.deep_mode_fail_count = current_jobs

        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        new_tasks = []
        payload = params.get('payload')

        if task_type == 'fetch_page':
            total, jobs = self._fetch_raw(params.get('page', 1), url, payload)
            self._add_jobs(jobs, label)
            return []

        elif task_type == 'check_split':
            total, jobs = self._fetch_raw(1, url, payload)
            self._add_jobs(jobs, label)
            if len(self.global_jobs) >= self.target_num: return []

            # 拆分條件： > 2000 筆 (且目標不是只抓 1 筆)
            if total > 2000:
                level = params.get('level')
                if level == 'root':
                    for c_name, c_code in self.REGION_CODES.items():
                        sub_payload = payload.copy()
                        sub_payload['city'] = c_code
                        sub_payload['searchUrl'] += f"&city={c_code}"
                        new_tasks.append({'type': 'check_split', 'params': {'payload': sub_payload, 'level': 'region'}, 'label': c_name})
                    return new_tasks
                elif level == 'region':
                    if payload.get('city') in self.BIG_CITIES:
                        for d in self._get_districts(payload.get('city')):
                            p = payload.copy()
                            p['city'] = d
                            p['searchUrl'] = re.sub(r'city=\d+', f'city={d}', p['searchUrl'])
                            new_tasks.append({'type': 'check_split', 'params': {'payload': p, 'level': 'district'}, 'label': f"{label}-{d}"})
                        return new_tasks
                    else:
                        return self._create_salary_tasks(payload, label)
                elif level == 'district':
                    return self._create_salary_tasks(payload, label)

            if total > 0:
                pages = min(math.ceil(total / 20), 100)
                for p in range(2, pages + 1):
                    new_tasks.append({'type': 'fetch_page', 'params': {'payload': payload, 'page': p}, 'label': label})
            return new_tasks
        return []

    def _strategy_recursive_split(self, base_payload):
        print(f"{self.BLUE}[1111] 進入「深度搜索模式」 (總數 > 3000)，啟動自動分區...{self.RESET}")
        executor = ThreadPoolExecutor(max_workers=10)
        futures = set()
        futures.add(executor.submit(self._process_deep_task, 'check_split', {'payload': base_payload, 'level': 'root'}, '全域'))
        
        while futures:
            if len(self.global_jobs) >= self.target_num: 
                self.abort_signal = True
                break
            
            print(f"\r{self.BLUE}[1111] 深度模式: {len(self.global_jobs)}/{self.target_num} | 任務數: {len(futures)} {self.RESET}", end="")
            
            done, not_done = wait(futures, return_when=FIRST_COMPLETED, timeout=1)
            for f in done:
                try:
                    res = f.result()
                    if res:
                        for t in res:
                            if not self.abort_signal:
                                not_done.add(executor.submit(self._process_deep_task, t['type'], t['params'], t['label']))
                except: pass
            futures = not_done
        executor.shutdown(wait=True)

    # ==========================================
    # 共用方法
    # ==========================================
    def _add_jobs(self, jobs, source_label=""):
        if not jobs: return
        with self.global_lock:
            for j in jobs:
                if len(self.global_jobs) >= self.target_num: break
                jid = str(j.get('jobId', ''))
                if jid and jid not in self.global_seen_ids:
                    self.global_seen_ids.add(jid)
                    j['search_range'] = source_label
                    self.global_jobs.append(j)
                else:
                    self.duplicate_count += 1

    def search(self, keyword, max_num=5000):
        self.target_num = max_num
        self.global_jobs = []
        self.global_seen_ids = set()
        self.duplicate_count = 0
        self.abort_signal = False
        
        print(f"{self.BLUE}[1111] 啟動搜尋: {keyword} (目標 {max_num} 筆){self.RESET}")

        url = 'https://www.1111.com.tw/api/v1/search/jobs/'
        safe_keyword = quote(keyword)
        base_payload = {
            'keyword': keyword,
            'conditionsText': keyword, # 補上
            'page': 1, 'sortBy': 'da', 'sortOrder': 'desc',
            'isSyncedRecommendJobs': 'false', 'fromOffset': 0,
            'searchUrl': f"/search/job?ks={safe_keyword}&col=da&sort=desc&page=1"
        }
        
        # 1. 偵查
        total_count, jobs_p1 = self._fetch_raw(1, url, base_payload)
        
        # 2. 如果偵查就有資料，先存起來
        # 這樣如果 max_num=1，這裡存完就直接收工了，不用進入任何策略
        if jobs_p1:
            self._add_jobs(jobs_p1, "偵查")
            
        if len(self.global_jobs) >= max_num:
            print(f"\n{self.BLUE}[1111] 搜尋結束。共取得: {len(self.global_jobs)} 筆 (API顯示總數: {total_count}){self.RESET}")
            return total_count, self.global_jobs

        # 3. 智慧判斷
        # 如果總數小於 3000，用簡單翻頁 (但記得我們要從第 1 頁還是第 2 頁開始? 
        # 為了保險，簡單模式 ThreadPool 會檢查 seen_ids，所以從第 1 頁開始重抓也沒關係，或者我們修改簡單模式從 P2 開始
        # 為了代碼乾淨，這裡讓簡單模式自己去處理 (它有 duplicate check)
        if total_count <= 3000:
            self._strategy_simple_paging(keyword, total_count)
        else:
            self._strategy_recursive_split(base_payload)
            # 如果深度模式因為無限迴圈被 abort，且資料量還很少，我們嘗試用簡單模式補救一下
            if self.abort_signal and len(self.global_jobs) < 1000:
                 self._strategy_simple_paging(keyword, total_count)
            
        print(f"\n{self.BLUE}[1111] 搜尋結束。共取得: {len(self.global_jobs)} 筆 (API顯示總數: {total_count}){self.RESET}")
        return total_count, self.global_jobs

    def search_job_transform(self, job_data):
        job_id = str(job_data.get('jobId', ''))
        job_url = f"https://www.1111.com.tw/job/{job_id}/" if job_id else ""
        location = ""
        wc = job_data.get('workCity')
        if isinstance(wc, list) and len(wc) > 0: location = wc[0].get('name', '')
        elif isinstance(wc, dict): location = wc.get('name', '')
        raw_date = str(job_data.get('updateAt', ''))
        
        return {
            'platform': '1111',
            'search_range': job_data.get('search_range', '一般搜尋'), 
            'update_date': raw_date.split(" ")[0] if raw_date else "",
            'name': job_data.get('title', ''),
            'company_name': job_data.get('companyName', ''),
            'salary': job_data.get('salary', '面議'),
            'job_url': job_url,
            'location': location
        }