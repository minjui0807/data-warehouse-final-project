// static/script.js

// --- 全域變數 ---
let currentJobsData = [];   // ★ 原始完整資料
let filteredJobsData = [];  // ★ 目前篩選後的資料
let currentKeyword = '';
let isComparing = false;    // 全域鎖

// --- 分頁相關變數 ---
let currentPage = 1;
const ITEMS_PER_PAGE = 50;

// =========================================================
// 1. 核心邏輯區 (搜尋與資料抓取)
// =========================================================

async function startAnalysis(e) {
    if (e) e.preventDefault();

    const keyword = document.getElementById('keyword').value;
    const maxNum = document.getElementById('max_num').value;
    const btn = document.getElementById('btn-search');
    const loader = document.getElementById('loader');
    const resultsArea = document.getElementById('results-area');

    if(!keyword) { alert("請輸入關鍵字"); return; }

    // UI 狀態更新
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
            // ★ 資料重置
            currentJobsData = data.jobs;   // 保存原始檔
            filteredJobsData = data.jobs;  // 初始篩選檔 = 原始檔
            currentPage = 1;               // 重置頁碼
            
            updateUI(data); 
            resultsArea.classList.add('visible'); 
        } else {
            alert('搜尋失敗: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('系統錯誤，請檢查後端是否執行中');
    } finally {
        btn.disabled = false;
        btn.innerText = "開始分析職缺";
        loader.classList.remove('active');
    }
}

function updateUI(data) {
    // 更新統計數字
    document.getElementById('stat-total').innerText = data.stats.total;
    document.getElementById('stat-salary').innerText = Math.round(data.stats.avg_salary).toLocaleString();
    document.getElementById('count_104').innerText = data.stats.count_104;
    document.getElementById('count_1111').innerText = data.stats.count_1111;

    // 更新圖表
    if (data.charts.salary_dist) {
        document.getElementById('chart-salary').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.salary_dist}" style="width:100%; height:auto; border-radius:8px;" />`;
    }
    if (data.charts.location_pie) {
        document.getElementById('chart-location').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.location_pie}" style="width:100%; height:auto; border-radius:8px;" />`;
    }

    // 初始化篩選器並進行第一次渲染
    initCityFilter(data.jobs);
    
    // 初始化 UI 狀態 (例如確保輸入框隱藏狀態正確)
    toggleSalaryInputs();
}

// =========================================================
// 2. 篩選與渲染優化區
// =========================================================

// 初始化縣市下拉選單
function initCityFilter(jobs) {
    const citySelect = document.getElementById('filter-city');
    if (!citySelect) return;

    const cities = new Set();
    jobs.forEach(job => {
        if (job.location && job.location.length >= 3) {
            cities.add(job.location.substring(0, 3));
        }
    });

    citySelect.innerHTML = '<option value="all">全部地區</option>';
    
    Array.from(cities).sort().forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        citySelect.appendChild(option);
    });
}

// ★ 關鍵修正：UI 切換 (隱藏輸入框與波浪號，並清空數值)
function toggleSalaryInputs() {
    const sTypeSelect = document.getElementById('salary-type');
    const group = document.getElementById('salary-inputs-group'); // 包裹輸入框和 ~ 的父層
    const minInput = document.getElementById('min-salary-input');
    const maxInput = document.getElementById('max-salary-input');
    
    if (!sTypeSelect || !group) return;

    const sType = sTypeSelect.value;
    
    // 判斷是否需要隱藏：所有類型、面議、論件
    const shouldHide = (sType === 'all' || sType === '面議' || sType === '論件');

    if (shouldHide) {
        // 隱藏整組 (包含 ~)
        group.style.display = 'none';
        
        // ★ 關鍵：隱藏時清空數值，避免影響篩選
        if (minInput) minInput.value = '';
        if (maxInput) maxInput.value = '';
    } else {
        // 顯示
        group.style.display = 'flex';
    }
    
    // 切換後自動觸發一次篩選
    applyFilters();
}

// ★ 補上：解析薪資範圍的函式 (數字篩選核心)
function parseSalaryRange(salaryStr) {
    if (!salaryStr) return { low: 0, high: 0 };
    
    // 移除逗號
    let clean = salaryStr.replace(/,/g, '');
    
    // 抓取所有數字
    let matches = clean.match(/\d+/g);
    
    if (!matches) return { low: 0, high: 0 };
    
    let nums = matches.map(n => parseInt(n));
    
    // 只有一個數字 (例如: 月薪 40000 以上)
    if (nums.length === 1) {
        return { low: nums[0], high: nums[0] };
    }
    
    // 有兩個數字 (例如: 月薪 35000~45000)
    if (nums.length >= 2) {
        return { low: nums[0], high: nums[1] };
    }
    
    return { low: 0, high: 0 };
}

// 核心篩選函式
function applyFilters() {
    console.log("執行篩選..."); // Debug 用

    const citySelect = document.getElementById('filter-city');
    if(!citySelect) return; 

    const cityFilter = citySelect.value;
    const show104 = document.getElementById('cb-104') ? document.getElementById('cb-104').checked : true;
    const show1111 = document.getElementById('cb-1111') ? document.getElementById('cb-1111').checked : true;
    const sortBy = document.getElementById('sort-by').value;

    const salaryType = document.getElementById('salary-type').value; 
    
    // 注意：這裡使用統一名稱 min-salary-input / max-salary-input
    const minInput = document.getElementById('min-salary-input');
    const maxInput = document.getElementById('max-salary-input');
    
    const salaryMin = (minInput && minInput.value) ? parseInt(minInput.value) : 0;
    const salaryMax = (maxInput && maxInput.value) ? parseInt(maxInput.value) : 0;

    // 1. 篩選邏輯
    filteredJobsData = currentJobsData.filter(job => {
        // (A) 平台
        if (job.platform === '104' && !show104) return false;
        if (job.platform === '1111' && !show1111) return false;
        
        // (B) 地點
        if (cityFilter !== 'all' && !job.location.startsWith(cityFilter)) return false;

        // (C) 薪資類型 (文字比對)
        // 如果不是選 "all"，就要檢查文字是否包含 (例如選"月薪"，薪資字串必須有"月薪")
        if (salaryType !== 'all') {
            if (!job.salary) return false; // 沒寫薪資的踢掉
            
            // 特殊處理：選 "面議" 時，只要有 "面議" 兩字就過關，不比對數字
            if (salaryType === '面議') {
                return job.salary.includes('面議');
            }
            
            // 其他類型 (月薪、時薪...)
            if (!job.salary.includes(salaryType)) return false;
        }

        // (D) 薪資數字篩選 (只有當類型不是 "面議" 且不是 "論件" 時才執行)
        // 且只有當使用者有輸入 min 或 max 時才執行
        if (salaryType !== '面議' && salaryType !== '論件') {
            if (salaryMin > 0 || salaryMax > 0) {
                // 解析該職缺的薪資數字
                const { low, high } = parseSalaryRange(job.salary);

                // 如果解析出來是 0 (例如格式錯誤)，但使用者又有要求數字 -> 踢掉
                if (low === 0 && high === 0) return false;

                // 檢查最小值：職缺的 Low 必須 >= 使用者輸入的 Min
                if (salaryMin > 0 && low < salaryMin) return false;

                // 檢查最大值：職缺的 High 必須 <= 使用者輸入的 Max
                if (salaryMax > 0 && high > salaryMax) return false;
            }
        }

        return true;
    });

    // 2. 排序
    filteredJobsData.sort((a, b) => {
        // 為了排序準確，即時解析薪資
        const valA = parseSalaryRange(a.salary).low;
        const valB = parseSalaryRange(b.salary).low;

        if (sortBy === 'salary_desc') return valB - valA;
        if (sortBy === 'salary_asc') return valA - valB;
        
        if (sortBy === 'date_desc') return (b.update_date || '').localeCompare(a.update_date || '');
        if (sortBy === 'company') return a.company_name.localeCompare(b.company_name, 'zh-Hant');
        return 0; 
    });

    // 3. 重置頁面
    currentPage = 1;
    const container = document.getElementById('jobs-container');
    if(container) container.innerHTML = '';
    renderCurrentPage();
}

function renderCurrentPage() {
    const container = document.getElementById('jobs-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    const spanShown = document.getElementById('shown-count');
    const spanTotal = document.getElementById('total-count');

    if(!container) return;

    // 無資料處理
    if (filteredJobsData.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;">沒有符合篩選條件的職缺</div>';
        if(btnLoadMore) btnLoadMore.style.display = 'none';
        if(spanShown) spanShown.innerText = 0;
        if(spanTotal) spanTotal.innerText = 0;
        return;
    }

    // 分頁計算
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageJobs = filteredJobsData.slice(start, end);

    const fragment = document.createDocumentFragment();

    pageJobs.forEach(job => {
        const tagClass = job.platform === '104' ? 'tag-104' : 'tag-1111';
        const dateStr = job.update_date || '近期';
        const salaryStr = job.salary || '面議';
        const locStr = job.location || '台灣';
        
        const a = document.createElement('a');
        a.href = job.job_url;
        a.target = "_blank";
        a.className = "job-card";
        a.innerHTML = `
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
        `;
        fragment.appendChild(a);
    });

    container.appendChild(fragment);

    // 更新按鈕狀態
    const currentShown = Math.min(end, filteredJobsData.length);
    if(spanShown) spanShown.innerText = currentShown;
    if(spanTotal) spanTotal.innerText = filteredJobsData.length;

    if (currentShown >= filteredJobsData.length) {
        if(btnLoadMore) btnLoadMore.style.display = 'none';
    } else {
        if(btnLoadMore) {
            btnLoadMore.style.display = 'inline-flex';
            btnLoadMore.disabled = false;
            btnLoadMore.innerHTML = `查看更多職缺 (已顯示 ${currentShown} / ${filteredJobsData.length})`;
        }
    }
}

function loadMoreJobs() {
    currentPage++;
    renderCurrentPage();
}

// =========================================================
// 3. 匯出功能區
// =========================================================

// 通用的 CSV 匯出邏輯
async function _exportCSV(dataToExport, suffix) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可匯出'); return; }
    
    const sType = document.getElementById('salary-type').value;
    const sMin = document.getElementById('min-salary-input').value;
    const sMax = document.getElementById('max-salary-input').value;
    
    let filenameSuffix = suffix;
    if (suffix !== 'Raw_Full') {
        if (sType !== 'all') filenameSuffix += `_${sType}`;
        if (sMin) filenameSuffix += `_Over${sMin}`;
        if (sMax) filenameSuffix += `_Under${sMax}`;
    }
    
    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport, 
                keyword: currentKeyword, 
                min_salary: sMin 
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentKeyword}_${filenameSuffix}.csv`;
            document.body.appendChild(a); a.click(); a.remove();
            window.URL.revokeObjectURL(url);
        } else { 
            alert("匯出失敗"); 
        }
    } catch(e) { console.error(e); alert("匯出過程發生錯誤"); }
}

// ★★★ 新增：通用的 DB 下載邏輯 (取代舊的 _saveToDB) ★★★
async function _downloadDB(dataToExport, suffix) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可匯出'); return; }
    
    // 取得篩選條件，主要是為了傳給後端做二次確認或紀錄，或者過濾條件
    const minSalary = document.getElementById('min-salary-input') ? document.getElementById('min-salary-input').value : '';

    try {
        // 改成呼叫新的 /api/export_db 接口
        const response = await fetch('/api/export_db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport, 
                keyword: currentKeyword, 
                min_salary: minSalary 
            })
        });

        if (response.ok) {
            // 處理二進位檔案流 (Blob)
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            // 設定下載檔名
            a.download = `${currentKeyword}_${suffix}.db`;
            document.body.appendChild(a); 
            a.click(); 
            a.remove();
            window.URL.revokeObjectURL(url);
        } else {
            // 嘗試讀取錯誤訊息
            const errData = await response.json();
            alert('下載失敗: ' + (errData.message || '未知錯誤'));
        }
    } catch(e) { 
        console.error(e); 
        alert("下載 DB 發生錯誤"); 
    }
}

// 1. 匯出全部 CSV
function exportAllCSV() { 
    console.log("匯出完整 CSV");
    _exportCSV(currentJobsData, "full_jobs"); 
}

// 2. 匯出篩選 CSV
function exportFilteredCSV() { 
    console.log("匯出篩選 CSV");
    _exportCSV(filteredJobsData, "filtered_jobs"); 
}

// 3. 下載全部 DB (呼叫新的 _downloadDB)
function saveAllToDB() { 
    console.log("下載完整 DB");
    _downloadDB(currentJobsData, "full_jobs"); 
}

// 4. 下載篩選 DB (呼叫新的 _downloadDB)
function saveFilteredToDB() { 
    console.log("下載篩選 DB");
    _downloadDB(filteredJobsData, "filtered_jobs"); 
}

// =========================================================
// 4. 多職缺比較功能區
// =========================================================

function addKeywordCard(value = '') {
    const container = document.getElementById('keywords-container');
    if (!container) return; 
    const div = document.createElement('div');
    div.className = 'keyword-card';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'keyword-input';
    input.placeholder = '職缺名稱';
    input.value = value;
    
    input.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            compareJobs(event);
        }
    });

    const btnDel = document.createElement('button');
    btnDel.className = 'btn-remove';
    btnDel.innerHTML = '&times;';
    btnDel.type = 'button'; 
    btnDel.onclick = function() { container.removeChild(div); };
    div.appendChild(input);
    div.appendChild(btnDel);
    container.appendChild(div);
    if (value === '') input.focus();
}

async function compareJobs(e) {
    if (e) e.preventDefault();
    if (isComparing) return;

    const btn = document.getElementById('btn-stats');
    const loader = document.getElementById('loader-stats') || document.getElementById('loader'); 
    const textStatsArea = document.getElementById('text-stats-area');
    
    const inputs = document.querySelectorAll('.keyword-input');
    let keywords = [];
    inputs.forEach(input => {
        const val = input.value.trim();
        if (val) keywords.push(val);
    });

    if (keywords.length === 0) { alert("請至少輸入一個職缺關鍵字"); return; }

    isComparing = true;
    btn.disabled = true;
    btn.innerText = "統計中...";
    if(loader) loader.classList.add('active');
    
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
                        <span style="color:white; font-size:18px;">${count.toLocaleString()}</span>
                    </div>`;
            }
            if(textStatsArea) textStatsArea.style.display = 'block';
        } else {
            alert('統計失敗: ' + data.message);
        }
    } catch (error) {
        console.error(error);
        alert('系統發生錯誤');
    } finally {
        isComparing = false;
        btn.disabled = false;
        btn.innerText = "開始統計分析";
        if(loader) loader.classList.remove('active');
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    const target = document.getElementById(`tab-${tabId}`);
    if(target) target.classList.add('active');
    
    const btn = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
    if(btn) btn.classList.add('active');
}

// =========================================================
// 5. 初始化 (更新監聽事件)
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
    // 1. 初始化單一職缺搜尋監聽
    const btnSearch = document.getElementById('btn-search');
    if (btnSearch) {
        btnSearch.addEventListener('click', startAnalysis);
        document.getElementById('keyword').addEventListener('keypress', (e) => { 
            if(e.key === 'Enter') { e.preventDefault(); startAnalysis(e); }
        });
    }

    // 2. 初始化 Filters (加上防抖 Debounce)
    let filterDebounce;
    function debouncedFilter() {
        clearTimeout(filterDebounce);
        filterDebounce = setTimeout(applyFilters, 300); 
    }

    // 綁定下拉選單
    ['filter-city', 'cb-104', 'cb-1111', 'sort-by'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', applyFilters);
    });
    
    // 綁定薪資類型下拉選單 (這會觸發 toggleSalaryInputs)
    const salaryTypeSelect = document.getElementById('salary-type');
    if (salaryTypeSelect) {
        salaryTypeSelect.addEventListener('change', toggleSalaryInputs);
    }

    // 綁定數字輸入框 (注意 ID 已經改為 min-salary-input)
    ['min-salary-input', 'max-salary-input'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('keyup', debouncedFilter);
    });

    // 綁定「載入更多」按鈕
    const btnLoadMore = document.getElementById('btn-load-more');
    if (btnLoadMore) {
        btnLoadMore.addEventListener('click', loadMoreJobs);
    }

    // 3. 初始化多職缺比較監聽
    const btnStats = document.getElementById('btn-stats');
    if (btnStats) {
        btnStats.addEventListener('click', compareJobs);
        const container = document.getElementById('keywords-container');
        if (container && container.children.length === 0) {
             ['Python', 'Java', 'JavaScript', 'C#', 'PHP', 'Swift', 'Go', 'C++', 'Ruby'].forEach(kw => addKeywordCard(kw));
        }
    }

    switchTab('market');
    // 頁面載入後執行一次狀態檢查 (確保輸入框初始狀態正確)
    toggleSalaryInputs();
});