from job_analysis import run_job_search, run_chart_analysis


if __name__ == "__main__":
    while True:
        print("\n==================================")
        print("   職缺分析器   ")
        print("==================================")
        print("1. 職缺查詢(104 + 1111整合搜尋)")
        print("2. 程式語言統計圖表")
        print("q. 離開程式")
        
        choice = input("請輸入選項: ")
        
        if choice == '1':
            run_job_search()
        elif choice == '2':
            run_chart_analysis()
        elif choice.lower() == 'q':
            print("退出成功!")
            break
        else:
            print("輸入錯誤，請重試。")