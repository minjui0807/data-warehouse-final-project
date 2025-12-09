# job_analysis.py
import matplotlib.pyplot as plt


plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False

def plot_location_pie(df):
    """
    功能: 繪製地區職缺佔比圖
    """
    print("\n正在生成地區佔比圖...")
    
    # 抓取前三個字 (例如 "台北市")
    def get_city(addr):
        if isinstance(addr, str) and len(addr) >= 3:
            return addr[:3]
        return "其他"
        
    city_counts = df['location'].apply(get_city).value_counts()
    
    # 只取前 6 名，剩下的歸類為「其他」
    if len(city_counts) > 6:
        main_cities = city_counts[:6]
        other_count = city_counts[6:].sum()
        main_cities['其他'] = other_count
        city_counts = main_cities

    plt.figure(figsize=(8, 8))
    plt.pie(city_counts, labels=city_counts.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.Pastel1.colors)
    plt.title("職缺地區分佈")
    
    filename = "location_pie.png"
    plt.savefig(filename)
    print(f"圖表已儲存: {filename}")
    plt.show()
        