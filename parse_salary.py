# job_analysis.py
import re

def parse_salary(salary_str):
        """將薪資字串 (如 '30000-50000') 轉換為平均數值"""
        salary_str = str(salary_str).replace(',', '') # 移除逗號
        
        if '面議' in salary_str:
            return 0
            
        # 抓取所有數字
        nums = re.findall(r'(\d+)', salary_str)
        if not nums:
            return 0
            
        # 轉成整數並計算平均
        nums = [int(n) for n in nums]
        avg_salary = sum(nums) / len(nums)
        
        # 排除明顯異常的數字 (例如時薪 180 或年薪 200萬，這裡簡單過濾月薪範圍)
        if avg_salary < 1000: # 可能是時薪，簡單乘以 160 小時估算
            return avg_salary * 160
        if avg_salary > 300000: # 可能是年薪，簡單除以 13 個月估算
            return avg_salary / 13
            
        return avg_salary