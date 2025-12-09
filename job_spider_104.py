import time
import random
import requests
from bs4 import BeautifulSoup
from lxml import etree

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

    def search_html(self, keyword, max_num=10):
        """HTML 爬蟲方式搜尋職缺 (使用 BeautifulSoup + XPath)"""
        jobs = []
        total_count = 0
        base_url = 'https://www.104.com.tw/jobs/search/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
            'Referer': 'https://www.104.com.tw/jobs/search/',
        }
        
        page = 1
        while len(jobs) < max_num:
            try:
                params = {
                    'ro': '0',
                    'kwop': '7',
                    'keyword': keyword,
                    'page': page,
                    'asc': '0'
                }
                
                r = requests.get(base_url, params=params, headers=headers, timeout=10)
                r.encoding = 'utf-8'
                
                if r.status_code != 200:
                    break
                
                # 方法 1: 使用 BeautifulSoup 解析
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # 方法 2: 使用 XPath 定位 (透過 lxml)
                html_tree = etree.HTML(r.text)
                
                # 使用 XPath 提取職缺清單
                job_items_xpath = html_tree.xpath('//div[@data-jobid]')
                
                if not job_items_xpath:
                    # 備用: 使用 BeautifulSoup 定位
                    job_items = soup.find_all('div', {'data-jobid': True})
                else:
                    job_items = job_items_xpath
                
                if not job_items:
                    break
                
                for item in job_items:
                    if len(jobs) >= max_num:
                        break
                    
                    try:
                        # 使用 XPath 定位各欄位
                        if isinstance(item, etree._Element):
                            # XPath 方式
                            job_id = item.xpath('.//@data-jobid')
                            job_name = item.xpath('.//h2[@class="js-job-link"]//a/text()')
                            company = item.xpath('.//h3[@class="js-company-link"]//a/text()')
                            salary = item.xpath('.//div[@class="job__item__info__salary"]/text()')
                            location = item.xpath('.//div[@class="job__item__info__location"]/text()')
                            job_url = item.xpath('.//h2[@class="js-job-link"]//a/@href')
                            
                            job_obj = {
                                'platform': '104',
                                'name': job_name[0].strip() if job_name else '未知職位',
                                'company_name': company[0].strip() if company else '未知公司',
                                'salary': salary[0].strip() if salary else '面議',
                                'location': location[0].strip() if location else '未知地點',
                                'job_url': f"https://www.104.com.tw{job_url[0]}" if job_url else '',
                            }
                        else:
                            # BeautifulSoup 方式
                            job_id = item.get('data-jobid', '')
                            job_name_elem = item.find('h2', class_='js-job-link')
                            job_name = job_name_elem.get_text(strip=True) if job_name_elem else '未知職位'
                            
                            company_elem = item.find('h3', class_='js-company-link')
                            company = company_elem.get_text(strip=True) if company_elem else '未知公司'
                            
                            salary_elem = item.find('div', class_='job__item__info__salary')
                            salary = salary_elem.get_text(strip=True) if salary_elem else '面議'
                            
                            location_elem = item.find('div', class_='job__item__info__location')
                            location = location_elem.get_text(strip=True) if location_elem else '未知地點'
                            
                            job_url_elem = item.find('h2', class_='js-job-link')
                            job_url = job_url_elem.find('a').get('href', '') if job_url_elem else ''
                            
                            job_obj = {
                                'platform': '104',
                                'name': job_name,
                                'company_name': company,
                                'salary': salary,
                                'location': location,
                                'job_url': f"https://www.104.com.tw{job_url}" if job_url else '',
                            }
                        
                        jobs.append(job_obj)
                    
                    except Exception as e:
                        print(f"[104] 單筆解析錯誤: {e}")
                        continue
                
                if len(jobs) < max_num:
                    page += 1
                    time.sleep(random.uniform(0.5, 1.5))
                else:
                    break
            
            except Exception as e:
                print(f"[104] HTML 爬蟲錯誤: {e}")
                break
        
        return len(jobs), jobs[:max_num]
