// static/script.js

// --- 全域變數 ---
let currentJobsData = [];   // 原始完整資料 (Source of Truth)
let filteredJobsData = [];  // 目前篩選後的資料 (View Data)
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

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: keyword, max_num: maxNum })
        });
        const data = await response.json();

        if (data.status === 'success') {
            // [重要] 初始化資料：原始資料與篩選資料一開始是相同的
            currentJobsData = data.jobs; 
            filteredJobsData = data.jobs; 

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
    }
}

function updateUI(data) {
    // 基本統計數據
    document.getElementById('stat-total').innerText = data.stats.total;
    document.getElementById('stat-salary').innerText = Math.round(data.stats.avg_salary).toLocaleString();
    
    document.getElementById('count_104').innerText = data.stats.count_104;
    document.getElementById('count_1111').innerText = data.stats.count_1111;

    // 更新圖表
    if (data.charts.salary_dist) {
        document.getElementById('chart-salary').innerHTML = `<img src="data:image/png;base64,${data.charts.salary_dist}" style="width:100%; height:auto;" />`;
    }
    if (data.charts.location_pie) {
        document.getElementById('chart-location').innerHTML = `<img src="data:image/png;base64,${data.charts.location_pie}" style="width:100%; height:auto;" />`;
    }

    // 初始化地區選單
    initCityFilter(data.jobs);
    
    // [重要] 呼叫一次篩選函式，確保畫面與篩選條件同步
    applyFilters();
}

// ==========================================
// 2. 自訂職缺比較功能 (多關鍵字)
// ==========================================

function addKeywordCard(value = '') {
    const container = document.getElementById('keywords-container');
    if (!container) return; 

    const div = document.createElement('div');
    div.className = 'keyword-card';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'keyword-input';
    input.placeholder = '職缺名稱 (例如: PHP)';
    input.value = value;
    
    input.addEventListener("keypress", function(event) {
        if (event.key === "Enter") compareJobs();
    });
    
    const btnDel = document.createElement('button');
    btnDel.className = 'btn-remove';
    btnDel.innerHTML = '&times;';
    btnDel.onclick = function() { container.removeChild(div); };
    
    div.appendChild(input);
    div.appendChild(btnDel);
    container.appendChild(div);
    
    if (value === '') input.focus();
}

async function compareJobs() {
    const btn = document.getElementById('btn-stats');
    const loader = document.getElementById('loader');
    const resultsArea = document.getElementById('results-area');
    const textStatsArea = document.getElementById('text-stats-area');
    
    const inputs = document.querySelectorAll('.keyword-input');
    let keywords = [];
    inputs.forEach(input => {
        const val = input.value.trim();
        if (val) keywords.push(val);
    });

    if (keywords.length === 0) {
        alert("請至少輸入一個職缺關鍵字");
        return;
    }

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
            document.getElementById('chart-stats').innerHTML = `<img src="data:image/png;base64,${data.chart}" style="width:100%;" />`;
            const listContainer = document.getElementById('stats-list');
            listContainer.innerHTML = '';
            for (const [kw, count] of Object.entries(data.data)) {
                listContainer.innerHTML += `
                    <div style="background:#333; padding:8px 16px; border-radius:4px; border:1px solid #555; display:flex; align-items:center; justify-content:space-between; min-width: 150px;">
                        <span style="color:var(--gold); font-weight:bold; margin-right:10px;">${kw}</span> 
                        <span style="color:white; font-family:'Playfair Display'; font-size:18px;">${count.toLocaleString()}</span>
                    </div>`;
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
// 3. 核心邏輯：即時篩選與渲染
// ==========================================

function initCityFilter(jobs) {
    const citySelect = document.getElementById('filter-city');
    if(!citySelect) return;

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

// [核心] 整合所有條件的篩選函式 (取代舊的 applySalaryFilter)
function applyFilters() {
    const citySelect = document.getElementById('filter-city');
    const listContainer = document.getElementById('jobs-container');
    
    if(!citySelect || !listContainer) return; 

    // 1. 取得所有 UI 狀態
    const cityFilter = citySelect.value;
    const show104 = document.getElementById('cb-104') ? document.getElementById('cb-104').checked : true;
    const show1111 = document.getElementById('cb-1111') ? document.getElementById('cb-1111').checked : true;
    const sortBy = document.getElementById('sort-by').value;
    
    // [新增] 取得薪資輸入框數值 (即時輸入)
    // 若使用者未輸入或輸入負數，視為 0 (不過濾)
    const minSalaryInput = document.getElementById('min-salary-input');
    const minSalary = minSalaryInput ? (parseInt(minSalaryInput.value) || 0) : 0;

    // 2. 執行過濾 (針對 currentJobsData)
    filteredJobsData = currentJobsData.filter(job => {
        // A. 平台篩選
        if (job.platform === '104' && !show104) return false;
        if (job.platform === '1111' && !show1111) return false;
        
        // B. 地區篩選
        if (cityFilter !== 'all') {
            if (!job.location.startsWith(cityFilter)) return false;
        }

        // C. [新增] 薪資篩選 (使用後端已算好的 salary_sort)
        if (minSalary > 0) {
            // 如果 job.salary_sort (後端算的) 小於 輸入值，則過濾掉
            // 注意：有些面議工作 salary_sort 為 0，這裡會一併過濾掉
            if ((job.salary_sort || 0) < minSalary) return false;
        }

        return true;
    });

    // 3. 執行排序 (針對 filteredJobsData)
    filteredJobsData.sort((a, b) => {
        // [優化] 直接使用後端提供的 salary_sort 數字比較，不需再 parseSalary
        if (sortBy === 'salary_desc') return (b.salary_sort || 0) - (a.salary_sort || 0);
        if (sortBy === 'salary_asc') return (a.salary_sort || 0) - (b.salary_sort || 0);
        
        if (sortBy === 'date_desc') return (b.update_date || '').localeCompare(a.update_date || '');
        if (sortBy === 'company') return a.company_name.localeCompare(b.company_name, 'zh-Hant');
        return 0; // default
    });

    // 4. 渲染畫面
    renderJobsList(filteredJobsData);
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

// ==========================================
// 4. 匯出與儲存功能 (重構為支援 全量/篩選 兩模式)
// ==========================================

// 通用內部函式：發送 CSV 請求
async function _exportCSV(dataToExport, suffix) {
    if (!dataToExport || dataToExport.length === 0) {
        alert('沒有資料可匯出');
        return;
    }
    
    // 取得當前薪資輸入，僅用於檔名標示，不影響傳送的 dataToExport
    const minSalary = document.getElementById('min-salary-input') ? document.getElementById('min-salary-input').value : '';
    
    // 如果是篩選後匯出，檔名加上條件；如果是全量，suffix 會是 "Raw"
    const filenameSuffix = (minSalary && suffix !== 'Raw') ? `${suffix}_Over${minSalary}` : suffix;

    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport,  // 直接傳送這一批資料
                keyword: currentKeyword
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentKeyword}_${filenameSuffix}.csv`;
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

// 通用內部函式：發送 DB 請求
async function _saveToDB(dataToExport) {
    if (!dataToExport || dataToExport.length === 0) {
        alert('沒有資料可儲存');
        return;
    }
    try {
        const response = await fetch('/api/save_db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport,
                keyword: currentKeyword
            })
        });
        const result = await response.json();
        alert(result.message);
    } catch(e) {
        console.error(e);
        alert("儲存失敗");
    }
}

// --- 公開給 HTML 按鈕呼叫的函式 ---

// 1. 上方按鈕：匯出「完整」資料
function exportAllCSV() {
    _exportCSV(currentJobsData, "Full_Raw");
}
function saveAllToDB() {
    _saveToDB(currentJobsData);
}

// 2. 列表旁按鈕：匯出「篩選後」資料
function exportFilteredCSV() {
    _exportCSV(filteredJobsData, "Filtered");
}
function saveFilteredToDB() {
    _saveToDB(filteredJobsData);
}

// 為了相容舊版按鈕 (如果還有的話)，保留舊名指向全量匯出
const exportCSV = exportAllCSV;
const saveToDB = saveAllToDB;


// ==========================================
// 5. 頁面初始化 (綁定事件)
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    
    // --- 首頁搜尋 (index.html) ---
    const btnSearch = document.getElementById('btn-search');
    if (btnSearch) {
        btnSearch.addEventListener('click', startAnalysis);
        const inputKw = document.getElementById('keyword');
        if(inputKw) {
            inputKw.addEventListener('keypress', (e) => {
                if(e.key === 'Enter') startAnalysis();
            });
        }
    }

    // --- 篩選器變更事件 ---
    // 注意：min-salary-input 已經在 HTML 用 oninput 綁定了，這裡不需要重複綁
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
        addKeywordCard();
    }
});