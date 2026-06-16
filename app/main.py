import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, Header, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from app import config, database, line_bot, crawler
import json
from pydantic import BaseModel

app = FastAPI(title="海大選課名額監控通知機器人")

class CourseRequest(BaseModel):
    code: str

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>海大選課名額即時監控儀表板 🤖</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.06);
            --primary: #2563eb;
            --primary-glow: rgba(37, 99, 235, 0.3);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.2);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', 'Noto Sans TC', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header Styling */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            backdrop-filter: blur(8px);
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            font-size: 2rem;
            animation: float 3s ease-in-out infinite;
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            padding: 0.5rem 1rem;
            border-radius: 99px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            font-weight: 600;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        /* Stats Section */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(16px);
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.1);
        }

        .stat-info h3 {
            font-size: 0.875rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-bottom: 0.25rem;
        }

        .stat-info p {
            font-size: 2rem;
            font-weight: 700;
        }

        .stat-icon {
            font-size: 2rem;
            opacity: 0.8;
            padding: 0.5rem;
            border-radius: 12px;
        }

        .stat-icon.total { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
        .stat-icon.open { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .stat-icon.full { background: rgba(239, 68, 68, 0.1); color: var(--danger); }

        /* Action Panel */
        .action-panel {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin-bottom: 2.5rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
            backdrop-filter: blur(16px);
        }

        .input-group {
            flex: 1;
            min-width: 280px;
            position: relative;
        }

        .input-group input {
            width: 100%;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 0.875rem 1rem 0.875rem 2.75rem;
            color: var(--text-main);
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }

        .input-icon {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
        }

        .btn {
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.875rem 1.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px var(--primary-glow);
        }

        .btn:active {
            transform: translateY(1px);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .search-group {
            min-width: 240px;
            position: relative;
        }

        .search-group input {
            width: 100%;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 0.875rem 1rem 0.875rem 2.5rem;
            color: var(--text-main);
            font-size: 0.875rem;
            transition: all 0.3s ease;
        }

        .search-group input:focus {
            outline: none;
            border-color: var(--success);
        }

        /* Courses Grid */
        .courses-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .course-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
        }

        .course-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.12);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }

        .course-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .course-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #f3f4f6;
            line-height: 1.4;
            max-width: 80%;
            word-break: break-all;
            white-space: normal;
        }

        .course-code {
            font-family: monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            display: inline-block;
            margin-top: 0.25rem;
        }

        .btn-delete {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 1.25rem;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .btn-delete:hover {
            color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
        }

        .course-divider {
            height: 1px;
            background: var(--card-border);
            margin-bottom: 1rem;
        }

        .course-info-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            flex-grow: 1;
        }

        .info-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.875rem;
        }

        .info-label {
            color: var(--text-muted);
            min-width: 48px;
        }

        .info-value {
            font-weight: 500;
        }

        /* Progress Area */
        .progress-container {
            margin-top: auto;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }

        .progress-status {
            font-weight: 700;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
        }

        .status-open { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .status-full { background: rgba(239, 68, 68, 0.1); color: var(--danger); }

        .progress-bar-bg {
            height: 8px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 99px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            border-radius: 99px;
            transition: width 0.5s ease;
        }

        .progress-bar-fill.open {
            background: linear-gradient(90deg, var(--success), #34d399);
            box-shadow: 0 0 8px var(--success-glow);
        }

        .progress-bar-fill.full {
            background: linear-gradient(90deg, var(--danger), #f87171);
            box-shadow: 0 0 8px var(--danger-glow);
        }

        .card-footer {
            margin-top: 1rem;
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Empty State */
        .empty-state {
            grid-column: 1 / -1;
            text-align: center;
            padding: 5rem 2rem;
            background: var(--card-bg);
            border: 1px dashed var(--card-border);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .empty-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            opacity: 0.5;
        }

        .empty-state h3 {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }

        .empty-state p {
            color: var(--text-muted);
            font-size: 0.875rem;
            max-width: 320px;
        }

        /* Animations */
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.7; }
        }

        /* Loading Overlay */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(8px);
            z-index: 999;
            display: none;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            gap: 1.5rem;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main);
            letter-spacing: 0.05em;
        }

        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #1f2937;
            border: 1px solid var(--card-border);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            z-index: 1000;
            display: none;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.875rem;
            font-weight: 600;
            animation: slideUp 0.3s ease forwards;
        }

        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .toast-success { border-left: 4px solid var(--success); }
        .toast-error { border-left: 4px solid var(--danger); }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="logo-area">
                <span class="logo-icon">🕵️‍♂️</span>
                <div>
                    <h1>海大搶課名額即時監控儀表板</h1>
                    <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">即時校務選課系統名額巡邏與推播通知</p>
                </div>
            </div>
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>系統監控中</span>
            </div>
        </header>

        <!-- Stats Section -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-info">
                    <h3>監控課程總數</h3>
                    <p id="stat-total">0</p>
                </div>
                <span class="stat-icon total">📚</span>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <h3>有名額課程</h3>
                    <p id="stat-open" style="color: var(--success);">0</p>
                </div>
                <span class="stat-icon open">💚</span>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <h3>已額滿課程</h3>
                    <p id="stat-full" style="color: var(--danger);">0</p>
                </div>
                <span class="stat-icon full">❤️</span>
            </div>
        </div>

        <!-- Action Panel -->
        <div class="action-panel">
            <div class="input-group">
                <span class="input-icon">🔍</span>
                <input type="text" id="course-input" placeholder="輸入海大課號監控，多個課號請以空白或逗號分隔 (例: B6C03V75 B6C11M97)...">
            </div>
            <button class="btn" id="btn-add">
                <span>⚡</span>
                <span>新增監控</span>
            </button>
            <div class="search-group">
                <input type="text" id="search-filter" placeholder="篩選監控課程名稱、課號或教師...">
            </div>
        </div>

        <!-- Courses Grid -->
        <div class="courses-grid" id="courses-container">
            <!-- Loading skeleton or empty state will go here -->
        </div>
    </div>

    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text" id="loading-text">正在啟動 Playwright 爬蟲獲取最新課程名額...</div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast">
        <span id="toast-icon"></span>
        <span id="toast-message"></span>
    </div>

    <script>
        const coursesContainer = document.getElementById('courses-container');
        const courseInput = document.getElementById('course-input');
        const btnAdd = document.getElementById('btn-add');
        const searchFilter = document.getElementById('search-filter');
        const loadingOverlay = document.getElementById('loading-overlay');
        const loadingText = document.getElementById('loading-text');

        let monitoredCourses = [];

        // Fetch courses on load
        async function fetchCourses() {
            try {
                const response = await fetch('/api/courses');
                if (response.ok) {
                    monitoredCourses = await response.json();
                    renderCourses();
                }
            } catch (error) {
                console.error("Failed to fetch courses:", error);
            }
        }

        // Add course monitor
        async function addCourse() {
            const rawInput = courseInput.value.trim();
            if (!rawInput) return;

            // Extract alphanumeric tokens
            const tokens = rawInput.split(/[\s,]+/).filter(t => t.length >= 4 && t.length <= 12);
            if (tokens.length === 0) {
                showToast("請輸入有效的 4 到 12 碼課程代號", "error");
                return;
            }

            courseInput.value = '';
            showLoading(true, `正在為您即時爬取 ${tokens.length} 門課程的資料，請稍候...`);

            let successCount = 0;
            let lastError = '';

            for (const code of tokens) {
                try {
                    const response = await fetch('/api/courses', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: code })
                    });
                    
                    const result = await response.json();
                    if (response.ok) {
                        successCount++;
                    } else {
                        lastError = result.detail || "新增失敗";
                    }
                } catch (error) {
                    lastError = "連線後端 API 發生錯誤";
                }
            }

            showLoading(false);
            await fetchCourses();

            if (successCount > 0) {
                showToast(`成功新增 ${successCount} 門課程監控！`, "success");
            } else {
                showToast(lastError, "error");
            }
        }

        // Delete course monitor
        async function deleteCourse(code) {
            if (!confirm(`確定要取消監控課號 ${code} 嗎？`)) return;

            showLoading(true, `正在取消監控課號 ${code}...`);
            try {
                const response = await fetch(`/api/courses/${code}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    showToast(`已成功取消監控 ${code}！`, "success");
                } else {
                    const result = await response.json();
                    showToast(result.detail || "取消失敗", "error");
                }
            } catch (error) {
                showToast("連線 API 發生錯誤", "error");
            } finally {
                showLoading(false);
                await fetchCourses();
            }
        }

        // Render stats
        function updateStats(courses) {
            document.getElementById('stat-total').innerText = courses.length;
            const openCount = courses.filter(c => c.quota < c.max_quota).length;
            const fullCount = courses.filter(c => c.quota >= c.max_quota).length;
            document.getElementById('stat-open').innerText = openCount;
            document.getElementById('stat-full').innerText = fullCount;
        }

        // Format NTOU Time string
        function formatNtouTime(timeStr) {
            if (!timeStr || timeStr === '無') return "無";
            const parts = timeStr.split(",").map(p => p.trim()).filter(Boolean);
            if (parts.length === 0) return timeStr;
            
            const dayMap = { "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "日" };
            const days = {};
            
            parts.forEach(p => {
                if (p.length >= 2) {
                    const day = p[0];
                    const period = p.slice(1).replace(/^0+/, '');
                    if (!days[day]) days[day] = [];
                    days[day].push(period);
                }
            });
            
            const res = [];
            for (const day in days) {
                const dayName = dayMap[day] || day;
                res.push(`星期${dayName} 第 ${days[day].join(',')} 節`);
            }
            return res.join(' | ');
        }

        // Render Course Cards
        function renderCourses() {
            const filterText = searchFilter.value.toLowerCase().trim();
            const filtered = monitoredCourses.filter(c => {
                return c.name.toLowerCase().includes(filterText) ||
                       c.course_code.toLowerCase().includes(filterText) ||
                       c.teacher.toLowerCase().includes(filterText);
            });

            updateStats(monitoredCourses);

            if (filtered.length === 0) {
                coursesContainer.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon">📂</span>
                        <h3>目前無監控課程</h3>
                        <p>${filterText ? '沒有找到符合搜尋條件的課程。' : '請在上方輸入海大課號以開始即時監控選課名額！'}</p>
                    </div>
                `;
                return;
            }

            coursesContainer.innerHTML = filtered.map(c => {
                const isFull = c.quota >= c.max_quota;
                const statusText = isFull ? "已額滿" : `有名額 (剩 ${c.max_quota - c.quota} 個)`;
                const statusClass = isFull ? "status-full" : "status-open";
                const fillClass = isFull ? "full" : "open";
                const percent = Math.min(100, Math.round((c.quota / (c.max_quota || 1)) * 100));
                
                // Format last updated time
                let timeFormatted = "";
                if (c.last_updated) {
                    const t = new Date(c.last_updated.replace(" ", "T"));
                    if (!isNaN(t.getTime())) {
                        timeFormatted = t.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    } else {
                        timeFormatted = c.last_updated;
                    }
                }

                // Clear parentheses in teacher name
                const teacherClean = c.teacher.replace(/\\(.*?\\)/, '').trim();

                return `
                    <div class="course-card">
                        <div class="course-header">
                            <div>
                                <div class="course-title" title="${c.name}">${c.name}</div>
                                <span class="course-code">${c.course_code}</span>
                            </div>
                            <button class="btn-delete" onclick="deleteCourse('${c.course_code}')" title="取消監控">🗑️</button>
                        </div>
                        <div class="course-divider"></div>
                        <div class="course-info-list">
                            <div class="info-item">
                                <span class="info-label">授課教師</span>
                                <span class="info-value">${teacherClean}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">上課時間</span>
                                <span class="info-value" title="${formatNtouTime(c.time)}">${formatNtouTime(c.time)}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">教室地點</span>
                                <span class="info-value">${c.classroom || "無"}</span>
                            </div>
                        </div>
                        <div class="progress-container">
                            <div class="progress-header">
                                <span style="font-weight: 600;">名額佔比 (${percent}%)</span>
                                <span class="progress-status ${statusClass}">${statusText}</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill ${fillClass}" style="width: ${percent}%;"></div>
                            </div>
                        </div>
                        <div class="card-footer">
                            <span>人數: ${c.quota} / ${c.max_quota} 人</span>
                            <span>更新: ${timeFormatted}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

                // Helpers
        function showLoading(show, text) {
            if (show) {
                if (text) loadingText.innerText = text;
                loadingOverlay.style.display = 'flex';
            } else {
                loadingOverlay.style.display = 'none';
            }
        }

        // Event Listeners (事件綁定)
        btnAdd.addEventListener('click', addCourse);
        courseInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addCourse();
            }
        });
        searchFilter.addEventListener('input', renderCourses);

        // Auto Refresh every 10 seconds (每 10 秒自動同步)
        setInterval(fetchCourses, 10000);

        // Init
        fetchCourses();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML

@app.get("/api/courses")
async def get_courses():
    try:
        courses = database.get_all_subscribed_courses()
        res = []
        for c in courses:
            res.append({
                "course_code": c.get("course_code"),
                "name": c.get("last_name", "未知課程"),
                "teacher": c.get("last_teacher", "未知"),
                "time": c.get("last_time", "無"),
                "classroom": c.get("last_classroom", "無"),
                "quota": c.get("last_quota", 0),
                "max_quota": c.get("last_max_quota", 0),
                "last_updated": str(c.get("last_updated", ""))
            })
        return sorted(res, key=lambda x: x["course_code"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses")
async def add_course(req: CourseRequest):
    code = req.code.upper().strip()
    if not code or len(code) < 4 or len(code) > 12:
        raise HTTPException(status_code=400, detail="請輸入有效的 4 到 12 碼課號")
        
    try:
        database.subscribe_course("web_user", code)
        scrape_results = await crawler.query_courses([code])
        info = scrape_results.get(code, {})
        
        if info.get("error"):
            database.unsubscribe_course("web_user", code)
            raise HTTPException(status_code=400, detail=f"查無此課號或系統忙碌中：{info.get('error')}")
            
        name = info.get("name", "未知課程")
        quota = info.get("quota", 0)
        max_quota = info.get("max_quota", 0)
        teacher = info.get("teacher", "未知")
        time_str = info.get("time", "無")
        classroom = info.get("classroom", "無")
        
        database.update_course_state(
            code, name, quota, max_quota,
            teacher=teacher, time_str=time_str, classroom=classroom
        )
        
        return {
            "status": "success",
            "course": {
                "course_code": code,
                "name": name,
                "teacher": teacher,
                "time": time_str,
                "classroom": classroom,
                "quota": quota,
                "max_quota": max_quota
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/courses/{code}")
async def delete_course(code: str):
    code = code.upper().strip()
    try:
        database.remove_course_globally(code)
        return {"status": "success", "message": f"已成功取消監控課號 {code}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")
        
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # Verify signature
    if not line_bot.verify_signature(body, x_line_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
        
    try:
        payload = json.loads(body_str)
        events = payload.get("events", [])
        # Process events
        await line_bot.process_events(events)
    except Exception as e:
        print(f"Error processing webhook events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "ok"}

async def check_courses_task():
    """
    Background worker for course checking.
    """
    print("CRON: Starting check-courses task...")
    try:
        active_courses = database.get_all_subscribed_courses()
        if not active_courses:
            print("CRON: No active course subscriptions found.")
            return
            
        course_codes = [c["course_code"] for c in active_courses]
        print(f"CRON: Found {len(course_codes)} active courses to monitor: {course_codes}")
        
        # Scrape current states using Playwright
        scrape_results = await crawler.query_courses(course_codes)
        
        user_to_courses = {} # maps user_id -> list of course details for periodic report
        
        # Check transitions and collect statuses
        for course_db in active_courses:
            code = course_db["course_code"]
            subscribers = course_db.get("subscribers", [])
            last_quota = course_db.get("last_quota", -1)
            last_max_quota = course_db.get("last_max_quota", -1)
            
            info = scrape_results.get(code, {})
            error = info.get("error")
            
            if error:
                print(f"CRON: Scrape error for {code}: {error}")
                # Fallback to DB last known values
                name = course_db.get("last_name", "未知課程")
                quota = course_db.get("last_quota", 0)
                max_quota = course_db.get("last_max_quota", 0)
                teacher = course_db.get("last_teacher", "未知")
                time_str = course_db.get("last_time", "無")
                classroom = course_db.get("last_classroom", "無")
            else:
                name = info.get("name", "未知課程")
                quota = info.get("quota", 0)
                max_quota = info.get("max_quota", 0)
                teacher = info.get("teacher", "未知")
                time_str = info.get("time", "無")
                classroom = info.get("classroom", "無")
                
                # Update database state
                database.update_course_state(
                    code, name, quota, max_quota,
                    teacher=teacher, time_str=time_str, classroom=classroom
                )
                
                # Check for transition alert (from Full to Open)
                is_first_run_open = (last_quota == -1 and quota < max_quota)
                is_transition_to_open = (last_quota >= last_max_quota and last_quota != -1 and quota < max_quota)
                
                if is_first_run_open or is_transition_to_open:
                    print(f"CRON: Triggering alert for {code}! Slots released.")
                    alert_text = (
                        f"🔔【海大搶課名額釋出通知】\n\n"
                        f"您關注的課程《{name}》（課號：{code}）目前有名額空缺囉！\n\n"
                        f"👤 授課老師：{teacher}\n"
                        f"📅 上課時間：{time_str} ({classroom})\n"
                        f"📊 目前人數：{quota} / {max_quota} 人\n\n"
                        f"👉 請盡快登入海大系統搶課！"
                    )
                    
                    for user_id in subscribers:
                        try:
                            line_bot.push_notification(user_id, alert_text)
                        except Exception as push_ex:
                            print(f"CRON: Push failed for user {user_id}: {push_ex}")
            
            # Map course info to each subscriber
            for user_id in subscribers:
                if user_id not in user_to_courses:
                    user_to_courses[user_id] = []
                user_to_courses[user_id].append({
                    "code": code,
                    "name": name,
                    "teacher": teacher,
                    "time": time_str,
                    "classroom": classroom,
                    "quota": quota,
                    "max_quota": max_quota,
                    "error": error
                })
                
        # Send periodic Flex Carousel reports to active subscribers
        print(f"CRON: Sending periodic reports to {len(user_to_courses)} active users...")
        for user_id, courses in user_to_courses.items():
            try:
                bubbles = []
                for c in courses[:10]: # Flex carousel limit is 10 bubbles
                    bubble = line_bot.create_course_flex_bubble(
                        c["code"], c["name"], c["teacher"], c["time"], c["classroom"], c["quota"], c["max_quota"], error=c["error"]
                    )
                    bubbles.append(bubble)
                    
                flex_msg = {
                    "type": "flex",
                    "altText": "定時課程名額回報",
                    "contents": {
                        "type": "carousel",
                        "contents": bubbles
                    }
                }
                
                messages = [
                    {
                        "type": "text",
                        "text": "📊【每半小時定時名額回報】🕵️\n您目前監控中的課程最新狀態如下："
                    },
                    flex_msg
                ]
                
                if len(courses) > 10:
                    messages.append({
                        "type": "text",
                        "text": f"💡 您目前共訂閱了 {len(courses)} 門課程。上方僅顯示前 10 門，您隨時可輸入「清單」查看完整列表。"
                    })
                    
                line_bot.push_messages(user_id, messages)
                print(f"CRON: Sent periodic report to user {user_id} with {len(courses)} courses.")
            except Exception as report_ex:
                print(f"CRON: Failed to send periodic report to user {user_id}: {report_ex}")
                
        print("CRON: check-courses task finished successfully.")
        
    except Exception as e:
        print(f"CRON: Error in check_courses_task: {e}")
        
    except Exception as e:
        print(f"CRON: Error in check_courses_task: {e}")

@app.get("/cron/check-courses")
async def check_courses_get(background_tasks: BackgroundTasks, secret: str = Query(None)):
    """
    Trigger course checks via GET request.
    Protected by a query parameter 'secret'.
    """
    if secret != config.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
        
    background_tasks.add_task(check_courses_task)
    return {"status": "accepted", "message": "Check courses background task started."}

@app.post("/cron/check-courses")
async def check_courses_post(background_tasks: BackgroundTasks, secret: str = Query(None)):
    """
    Trigger course checks via POST request.
    Protected by a query parameter 'secret'.
    """
    if secret != config.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
        
    background_tasks.add_task(check_courses_task)
    return {"status": "accepted", "message": "Check courses background task started."}

@app.on_event("startup")
async def startup_event():
    # Start the local periodic checker loop (every 30 minutes)
    asyncio.create_task(periodic_check_loop())

async def periodic_check_loop():
    print("Background scheduler: Starting periodic check loop...")
    while True:
        try:
            await asyncio.sleep(1800) # Wait 30 minutes
            print("Background scheduler: Running course status check...")
            await check_courses_task()
        except asyncio.CancelledError:
            print("Background scheduler: Loop cancelled.")
            break
        except Exception as e:
            print(f"Background scheduler error: {e}")
