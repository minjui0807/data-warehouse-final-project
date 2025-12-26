// static/script.js

// --- 全域變數 ---
let currentJobsData = [];
let filteredJobsData = [];
let currentKeyword = '';

// [新增] 全域鎖，防止連點或雙重觸發
let isComparing = false; 

// 分頁切換
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active-tab'));
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) targetView.classList.add('active-tab');
    
    const navLinks = document.querySelectorAll('.nav-link');
    if (navLinks.length >= 2) {
        if (tabName === 'market') navLinks[0].classList.add('active');
        if (tabName === 'trend') navLinks[1].classList.add('active');
    }
}

async function startAnalysis(e) {
    // [修正] 擋住預設行為
    if (e) e.preventDefault();

    const keyword = document.getElementById('keyword').value;
    const maxNum = document.getElementById('max_num').value;
    const btn = document.getElementById('btn-search');
    const loader = document.getElementById('loader');
    const resultsArea = document.getElementById('results-area');

    if(!keyword) { alert("請輸入關鍵字"); return; }

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
        btn.disabled = false;
        btn.innerText = "開始分析職缺";
        loader.classList.remove('active');
    }
}

function updateUI(data) {
    document.getElementById('stat-total').innerText = data.stats.total;
    document.getElementById('stat-salary').innerText = Math.round(data.stats.avg_salary).toLocaleString();
    document.getElementById('count_104').innerText = data.stats.count_104;
    document.getElementById('count_1111').innerText = data.stats.count_1111;

    if (data.charts.salary_dist) {
        document.getElementById('chart-salary').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.salary_dist}" style="width:100%; height:auto; border-radius:8px;" />`;
    }

    if (data.charts.location_pie) {
        document.getElementById('chart-location').innerHTML = 
            `<img src="data:image/png;base64,${data.charts.location_pie}" style="width:100%; height:auto; border-radius:8px;" />`;
    }

    initCityFilter(data.jobs);
    applyFilters();
}

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
    
    // [修正] 針對 Enter 鍵的防呆處理
    input.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault(); // 1. 阻止表單提交
            compareJobs(event);     // 2. 呼叫函式並傳入 event
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

// [修正] 接收 event 參數，並加入全域鎖
async function compareJobs(e) {
    // 1. 如果有 event，阻止預設行為 (例如表單提交)
    if (e) e.preventDefault();

    // 2. 如果正在跑，直接結束，防止雙重執行
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

    // 3. 上鎖
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
        // 4. 解鎖
        isComparing = false;
        btn.disabled = false;
        btn.innerText = "開始統計分析";
        if(loader) loader.classList.remove('active');
    }
}

function initCityFilter(jobs) {
    const citySelect = document.getElementById('filter-city');
    if(!citySelect) return;
    citySelect.innerHTML = '<option value="all">所有縣市</option>';
    const cities = new Set();
    jobs.forEach(job => {
        if (job.location && job.location.length >= 3) cities.add(job.location.substring(0, 3));
    });
    Array.from(cities).sort().forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.innerText = city;
        citySelect.appendChild(option);
    });
}

function applyFilters() {
    const citySelect = document.getElementById('filter-city');
    const listContainer = document.getElementById('jobs-container');
    if(!citySelect || !listContainer) return; 
    const cityFilter = citySelect.value;
    const show104 = document.getElementById('cb-104') ? document.getElementById('cb-104').checked : true;
    const show1111 = document.getElementById('cb-1111') ? document.getElementById('cb-1111').checked : true;
    const sortBy = document.getElementById('sort-by').value;
    const minSalaryInput = document.getElementById('min-salary-input');
    const minSalary = minSalaryInput ? (parseInt(minSalaryInput.value) || 0) : 0;

    filteredJobsData = currentJobsData.filter(job => {
        if (job.platform === '104' && !show104) return false;
        if (job.platform === '1111' && !show1111) return false;
        if (cityFilter !== 'all' && !job.location.startsWith(cityFilter)) return false;
        if (minSalary > 0 && (job.salary_sort || 0) < minSalary) return false;
        return true;
    });

    filteredJobsData.sort((a, b) => {
        if (sortBy === 'salary_desc') return (b.salary_sort || 0) - (a.salary_sort || 0);
        if (sortBy === 'salary_asc') return (a.salary_sort || 0) - (b.salary_sort || 0);
        if (sortBy === 'date_desc') return (b.update_date || '').localeCompare(a.update_date || '');
        if (sortBy === 'company') return a.company_name.localeCompare(b.company_name, 'zh-Hant');
        return 0; 
    });
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
            </a>`;
        container.insertAdjacentHTML('beforeend', cardHTML);
    });
}

// 匯出/儲存功能
async function _exportCSV(dataToExport, suffix) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可匯出'); return; }
    const minSalary = document.getElementById('min-salary-input') ? document.getElementById('min-salary-input').value : '';
    const filenameSuffix = (minSalary && suffix !== 'Raw') ? `${suffix}_Over${minSalary}` : suffix;
    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jobs: dataToExport, keyword: currentKeyword, min_salary: minSalary })
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentKeyword}_${filenameSuffix}.csv`;
            document.body.appendChild(a); a.click(); a.remove();
        } else { alert("匯出失敗"); }
    } catch(e) { console.error(e); alert("匯出過程發生錯誤"); }
}

async function _saveToDB(dataToExport) {
    if (!dataToExport || dataToExport.length === 0) { alert('沒有資料可儲存'); return; }
    const minSalary = document.getElementById('min-salary-input') ? document.getElementById('min-salary-input').value : '';
    try {
        const response = await fetch('/api/save_db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jobs: dataToExport, keyword: currentKeyword, min_salary: minSalary })
        });
        const result = await response.json();
        alert(result.message);
    } catch(e) { console.error(e); alert("儲存失敗"); }
}

function exportAllCSV() { _exportCSV(currentJobsData, "Full_Raw"); }
function saveAllToDB() { _saveToDB(currentJobsData); }
function exportFilteredCSV() { _exportCSV(filteredJobsData, "Filtered"); }
function saveFilteredToDB() { _saveToDB(filteredJobsData); }

const exportCSV = exportAllCSV;
const saveToDB = saveAllToDB;

document.addEventListener('DOMContentLoaded', () => {
    // 1. 初始化單一職缺搜尋監聽
    const btnSearch = document.getElementById('btn-search');
    if (btnSearch) {
        btnSearch.addEventListener('click', startAnalysis);
        document.getElementById('keyword').addEventListener('keypress', (e) => { 
            if(e.key === 'Enter') {
                e.preventDefault(); // 記得也要加這個
                startAnalysis(e); 
            }
        });
    }

    // 2. 初始化 Filters
    ['filter-city', 'cb-104', 'cb-1111', 'sort-by'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', applyFilters);
    });

    // 3. 初始化多職缺比較監聽
    const btnStats = document.getElementById('btn-stats');
    if (btnStats) {
        // [關鍵] 這裡綁定了 click，所以 compareJobs 的參數 e 就是 ClickEvent
        btnStats.addEventListener('click', compareJobs);
        
        const container = document.getElementById('keywords-container');
        if (container && container.children.length === 0) {
             ['Python', 'Java', 'JavaScript', 'C#', 'PHP', 'Swift', 'Go', 'C++', 'Ruby'].forEach(kw => addKeywordCard(kw));
        }
    }
    switchTab('market');
});