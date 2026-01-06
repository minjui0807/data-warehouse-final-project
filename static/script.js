// static/script.js

// --- 全域變數 (主搜尋用) ---
let currentJobsData = [];   // ★ 原始完整資料
let filteredJobsData = [];  // ★ 目前篩選後的資料
let currentKeyword = '';
let isComparing = false;    // 全域鎖

// --- 全域變數 (歷史紀錄用) --- NEW ★
let historyJobsData = [];      // 歷史紀錄的原始資料
let filteredHistoryJobs = [];  // 歷史紀錄的篩選後資料
let currentHistoryKeyword = ''; // 歷史紀錄的關鍵字

// --- 分頁相關變數 ---
let currentPage = 1; //首頁的
let currentHistoryPage = 1; //歷史紀錄的
const ITEMS_PER_PAGE = 30;

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

            // 【新增這行】自動存入伺服器紀錄，並傳入 true 表示不彈出視窗
            console.log("正在自動備份至歷史紀錄...");
            saveToHistoryServer(true);
            
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
function initCityFilter(jobs, targetId = 'filter-city') {
    const citySelect = document.getElementById(targetId);
    if (!citySelect) return;

    const cities = new Set();
    
    // 1. 台灣縣市正則 (台北市、彰化縣等)
    const taiwanCityRegex = /^[^\s,]{2}[縣市]/;
    // 2. 國外行政邊界 (州、國、省)
    const globalBoundaryRegex = /^.*?[州國省]/;

    jobs.forEach(job => {
        if (job.location) {
            let loc = job.location.trim();
            
            // 優先判斷是否為台灣縣市
            const twMatch = loc.match(taiwanCityRegex);
            if (twMatch) {
                cities.add(twMatch[0]);
            } else {
                // 判斷是否有 "州/國/省" 邊界
                const globalMatch = loc.match(globalBoundaryRegex);
                if (globalMatch) {
                    // 抓到第一個 州/國/省 就停止
                    cities.add(globalMatch[0]);
                } else {
                    // 都沒有的話，抓前 2 或 3 個字作為代表
                    cities.add(loc.length > 3 ? loc.substring(0, 3) : loc);
                }
            }
        }
    });

    citySelect.innerHTML = '<option value="all">全部地區</option>';
    
    // 排序：使用繁體中文排序邏輯
    const sortedCities = Array.from(cities).sort((a, b) => {
        return a.localeCompare(b, 'zh-Hant');
    });

    sortedCities.forEach(city => {
        if (city && city !== 'null') {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        }
    });
}

// 薪水數值框關鍵修正：UI 切換 (隱藏輸入框與波浪號，並清空數值)
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
        group.style.display = 'none';
        if (minInput) minInput.value = '';
        if (maxInput) maxInput.value = '';
    } else {
        group.style.display = 'flex';
    }
    
    // 切換後自動觸發一次篩選
    applyFilters();
}

// ★ 解析薪資範圍的函式 (共用)
function parseSalaryRange(salaryStr) {
    if (!salaryStr) return { low: 0, high: 0 };
    let clean = salaryStr.replace(/,/g, '');
    let matches = clean.match(/\d+/g);
    if (!matches) return { low: 0, high: 0 };
    let nums = matches.map(n => parseInt(n));
    if (nums.length === 1) return { low: nums[0], high: nums[0] };
    if (nums.length >= 2) return { low: nums[0], high: nums[1] };
    return { low: 0, high: 0 };
}

// 核心篩選函式 (主搜尋用)
function applyFilters() {
    const citySelect = document.getElementById('filter-city');
    if(!citySelect) return; 

    const cityFilter = citySelect.value;
    const show104 = document.getElementById('cb-104') ? document.getElementById('cb-104').checked : true;
    const show1111 = document.getElementById('cb-1111') ? document.getElementById('cb-1111').checked : true;
    const sortBy = document.getElementById('sort-by').value;
    const salaryType = document.getElementById('salary-type').value; 
    const minInput = document.getElementById('min-salary-input');
    const maxInput = document.getElementById('max-salary-input');
    const salaryMin = (minInput && minInput.value) ? parseInt(minInput.value) : 0;
    const salaryMax = (maxInput && maxInput.value) ? parseInt(maxInput.value) : 0;

    // 1. 篩選邏輯
    filteredJobsData = currentJobsData.filter(job => {
        // 共用過濾邏輯
        return checkJobFilter(job, cityFilter, show104, show1111, salaryType, salaryMin, salaryMax);
    });

    // 2. 排序
    sortJobs(filteredJobsData, sortBy);

    // 3. 重置頁面
    currentPage = 1;
    const container = document.getElementById('jobs-container');
    if(container) container.innerHTML = '';
    renderCurrentPage();
}

// 抽離出共用的單筆篩選判斷 (給主搜尋和歷史紀錄共用)
function checkJobFilter(job, city, s104, s1111, sType, sMin, sMax) {
    // (A) 平台
    if (job.platform === '104' && !s104) return false;
    if (job.platform === '1111' && !s1111) return false;
    
    // (B) 地點
    if (city !== 'all' && !job.location.startsWith(city)) return false;

    // (C) 薪資類型
    if (sType !== 'all') {
        if (!job.salary) return false;
        if (sType === '面議') {
            return job.salary.includes('面議');
        }
        if (!job.salary.includes(sType)) return false;
    }

    // (D) 薪資數字
    if (sType !== '面議' && sType !== '論件') {
        if (sMin > 0 || sMax > 0) {
            const { low, high } = parseSalaryRange(job.salary);
            if (low === 0 && high === 0) return false;
            if (sMin > 0 && low < sMin) return false;
            if (sMax > 0 && high > sMax) return false;
        }
    }
    return true;
}

// 抽離出共用的排序邏輯
function sortJobs(jobsArray, sortBy) {
    jobsArray.sort((a, b) => {
        const valA = parseSalaryRange(a.salary).low;
        const valB = parseSalaryRange(b.salary).low;

        if (sortBy === 'salary_desc') return valB - valA;
        if (sortBy === 'salary_asc') return valA - valB;
        if (sortBy === 'date_desc') return (b.update_date || '').localeCompare(a.update_date || '');
        if (sortBy === 'company') return a.company_name.localeCompare(b.company_name, 'zh-Hant');
        return 0; 
    });
}

function renderCurrentPage() {
    const container = document.getElementById('jobs-container');
    const btnLoadMore = document.getElementById('btn-load-more');
    const spanShown = document.getElementById('shown-count');
    const spanTotal = document.getElementById('total-count');

    if(!container) return;

    if (filteredJobsData.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;">沒有符合篩選條件的職缺</div>';
        if(btnLoadMore) btnLoadMore.style.display = 'none';
        if(spanShown) spanShown.innerText = 0;
        if(spanTotal) spanTotal.innerText = 0;
        return;
    }

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageJobs = filteredJobsData.slice(start, end);

    const fragment = document.createDocumentFragment();
    pageJobs.forEach(job => fragment.appendChild(createJobCard(job)));

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

// 建立單張職缺卡片的 HTML 元素
function createJobCard(job) {
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
    return a;
}

// =========================================================
// 3. 匯出功能區
// =========================================================

function exportCSV() { _exportCSV(currentJobsData, "full_jobs"); } 
function exportFilteredCSV() { _exportCSV(filteredJobsData, "filtered_jobs"); }

// 通用的 CSV 匯出邏輯 (支援歷史紀錄)
async function _exportCSV(dataToExport, suffix, keywordOverride) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可匯出'); return; }
    
    const finalKeyword = keywordOverride || currentKeyword;

    // 簡易檔名後綴
    let filenameSuffix = suffix;
    
    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport, 
                keyword: finalKeyword, 
                min_salary: '' 
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${finalKeyword}_${filenameSuffix}.csv`;
            document.body.appendChild(a); a.click(); a.remove();
            window.URL.revokeObjectURL(url);
        } else { 
            alert("匯出失敗"); 
        }
    } catch(e) { console.error(e); alert("匯出過程發生錯誤"); }
}

async function _downloadDB(dataToExport, suffix, keywordOverride) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可匯出'); return; }
    
    const finalKeyword = keywordOverride || currentKeyword;
    
    try {
        const response = await fetch('/api/export_db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: dataToExport, 
                keyword: finalKeyword, 
                min_salary: ''
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${finalKeyword}_${suffix}.db`;
            document.body.appendChild(a); a.click(); a.remove();
            window.URL.revokeObjectURL(url);
        } else {
            const errData = await response.json();
            alert('下載失敗: ' + (errData.message || '未知錯誤'));
        }
    } catch(e) { 
        console.error(e); 
        alert("下載 DB 發生錯誤"); 
    }
}

// 主搜尋的匯出
function exportAllCSV() { _exportCSV(currentJobsData, "full_jobs"); }
function exportFilteredCSV() { _exportCSV(filteredJobsData, "filtered_jobs"); }
function saveAllToDB() { _downloadDB(currentJobsData, "full_jobs"); }
function saveFilteredToDB() { _downloadDB(filteredJobsData, "filtered_jobs"); }

// =========================================================
// 4. 多職缺比較功能區
// =========================================================
// (保持原樣，篇幅省略，若有需要請參考原代碼或上方邏輯)
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
                        <span style="color:white; font-size:20px;">${count.toLocaleString()}</span>
                    </div>`;
            }// 上面這段是職缺趨勢比較_詳細數據的版型
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

function switchTab(tabName) {
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(div => {
        div.style.display = 'none';
        div.classList.remove('active-tab');
    });
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    const target = document.getElementById('view-' + tabName);
    if (target) {
        target.style.display = 'block';
        setTimeout(() => target.classList.add('active-tab'), 10);
    }
    const activeBtn = document.querySelector(`.nav-link[onclick*="'${tabName}'"]`);
    if(activeBtn) {
        activeBtn.classList.add('active');
    }
}

// =========================================================
// 5. 歷史紀錄功能區 (補強篩選與匯出)
// =========================================================

async function loadHistoryItem(batchId, keyword, time) {
    const loader = document.getElementById('loader');
    if(loader) loader.classList.add('active');

    try {
        const response = await fetch('/api/load_history_item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchId })
        });
        const data = await response.json();

        if (data.status === 'success') {
            document.getElementById('history-list-view').style.display = 'none';
            document.getElementById('history-detail-view').style.display = 'block';

            historyJobsData = data.jobs;
            filteredHistoryJobs = data.jobs;
            currentHistoryKeyword = keyword;
            currentHistoryPage = 1; // ★ 重置歷史頁碼

            renderHistoryView(data, keyword, time);
        } else {
            alert('讀取失敗');
        }
    } catch(e) {
        console.error(e);
        alert('系統錯誤');
    } finally {
        if(loader) loader.classList.remove('active');
    }
}

// ★ 歷史紀錄專用：核心篩選函式 (修正後的版本)
function applyHistoryFilters() {
    // 取得所有控制項元素
    const cityEl = document.getElementById('h-filter-city');
    const sTypeEl = document.getElementById('h-salary-type');
    const sortEl = document.getElementById('h-sort-by');
    const cb104 = document.getElementById('h-cb-104');
    const cb1111 = document.getElementById('h-cb-1111');
    const minEl = document.getElementById('h-min-salary-input');
    const maxEl = document.getElementById('h-max-salary-input');

    if (!cityEl) return;

    // 取得數值
    const city = cityEl.value;
    const sType = sTypeEl.value;
    const sortBy = sortEl.value;
    const show104 = cb104 ? cb104.checked : true;
    const show1111 = cb1111 ? cb1111.checked : true;
    const sMin = parseInt(minEl?.value || 0);
    const sMax = parseInt(maxEl?.value || 0);

    // 1. 執行過濾邏輯 (複用您寫好的 checkJobFilter)
    filteredHistoryJobs = historyJobsData.filter(job => {
        return checkJobFilter(job, city, show104, show1111, sType, sMin, sMax);
    });

    // 2. 執行排序
    sortJobs(filteredHistoryJobs, sortBy);
    
    // 3. ★ 關鍵修正：重置分頁狀態並「清空容器」
    currentHistoryPage = 1; 
    const container = document.getElementById('h-jobs-list');
    if (container) {
        container.innerHTML = ''; // 必須清空，否則會累積到 100 筆以上
    }
    
    // 4. 執行渲染 (會從第 1 頁開始抓 50 筆)
    renderHistoryJobs();
}

// ★ 歷史紀錄渲染 (包含 50 筆分頁邏輯)
function renderHistoryJobs() {
    const container = document.getElementById('h-jobs-list');
    const loadMoreContainer = document.getElementById('h-load-more-container');
    const spanShown = document.getElementById('h-shown-count');
    const spanTotal = document.getElementById('h-total-count');

    if (!container) return;

    if (filteredHistoryJobs.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:20px; grid-column: 1/-1;">無符合條件的職缺</p>';
        if(loadMoreContainer) loadMoreContainer.style.display = 'none';
        if(spanShown) spanShown.innerText = 0;
        if(spanTotal) spanTotal.innerText = 0;
        return;
    }

    // 計算分頁範圍
    const start = (currentHistoryPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageJobs = filteredHistoryJobs.slice(start, end);

    // 渲染卡片
    const fragment = document.createDocumentFragment();
    pageJobs.forEach(job => fragment.appendChild(createJobCard(job)));
    container.appendChild(fragment);

    // 更新下方數字與按鈕狀態
    const currentShown = Math.min(end, filteredHistoryJobs.length);
    if(spanShown) spanShown.innerText = currentShown;
    if(spanTotal) spanTotal.innerText = filteredHistoryJobs.length;

    // 判斷是否還有更多
    if (currentShown >= filteredHistoryJobs.length) {
        if(loadMoreContainer) loadMoreContainer.style.display = 'none';
    } else {
        if(loadMoreContainer) {
            loadMoreContainer.style.display = 'block';
            const btn = document.getElementById('h-btn-load-more');
            if(btn) btn.innerHTML = `查看更多歷史職缺 (已顯示 ${currentShown} / ${filteredHistoryJobs.length})`;
        }
    }
}

// ★ 新增：歷史紀錄點擊載入更多
function loadMoreHistoryJobs() {
    currentHistoryPage++;
    renderHistoryJobs();
}

async function saveToHistoryServer() {
    if (!currentJobsData || currentJobsData.length === 0) {
        alert('目前畫面沒有資料，無法存檔。請先進行搜尋。');
        return;
    }
    const keyword = document.getElementById('keyword').value || currentKeyword || '未命名';

    try {
        const response = await fetch('/api/save_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                jobs: currentJobsData, 
                keyword: keyword 
            })
        });
        const result = await response.json();
        // 2. 移除成功/失敗的 alert：改用 console 記錄結果
        if (result.status === 'success') {
            console.log('自動存檔成功:', result.message);
        } else {
            console.error('自動儲存失敗:', result.message);
        }
    } catch(e) {
        // 3. 移除連線錯誤的 alert
        console.error('自動存檔連線錯誤:', e);
    }
}

async function loadHistoryList() {
    // 切換視圖
    document.getElementById('history-list-view').style.display = 'block';
    document.getElementById('history-detail-view').style.display = 'none';

    const container = document.getElementById('history-list-container');
    // 1. 取得剛剛在 HTML 新增的空狀態區塊
    const emptyState = document.getElementById('history-empty-state');

    // 初始狀態：顯示讀取中，隱藏空狀態
    container.innerHTML = '<p style="text-align:center; color:#666;">讀取中...</p>';
    container.style.display = 'grid'; // 確保列表容器是顯示的
    if (emptyState) emptyState.style.display = 'none';

    try {
        const response = await fetch('/api/get_history_list');
        const result = await response.json();

        if (result.status === 'success') {
            container.innerHTML = ''; // 清除讀取中文字

            // 2. ★ 修改這裡：判斷有無資料來決定顯示哪個區塊
            if (result.data.length === 0) {
                // --- 沒資料：隱藏列表，顯示空狀態 ---
                container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'block';
                return;
            }

            // --- 有資料：顯示列表，隱藏空狀態 ---
            container.style.display = 'grid';
            if (emptyState) emptyState.style.display = 'none';

            // 3. 渲染卡片 (保持原本邏輯)
            result.data.forEach(item => {
                const card = document.createElement('div');
                card.className = 'history-card';
                
                // 刪除按鈕
                const delBtn = document.createElement('div');
                delBtn.className = 'btn-delete-card';
                delBtn.innerHTML = '×';
                delBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteHistoryItem(item.batch_id);
                };

                // 卡片內容
                const content = document.createElement('div');
                content.onclick = () => loadHistoryItem(item.batch_id, item.keyword, item.save_time);
                // 歷史紀錄的卡片版型都寫死在這裡 其他地方改不了
                content.innerHTML = `
                    <h4>${item.keyword}</h4>
                    <div class="history-meta">
                        <span style="color:#C6A96B; border:1px solid #C6A96B; padding: 6px 10px; border-radius:4px;">
                            ${item.count} 筆職缺
                        </span>
                        <span style="padding: 6px 10px;">${item.save_time}</span>
                    </div>
                `;
                
                card.appendChild(delBtn);
                card.appendChild(content);
                container.appendChild(card);
            });
        }
    } catch(e) {
        console.error(e);
        container.style.display = 'block';
        container.innerHTML = '<p style="text-align:center; color:red;">讀取失敗，請檢查連線</p>';
    }
}

// 刪除歷史紀錄
async function deleteHistoryItem(batchId) {
    if (!confirm('確定要永久刪除這筆紀錄嗎？')) return;
    try {
        const response = await fetch('/api/delete_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchId })
        });
        const result = await response.json();
        if (result.status === 'success') {
            loadHistoryList();
        } else {
            alert('刪除失敗');
        }
    } catch (e) { console.error(e); }
}

async function loadHistoryItem(batchId, keyword, time) {
    const loader = document.getElementById('loader');
    if(loader) loader.classList.add('active');

    try {
        const response = await fetch('/api/load_history_item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchId })
        });
        const data = await response.json();

        if (data.status === 'success') {
            document.getElementById('history-list-view').style.display = 'none';
            document.getElementById('history-detail-view').style.display = 'block';

            historyJobsData = data.jobs;
            filteredHistoryJobs = data.jobs;
            currentHistoryKeyword = keyword;

            renderHistoryView(data, keyword, time);
        } else {
            alert('讀取失敗');
        }
    } catch(e) {
        console.error(e);
        alert('系統錯誤');
    } finally {
        if(loader) loader.classList.remove('active');
    }
}

function backToHistoryList() {
    document.getElementById('history-detail-view').style.display = 'none';
    document.getElementById('history-list-view').style.display = 'block';
    historyJobsData = [];
    filteredHistoryJobs = [];
}

// 渲染歷史詳細畫面
function renderHistoryView(data, keyword, time) {
    document.getElementById('h-keyword-title').innerText = keyword;
    document.getElementById('h-save-time').innerText = time;
    document.getElementById('h-total-jobs').innerText = data.stats.total;
    document.getElementById('h-avg-salary').innerText = Math.round(data.stats.avg_salary).toLocaleString();
    document.getElementById('h-count-104').innerText = data.stats.count_104;
    document.getElementById('h-count-1111').innerText = data.stats.count_1111;

    if (data.charts.salary_dist) {
        document.getElementById('h-chart-salary').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.salary_dist}" style="width:100%; border-radius:8px;">`;
    }
    if (data.charts.location_pie) {
        document.getElementById('h-chart-location').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.location_pie}" style="width:100%; border-radius:8px;">`;
    }

    // 初始化歷史區地區選單
    initCityFilter(data.jobs, 'h-filter-city');
    
    // 初始化薪資輸入框顯示狀態
    toggleHistorySalaryInputs();
}

// 歷史紀錄區專用的薪資輸入框切換
function toggleHistorySalaryInputs() {
    const sType = document.getElementById('h-salary-type').value;
    const group = document.getElementById('h-salary-inputs-group');
    if (!group) return;

    if (sType === 'all' || sType === '面議' || sType === '論件') {
        group.style.display = 'none';
        document.getElementById('h-min-salary-input').value = '';
        document.getElementById('h-max-salary-input').value = '';
    } else {
        group.style.display = 'flex';
    }
    applyHistoryFilters();
}



// 歷史紀錄匯出功能
function exportHistoryCSV() { _exportCSV(filteredHistoryJobs, "history_filtered", currentHistoryKeyword); }
function downloadHistoryDB() { _downloadDB(filteredHistoryJobs, "history_filtered", currentHistoryKeyword); }

// =========================================================
// 6. 初始化 (更新監聽事件)
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

    // 主搜尋篩選監聽
    ['filter-city', 'cb-104', 'cb-1111', 'sort-by'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', applyFilters);
    });
    
    const salaryTypeSelect = document.getElementById('salary-type');
    if (salaryTypeSelect) {
        salaryTypeSelect.addEventListener('change', toggleSalaryInputs);
    }

    ['min-salary-input', 'max-salary-input'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('keyup', debouncedFilter);
    });

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

    // 4. 初始化歷史紀錄區篩選監聽 (新增部分，不更動原有邏輯)
    let hFilterDebounce;
    function debouncedHistoryFilter() {
        clearTimeout(hFilterDebounce);
        hFilterDebounce = setTimeout(applyHistoryFilters, 300); 
    }

    // 歷史區下拉選單與勾選框
    ['h-filter-city', 'h-cb-104', 'h-cb-1111', 'h-sort-by'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', applyHistoryFilters);
    });
    
    // 歷史區薪資類型切換
    const hSalaryTypeSelect = document.getElementById('h-salary-type');
    if (hSalaryTypeSelect) {
        hSalaryTypeSelect.addEventListener('change', toggleHistorySalaryInputs);
    }

    // 歷史區薪資輸入框 (同樣套用防抖)
    ['h-min-salary-input', 'h-max-salary-input'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('keyup', debouncedHistoryFilter);
    });

    switchTab('market');
    toggleSalaryInputs();


    // --- 回到頂端按鈕功能 ---
    const topBtn = document.getElementById('scroll-to-top');

    if (topBtn) {
        // 監聽滾動事件
        window.onscroll = function() {
            if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
                topBtn.style.display = "block";
                topBtn.style.opacity = "1";
            } else {
                topBtn.style.opacity = "0";
                setTimeout(() => { if(topBtn.style.opacity === "0") topBtn.style.display = "none"; }, 300);
            }
        };

        // 點擊滾動回最上方
        topBtn.onclick = function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth' // 平滑滾動
            });
        };
    }
});
