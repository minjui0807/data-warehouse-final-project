#已廢棄但刪掉可惜 不要上傳!
import time
import random
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

class JobSpiderTimed():
    def __init__(self):
        print("啟動爬蟲...")
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # 若需背景執行請取消註解
        
        self.driver = uc.Chrome(options=options)
        self.driver.set_window_size(1200, 900)

    def close(self):
        print("關閉瀏覽器...")
        self.driver.quit()

    # ================= 104 搜尋邏輯 =================
    def search_104(self, keyword, max_num=10):
        print(f"\n=== [104] 搜尋: {keyword} | 目標: {max_num} 筆 ===")
        jobs = []
        page = 1
        
        while len(jobs) < max_num:
            url = f"https://www.104.com.tw/jobs/search/?keyword={keyword}&page={page}&mode=s&jobsource=index_s"
            
            try:
                self.driver.get(url)
                
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-gtm-joblist="職缺-職缺名稱"]'))
                    )
                except:
                    break

                # 滾動
                for _ in range(3):
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(0.5)

                # 解析
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                containers = soup.select('div.info-container')
                
                if not containers: break

                for container in containers:
                    if len(jobs) >= max_num: break
                    try:
                        title_tag = container.select_one('[data-gtm-joblist="職缺-職缺名稱"]')
                        if not title_tag: continue
                        name = title_tag.get_text(strip=True)
                        href = title_tag.get('href')
                        if href and not href.startswith('http'): href = 'https:' + href

                        company_tag = container.select_one('[data-gtm-joblist="職缺-公司名稱"]')
                        company = company_tag.get_text(strip=True) if company_tag else "未知"
                        
                        salary_tag = container.select_one('[data-gtm-joblist^="職缺-薪資"]')
                        salary = salary_tag.get_text(strip=True) if salary_tag else "面議"
                        
                        location_tag = container.select_one('[data-gtm-joblist^="職缺-地區"]')
                        location = location_tag.get_text(strip=True) if location_tag else "未知"

                        jobs.append({
                            "platform": "104",
                            "name": name,
                            "company": company,
                            "salary": salary,
                            "location": location,
                            "url": href
                        })
                    except: continue
                
                print(f"   [104] 第 {page} 頁完成，目前累積 {len(jobs)} 筆")
                page += 1
                time.sleep(1) # 翻頁稍微休息

            except Exception:
                break

        return jobs[:max_num]

    # ================= 1111 搜尋邏輯 =================
    def search_1111(self, keyword, max_num=10):
        print(f"\n=== [1111] 搜尋: {keyword} | 目標: {max_num} 筆 ===")
        jobs = []
        page = 1
        
        while len(jobs) < max_num:
            url = f"https://www.1111.com.tw/search/job?ks={keyword}&page={page}"
            
            try:
                self.driver.get(url)
                
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.job-card'))
                    )
                except:
                    break

                for _ in range(3):
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(0.6)

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                cards = soup.select('div.job-card')
                
                if not cards: break

                for card in cards:
                    if len(jobs) >= max_num: break
                    try:
                        title_tag = card.select_one("a[href^='/job/']")
                        if not title_tag: continue
                        name = title_tag.get('title') or title_tag.get_text(strip=True)
                        href = title_tag.get('href')
                        if href and not href.startswith('http'): href = "https://www.1111.com.tw" + href

                        company_tag = card.select_one("a[href^='/corp/']")
                        company = company_tag.get('title') if company_tag else (company_tag.get_text(strip=True) if company_tag else "未知")

                        details = card.select(".job-card-condition__text")
                        location = details[0].get_text(strip=True) if len(details) >= 1 else "未知"
                        salary = details[1].get_text(strip=True) if len(details) >= 2 else "面議"

                        jobs.append({
                            "platform": "1111",
                            "name": name,
                            "company": company,
                            "salary": salary,
                            "location": location,
                            "url": href
                        })
                    except: continue
                
                print(f"   [1111] 第 {page} 頁完成，目前累積 {len(jobs)} 筆")
                page += 1
                time.sleep(1)

            except Exception:
                break

        return jobs[:max_num]

# ================= 主程式執行與計時區 =================
if __name__ == "__main__":
    spider = JobSpiderTimed()
    
    # 設定參數
    search_keyword = "Python"
    target_count = 30 # 每個網站抓幾筆
    
    # 總計時器開始
    program_start = time.time()
    
    try:
        # --- 1. 測量 104 時間 ---
        start_104 = time.time()
        results_104 = spider.search_104(search_keyword, max_num=target_count)
        end_104 = time.time()
        time_104 = end_104 - start_104

        # --- 2. 測量 1111 時間 ---
        start_1111 = time.time()
        results_1111 = spider.search_1111(search_keyword, max_num=target_count)
        end_1111 = time.time()
        time_1111 = end_1111 - start_1111

        # 總計時器結束
        program_end = time.time()
        total_time = program_end - program_start
        
        all_jobs = results_104 + results_1111
        if all_jobs:
            df = pd.DataFrame(all_jobs)
            filename = f"combined_jobs_{search_keyword}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n原始資料已儲存: {filename}")

        total_jobs = len(all_jobs)

        # --- 3. 輸出漂亮的報表 ---
        print("\n" + "="*50)
        print(f"效能分析報告")
        print("="*50)
        print(f"搜尋關鍵字: {search_keyword}")
        print(f"總資料筆數: {total_jobs} 筆")
        print("-" * 30)
        
        # 104 分析
        print(f"[104] 耗時: {time_104:.2f} 秒")
        if results_104:
            print(f"平均每筆: {time_104 / len(results_104):.2f} 秒)")
        else:
            print("(未抓到資料)")

        # 1111 分析
        print(f"[1111] 耗時: {time_1111:.2f} 秒")
        if results_1111:
            print(f"(平均每筆: {time_1111 / len(results_1111):.2f} 秒)")
        else:
            print("(未抓到資料)")

        print("-" * 30)
        print(f"程式總執行時間: {total_time:.2f} 秒")
        print("="*50)

    finally:
        spider.close()