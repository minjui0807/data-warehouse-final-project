// static/script.js

// --- 全域變數 ---
let currentJobsData = [];
let currentKeyword = '';

// ==========================================
// 1. 市場分析功能 (單一關鍵字搜尋)
// ==========================================

async function startAnalysis() {
    const keyword = document.getElementById('keyword').value;
    const maxNum = document.getElementById('max_num').value;
    const btn = document.getElementById('btn-search');
    const loader = document.getElementById('loader');
    const resultsArea = document.getElementById('results-area');

    // 1. 新增：抓取我們剛剛在 HTML 加的訊息框元素
    const statusMsg = document.getElementById('status-msg'); // <--- 新增這行

    if(!keyword) {
        alert("請輸入關鍵字");
        return;
    }

    // UI 鎖定
    btn.disabled = true;
    btn.innerText = "正在分析數據...";
    loader.classList.add('active');
    resultsArea.classList.remove('visible'); 
    currentKeyword = keyword;

    // 2. 新增：讓訊息框顯示出來 (CSS 動畫就會自動開始跑)
    if (statusMsg) statusMsg.style.display = 'block'; // <--- 新增這行

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: keyword, max_num: maxNum })
        });
        const data = await response.json();

        if (data.status === 'success') {
            currentJobsData = data.jobs; 
            updateUI(data); 
            resultsArea.classList.add('visible'); 
        } else {
            alert('搜尋失敗: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('系統錯誤，請檢查後端是否執行中');
    } finally {
        // UI 解鎖
        btn.disabled = false;
        btn.innerText = "開始分析職缺";
        loader.classList.remove('active');

        // 3. 新增：搜尋結束後，把訊息框隱藏起來
        if (statusMsg) statusMsg.style.display = 'none'; // <--- 新增這行
    }
}

function updateUI(data) {
    // 基本統計數據
    document.getElementById('stat-total').innerText = data.stats.total;
    // 薪資取整數並加逗號
    document.getElementById('stat-salary').innerText = Math.round(data.stats.avg_salary).toLocaleString();
    
    // --- [修正點] 這裡原本寫 stats.count_104 是錯的，應改為 data.stats ---
    document.getElementById('count_104').innerText = data.stats.count_104;
    document.getElementById('count_1111').innerText = data.stats.count_1111;

    // 更新圖表 (如果有回傳圖表才更新)
    if (data.charts.salary_dist) {
        document.getElementById('chart-salary').innerHTML = `<img src="data:image/png;base64,${data.charts.salary_dist}" style="width:100%; height:auto;" />`;
    }
    if (data.charts.location_pie) {
        document.getElementById('chart-location').innerHTML = `<img src="data:image/png;base64,${data.charts.location_pie}" style="width:100%; height:auto;" />`;
    }

    // 初始化篩選器並顯示列表
    initCityFilter(data.jobs);
    applyFilters();
}

// ==========================================
// 2. 自訂職缺比較功能 (多關鍵字)
// ==========================================

// 在畫面上新增一個關鍵字輸入卡片
function addKeywordCard(value = '') {
    const container = document.getElementById('keywords-container');
    if (!container) return; // 如果在首頁，可能沒有這個元素

    const div = document.createElement('div');
    div.className = 'keyword-card';
    
    // 輸入框
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'keyword-input';
    input.placeholder = '職缺名稱 (例如: PHP)';
    input.value = value;
    
    // 按 Enter 鍵自動觸發搜尋
    input.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            compareJobs();
        }
    });
    
    // 刪除按鈕
    const btnDel = document.createElement('button');
    btnDel.className = 'btn-remove';
    btnDel.innerHTML = '&times;';
    btnDel.onclick = function() {
        container.removeChild(div);
    };
    
    div.appendChild(input);
    div.appendChild(btnDel);
    container.appendChild(div);
    
    // 新增後自動 focus
    if (value === '') {
        input.focus();
    }
}

// 執行比較分析
async function compareJobs() {
    const btn = document.getElementById('btn-stats');
    const loader = document.getElementById('loader');
    const resultsArea = document.getElementById('results-area');
    const textStatsArea = document.getElementById('text-stats-area');
    
    // 蒐集輸入
    const inputs = document.querySelectorAll('.keyword-input');
    let keywords = [];
    let emptyElements = []; 

    inputs.forEach(input => {
        const val = input.value.trim();
        if (val) {
            keywords.push(val);
        } else {
            emptyElements.push(input.parentElement);
        }
    });

    // 移除空輸入框
    emptyElements.forEach(card => card.remove());

    if (keywords.length === 0) {
        alert("請至少輸入一個職缺關鍵字");
        addKeywordCard(); 
        return;
    }

    // UI 鎖定
    btn.disabled = true;
    btn.innerText = "統計中...";
    loader.classList.add('active');
    resultsArea.classList.remove('visible');

    try {
        const response = await fetch('/api/compare_jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords: keywords })
        });
        const data = await response.json();

        if (data.status === 'success') {
            // 顯示圖表
            document.getElementById('chart-stats').innerHTML = `<img src="data:image/png;base64,${data.chart}" style="width:100%;" />`;
            
            // 顯示文字列表
            const listContainer = document.getElementById('stats-list');
            listContainer.innerHTML = '';
            
            for (const [kw, count] of Object.entries(data.data)) {
                listContainer.innerHTML += `
                    <div style="background:#333; padding:8px 16px; border-radius:4px; border:1px solid #555; display:flex; align-items:center; justify-content:space-between; min-width: 150px;">
                        <span style="color:var(--gold); font-weight:bold; margin-right:10px;">${kw}</span> 
                        <span style="color:white; font-family:'Playfair Display'; font-size:18px;">${count.toLocaleString()}</span>
                    </div>
                `;
            }
            textStatsArea.style.display = 'block';
            resultsArea.classList.add('visible');
        } else {
            alert('統計失敗: ' + data.message);
        }

    } catch (error) {
        console.error('Error:', error);
        alert('系統發生錯誤');
    } finally {
        btn.disabled = false;
        btn.innerText = "開始統計分析";
        loader.classList.remove('active');
    }
}

// ==========================================
// 3. 共用工具函式
// ==========================================

function initCityFilter(jobs) {
    const citySelect = document.getElementById('filter-city');
    if(!citySelect) return; // 如果頁面上沒有這個篩選器則跳過

    citySelect.innerHTML = '<option value="all">所有縣市</option>';
    const cities = new Set();
    
    jobs.forEach(job => {
        if (job.location && job.location.length >= 3) {
            cities.add(job.location.substring(0, 3));
        }
    });
    
    Array.from(cities).sort().forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.innerText = city;
        citySelect.appendChild(option);
    });
}

function parseSalary(salaryStr) {
    if (!salaryStr) return 0;
    const str = salaryStr.toString().replace(/,/g, '');
    if (str.indexOf('面議') !== -1) return 0;
    
    // 取出所有數字
    const nums = str.match(/(\d+)/g);
    if (!nums) return 0;
    
    let sum = 0;
    nums.forEach(n => sum += parseInt(n));
    return sum / nums.length; // 取區間平均
}

function applyFilters() {
    const citySelect = document.getElementById('filter-city');
    const listContainer = document.getElementById('jobs-container');
    
    // 如果頁面沒有職缺列表容器，就不執行篩選邏輯
    if(!citySelect || !listContainer) return; 

    const cityFilter = citySelect.value;
    // 檢查 checkbox 是否存在，若不存在預設為 true (避免報錯)
    const cb104 = document.getElementById('cb-104');
    const cb1111 = document.getElementById('cb-1111');
    const show104 = cb104 ? cb104.checked : true;
    const show1111 = cb1111 ? cb1111.checked : true;
    const sortBy = document.getElementById('sort-by').value;

    let filtered = currentJobsData.filter(job => {
        if (job.platform === '104' && !show104) return false;
        if (job.platform === '1111' && !show1111) return false;
        if (cityFilter !== 'all') {
            if (!job.location.startsWith(cityFilter)) return false;
        }
        return true;
    });

    // 排序邏輯
    filtered.sort((a, b) => {
        if (sortBy === 'salary_desc') return parseSalary(b.salary) - parseSalary(a.salary);
        if (sortBy === 'salary_asc') return parseSalary(a.salary) - parseSalary(b.salary);
        if (sortBy === 'date_desc') return (b.update_date || '').localeCompare(a.update_date || '');
        if (sortBy === 'company') return a.company_name.localeCompare(b.company_name, 'zh-Hant');
        return 0;
    });

    renderJobsList(filtered);
}

function renderJobsList(jobs) {
    const container = document.getElementById('jobs-container');
    if(!container) return;

    container.innerHTML = ''; 

    if (jobs.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;">沒有符合篩選條件的職缺</div>';
        return;
    }

    jobs.forEach(job => {
        const tagClass = job.platform === '104' ? 'tag-104' : 'tag-1111';
        // 安全處理 null 值
        const dateStr = job.update_date || '近期';
        const salaryStr = job.salary || '面議';
        const locStr = job.location || '台灣';

        const cardHTML = `
            <a href="${job.job_url}" target="_blank" class="job-card">
                <div class="job-header">
                    <span class="platform-tag ${tagClass}">${job.platform}</span>
                    <span class="job-date">${dateStr}</span>
                </div>
                <h4 class="job-title">${job.name}</h4>
                <p class="job-company">${job.company_name}</p>
                <div class="job-meta">
                    <span class="salary">${salaryStr}</span>
                    <span class="location">${locStr}</span>
                </div>
            </a>
        `;
        container.insertAdjacentHTML('beforeend', cardHTML);
    });
}

// 匯出 CSV
async function exportCSV() {
    if (currentJobsData.length === 0) { alert('目前沒有資料可匯出'); return; }
    
    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jobs: currentJobsData, keyword: currentKeyword })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentKeyword}_職缺資料.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else { 
            alert("匯出失敗"); 
        }
    } catch(e) {
        console.error(e);
        alert("匯出過程發生錯誤");
    }
}

// 儲存至資料庫
async function saveToDB() {
    if (currentJobsData.length === 0) { alert('目前沒有資料可儲存'); return; }
    
    try {
        const response = await fetch('/api/save_db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jobs: currentJobsData, keyword: currentKeyword })
        });
        const result = await response.json();
        alert(result.message);
    } catch(e) {
        console.error(e);
        alert("儲存失敗");
    }
}

// ==========================================
// 4. 頁面初始化 (綁定事件)
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    
    // --- 首頁搜尋 (index.html) ---
    const btnSearch = document.getElementById('btn-search');
    if (btnSearch) {
        btnSearch.addEventListener('click', startAnalysis);
        // 綁定 Enter 鍵
        const inputKw = document.getElementById('keyword');
        if(inputKw) {
            inputKw.addEventListener('keypress', (e) => {
                if(e.key === 'Enter') startAnalysis();
            });
        }
    }

    // --- 篩選器變更事件 (index.html) ---
    const filterIds = ['filter-city', 'cb-104', 'cb-1111', 'sort-by'];
    filterIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', applyFilters);
        }
    });

    // --- 職缺比較頁 (stats.html) ---
    const btnStats = document.getElementById('btn-stats');
    if (btnStats) {
        btnStats.addEventListener('click', compareJobs);
        // 預設加一張卡片
        addKeywordCard();
    }
});