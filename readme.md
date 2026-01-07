# Data Warehouse Final Project

本專案為資料倉儲期末專題，主要功能是**爬取台灣求職網站（104 與 1111）的職缺資料**，並透過 **Flask Web 介面**呈現結果，作為資料蒐集與分析展示用途。

---

## 專案功能說明

* 爬蟲模組

  * `job_spider_104.py`：爬取 104 人力銀行職缺資料
  * `job_spider_1111.py`：爬取 1111 人力銀行職缺資料

* Web 介面

  * 使用 Flask 建立簡易 Web Server
  * 透過瀏覽器顯示爬取後的資料結果

* ▶主程式

  * `main.py`：專案啟動入口，會自動啟動 Web Server 並開啟瀏覽器

---

## 專案目錄結構

```
data-warehouse-final-project-main/
│
├── main.py                  # 專案主程式（執行入口）
├── web_server.py            # Flask Web Server
├── job_spider_104.py        # 104 人力銀行爬蟲
├── job_spider_1111.py       # 1111 人力銀行爬蟲
├── requirements.txt         # 專案所需套件
│
├── templates/               # HTML 樣板
│   └── index.html
│
├── static/                  # 前端靜態資源
│   ├── style.css
│   └── script.js
│
└── .gitignore
```

---

## 環境需求

* Python 3.8（含）以上
* 作業系統：Windows / macOS / Linux 皆可

---

## 套件安裝方式

建議使用 **虛擬環境（venv）** 來執行專案。

### 1️建立並啟動虛擬環境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2️安裝必要套件

```bash
pip install -r requirements.txt
```

---

## ▶專案執行方式

本專案**只需要執行 `main.py` 即可**，不需額外指令。

```bash
python main.py
```

執行後流程如下：

1. 啟動 Flask Web Server
2. 自動開啟預設瀏覽器
3. 瀏覽網址：[http://localhost:5000](http://localhost:5000)

若瀏覽器未自動開啟，可手動輸入上述網址。

---

## 測試方式說明

* 確認終端機顯示「Web 伺服器啟動成功」相關訊息
* 使用瀏覽器開啟 `http://localhost:5000`
* 檢查頁面是否正常顯示職缺資料
* 若資料成功顯示，代表：

  * 爬蟲模組正常
  * Web Server 運作正常

---

## 補充說明

* 本專案為課程學習用途，爬取資料僅供學術研究與展示
* 若網站結構變更，爬蟲程式可能需調整

---

