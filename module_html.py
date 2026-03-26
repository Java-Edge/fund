# -*- coding: UTF-8 -*-

def get_table_html(title, data, sortable_columns=None):
    """
    生成单个表格的HTML代码。
    :param title: list, 表头标题列表。
    :param data: list of lists, 表格数据。
    :param sortable_columns: list, 可排序的列的索引 (从0开始)。例如 [1, 2, 3]
    """
    if sortable_columns is None:
        sortable_columns = []

    ths = []
    for i, col_name in enumerate(title):
        if i in sortable_columns:
            ths.append(f'<th class="sortable" onclick="sortTable(this.closest(\'table\'), {i})">{col_name}</th>')
        else:
            ths.append(f"<th>{col_name}</th>")

    thead_html = f"""
    <thead>
        <tr>
            {''.join(ths)}
        </tr>
    </thead>
    """

    tbody_rows = []
    for row_data in data:
        tds = [f"<td>{x}</td>" for x in row_data]
        tbody_rows.append(f"<tr>{''.join(tds)}</tr>")

    tbody_html = f"""
    <tbody>
        {''.join(tbody_rows)}
    </tbody>
    """

    return f"""
    <div class="table-container">
        <table class="style-table">
            {thead_html}
            {tbody_html}
        </table>
    </div>
    """


def get_full_page_html(tabs_data):
    js_script = get_javascript_code()
    css_style = get_css_style()

    # Generate Tab Headers
    tab_headers = []
    tab_contents = []

    # Check if tabs_data is a list of dicts (new format) or list of strings (old format fallback)
    if isinstance(tabs_data, list) and len(tabs_data) > 0 and isinstance(tabs_data[0], str):
        # Fallback for old format
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MaYi Fund Dashboard</title>
            {css_style}
        </head>
        <body>
            <div class="app-container">
                <div class="main-content">
                    <div class="dashboard-grid">
                        {''.join(tabs_data)}
                    </div>
                </div>
            </div>
            {js_script}
        </body>
        </html>
        """

    for index, tab in enumerate(tabs_data):
        is_active = 'active' if index == 0 else ''
        tab_id = tab['id']
        tab_title = tab['title']
        content = tab['content']

        tab_headers.append(f"""
            <button class="tab-button {is_active}" onclick="openTab(event, '{tab_id}')">
                {tab_title}
            </button>
        """)

        tab_contents.append(f"""
            <div id="{tab_id}" class="tab-content {is_active}">
                {content}
            </div>
        """)

    # Check if we have actual data or if this is initial SSE setup
    has_data = tabs_data and len(tabs_data) > 0 and tabs_data[0].get('content', '').strip()

    if not has_data:
        # Return SSE-enabled loading page
        return get_sse_loading_page(css_style, js_script)

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>MaYi Fund Dashboard</title>
        {css_style}
    </head>
    <body>
        <nav class="navbar">
            <div class="navbar-brand">MaYi Fund 蚂蚁基金助手</div>
            <div class="navbar-menu">
                <span class="navbar-item">实时行情</span>
            </div>
        </nav>
        
        <div class="app-container">
            <div class="main-content">
                <div class="tabs-header">
                    {''.join(tab_headers)}
                </div>
                <div class="dashboard-grid">
                    {''.join(tab_contents)}
                </div>
            </div>
        </div>

        {js_script}
    </body>
    </html>
    """


def get_sse_loading_page(css_style, js_script):
    """Return a loading page that will be updated via SSE"""
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MaYi Fund Dashboard - Loading</title>
        {css_style}
        <style>
            .loading-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                padding: 2rem;
            }}
            .loading-spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid var(--bloomberg-blue);
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .loading-status {{
                margin-top: 1rem;
                font-size: 0.9rem;
                color: #666;
            }}
            .task-list {{
                margin-top: 1rem;
                max-width: 400px;
            }}
            .task-item {{
                padding: 0.5rem;
                margin: 0.3rem 0;
                border-radius: 4px;
                background: #f5f5f5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .task-item.completed {{
                background: #d4edda;
                color: #155724;
            }}
            .task-item.error {{
                background: #f8d7da;
                color: #721c24;
            }}
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="navbar-brand">MaYi Fund 蚂蚁基金助手</div>
            <div class="navbar-menu">
                <span class="navbar-item">加载中...</span>
            </div>
        </nav>
        
        <div class="app-container">
            <div class="main-content">
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-status" id="status">正在连接数据源...</div>
                    <div class="task-list" id="task-list"></div>
                </div>
            </div>
        </div>

        <script>
        const eventSource = new EventSource('/fund' + window.location.search);
        const taskList = document.getElementById('task-list');
        const statusEl = document.getElementById('status');
        const taskElements = {{}};

        eventSource.addEventListener('message', function(e) {{
            try {{
                const data = JSON.parse(e.data);
                
                if (data.type === 'init') {{
                    statusEl.textContent = '正在加载数据模块...';
                    data.tasks.forEach(taskName => {{
                        const taskEl = document.createElement('div');
                        taskEl.className = 'task-item';
                        taskEl.innerHTML = `<span>${{getTaskTitle(taskName)}}</span><span>⏳</span>`;
                        taskList.appendChild(taskEl);
                        taskElements[taskName] = taskEl;
                    }});
                }}
                else if (data.type === 'task_complete') {{
                    if (taskElements[data.name]) {{
                        taskElements[data.name].className = 'task-item completed';
                        taskElements[data.name].querySelector('span:last-child').textContent = '✓';
                    }}
                }}
                else if (data.type === 'error') {{
                    if (taskElements[data.name]) {{
                        taskElements[data.name].className = 'task-item error';
                        taskElements[data.name].querySelector('span:last-child').textContent = '✗';
                    }}
                }}
                else if (data.type === 'complete') {{
                    statusEl.textContent = '加载完成！正在渲染页面...';
                    eventSource.close();
                    // Replace entire page with the complete HTML
                    document.open();
                    document.write(data.html);
                    document.close();
                }}
            }} catch (err) {{
                console.error('SSE parse error:', err);
            }}
        }});

        eventSource.addEventListener('error', function(e) {{
            statusEl.textContent = '连接错误，正在重试...';
            console.error('SSE error:', e);
        }});

        function getTaskTitle(taskName) {{
            const titles = {{
                'kx': '7*24快讯',
                'marker': '全球指数',
                'real_time_gold': '实时贵金属',
                'gold': '历史金价',
                'seven_A': '成交量趋势',
                'A': '上证分时',
                'fund': '自选基金',
                'bk': '行业板块'
            }};
            return titles[taskName] || taskName;
        }}
        </script>
    </body>
    </html>
    """


def get_css_style():
    return r"""
    <style>
        :root {
            --primary-color: #000000;
            --background-color: #ffffff;
            --card-background: #ffffff;
            --text-color: #000000;
            --border-color: #000000;
            --header-bg: #ffffff;
            --hover-bg: #f0f0f0;
            /* Bloomberg 风格：鲜艳的红绿用于金融数据 */
            --up-color: #d10000; /* Red for rise (China) */
            --down-color: #008000; /* Green for fall (China) */
            /* Bloomberg 特有的强调蓝 */
            --bloomberg-blue: #0070e0;
            --font-family: "Haas Grot Text R", "Helvetica Neue", Helvetica, Arial, sans-serif;
            --font-mono: "Menlo", "Consolas", "Roboto Mono", monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.4;
            -webkit-font-smoothing: antialiased;
        }

        /* Navbar */
        .navbar {
            background-color: #000000;
            color: #ffffff;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 4px solid var(--bloomberg-blue);
        }

        .navbar-brand {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-transform: uppercase;
        }

        .navbar-item {
            font-weight: 700;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Layout */
        .app-container {
            display: flex;
            min-height: calc(100vh - 60px); /* Subtract navbar height */
            overflow: hidden; /* Prevent body scroll */
        }

        .tabs-header {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 1rem;
            background: #fff;
            padding: 0 1rem;
        }

        .tab-button {
            padding: 12px 24px;
            background: none;
            border: none;
            cursor: pointer;
            font-weight: 700;
            text-align: center;
            position: relative;
            transition: all 0.3s;
            color: #666;
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .tab-button:hover {
            color: var(--bloomberg-blue);
            background-color: rgba(0, 112, 224, 0.05);
        }

        .tab-button.active {
            color: var(--bloomberg-blue);
            border-bottom: 3px solid var(--bloomberg-blue);
        }

        .tab-content {
            display: none;
            padding: 1rem 0;
            animation: fadeIn 0.3s ease-in-out;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .dashboard-grid {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 1rem;
        }

        .tab-button {
            flex: 1;
            padding: 12px 16px;
            background: none;
            border: none;
            cursor: pointer;
            font-weight: 700;
            text-align: center;
            position: relative;
            transition: color 0.3s;
        }

        .tab-button.active {
            color: var(--bloomberg-blue);
            border-bottom: 2px solid var(--bloomberg-blue);
        }

        .tab-content {
            display: none;
            padding: 1rem 0;
        }

        .tab-content.active {
            display: block;
        }

        .dashboard-grid {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            padding-bottom: 40px;
        }

        .main-content {
            padding: 2rem;
            flex: 1;
            margin: 0;
            overflow-y: auto;
            height: calc(100vh - 60px);
            background-color: #f5f5f5;
        }

        /* Tables */
        .table-container {
            background: var(--card-background);
            /* Bloomberg 风格：无圆角，无阴影，只有实线 */
            border-top: 4px solid #000000;
            border-bottom: 1px solid #000000;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin-bottom: 1rem;
        }

        .style-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }

        .style-table th {
            text-align: left;
            padding: 12px 16px;
            background-color: var(--header-bg);
            font-weight: 800;
            color: #000000;
            border-bottom: 2px solid #000000;
            white-space: nowrap;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .style-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #e0e0e0;
            color: #000000;
            font-weight: 400;
        }

        .style-table tbody tr:hover {
            background-color: var(--hover-bg);
        }
        
        /* 最后一行的下划线加粗 */
        .style-table tbody tr:last-child td {
            border-bottom: 1px solid #000000;
        }

        /* Sortable Headers */
        .style-table th.sortable {
            cursor: pointer;
            user-select: none;
            transition: color 0.2s;
        }

        .style-table th.sortable:hover {
            color: var(--bloomberg-blue);
        }

        .style-table th.sortable::after {
            content: '↕';
            display: inline-block;
            margin-left: 8px;
            font-size: 0.8em;
            color: #ccc;
        }

        .style-table th.sorted-asc::after {
            content: '↑';
            color: #000000;
        }

        .style-table th.sorted-desc::after {
            content: '↓';
            color: #000000;
        }

        /* Numeric Columns Alignment & Font */
        .style-table th:nth-child(n+2),
        .style-table td:nth-child(n+2) {
            text-align: right;
            font-family: var(--font-mono); /* 使用等宽字体显示数字 */
            font-variant-numeric: tabular-nums; /* 确保数字对齐 */
        }

        /* Sticky first column for mobile/tablet */
        @media (max-width: 1024px) {
            .style-table th:first-child,
            .style-table td:first-child {
                position: sticky;
                left: 0;
                background-color: #ffffff;
                z-index: 10;
                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
            }

            .style-table th:first-child {
                z-index: 20;
                background-color: #ffffff;
            }

            .style-table tbody tr:hover td:first-child {
                background-color: #f8f8f8;
            }
        }
        
        /* Colors */
        .positive {
            color: var(--up-color) !important;
            font-weight: 700;
        }

        .negative {
            color: var(--down-color) !important;
            font-weight: 700;
        }
        
        /* Specific tweaks for small screens */
        @media (max-width: 768px) {
            body {
                font-size: 14px;
            }

            /* Navbar */
            .navbar {
                padding: 0.75rem 1rem;
                flex-wrap: wrap;
                gap: 0.5rem;
            }

            .navbar-brand {
                font-size: 1rem;
                flex: 1;
                min-width: 150px;
            }

            .navbar-menu {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .navbar-item {
                font-size: 0.75rem;
            }

            /* App container */
            .app-container {
                flex-direction: column;
                overflow: visible;
            }

            .main-content {
                height: auto;
                min-height: calc(100vh - 100px);
                padding: 1rem;
                overflow-y: visible;
            }

            .dashboard-grid {
                max-width: 100%;
                padding-bottom: 20px;
            }

            /* Tabs */
            .tabs-header {
                padding: 0;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }

            .tabs-header::-webkit-scrollbar {
                display: none;
            }

            .tab-button {
                padding: 10px 12px;
                font-size: 0.8rem;
                white-space: nowrap;
                flex: 0 0 auto;
                min-width: 80px;
            }

            /* Tables - Enable horizontal scroll */
            .table-container {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                border-radius: 0;
            }

            .style-table {
                font-size: 0.75rem;
                min-width: 100%;
            }

            .style-table th {
                padding: 8px 10px;
                font-size: 0.75rem;
                white-space: nowrap;
            }

            .style-table td {
                padding: 8px 10px;
                font-size: 0.75rem;
            }

            /* Make numeric columns more compact on mobile */
            .style-table th:nth-child(n+4),
            .style-table td:nth-child(n+4) {
                padding: 8px 6px;
                font-size: 0.7rem;
            }

            /* Hide less important columns on very small screens */
            @media (max-width: 480px) {
                .style-table td:nth-child(n+7),
                .style-table th:nth-child(n+7) {
                    display: none;
                }
            }

            /* Loading page adjustments */
            .loading-container {
                padding: 1rem;
            }

            .task-list {
                max-width: 100%;
            }

            .task-item {
                font-size: 0.85rem;
            }
        }

    </style>
    """


def get_javascript_code():
    return r"""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        autoColorize();
    });

    function autoColorize() {
        const cells = document.querySelectorAll('.style-table td');
        cells.forEach(cell => {
            const text = cell.textContent.trim();
            const cleanText = text.replace(/[%,亿万手]/g, '');
            const val = parseFloat(cleanText);

            if (!isNaN(val)) {
                if (text.includes('%') || text.includes('涨跌')) {
                    if (text.includes('-')) {
                        cell.classList.add('negative');
                    } else if (val > 0) {
                        cell.classList.add('positive');
                    }
                } else if (text.startsWith('-')) {
                    cell.classList.add('negative');
                } else if (text.startsWith('+')) {
                    cell.classList.add('positive');
                }
            }
        });
    }

    function sortTable(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const currentSortCol = table.dataset.sortCol;
        const currentSortDir = table.dataset.sortDir || 'asc';
        let direction = 'asc';

        if (currentSortCol == columnIndex) {
            direction = currentSortDir === 'asc' ? 'desc' : 'asc';
        }
        table.dataset.sortCol = columnIndex;
        table.dataset.sortDir = direction;

        rows.sort((a, b) => {
            const aText = a.cells[columnIndex].textContent.trim();
            const bText = b.cells[columnIndex].textContent.trim();
            const valA = parseValue(aText);
            const valB = parseValue(bText);
            let comparison = 0;
            if (valA > valB) {
                comparison = 1;
            } else if (valA < valB) {
                comparison = -1;
            }
            return direction === 'asc' ? comparison : -comparison;
        });

        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));

        table.querySelectorAll('th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        const headerToUpdate = table.querySelectorAll('th')[columnIndex];
        if (headerToUpdate) {
            headerToUpdate.classList.add(direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    }

    function parseValue(val) {
        if (val === 'N/A' || val === '--' || val === '---' || val === '') {
            return -Infinity;
        }
        const cleanedVal = val.replace(/%|亿|万|元\/克|手/g, '').replace(/,/g, '');
        const num = parseFloat(cleanedVal);
        return isNaN(num) ? val.toLowerCase() : num;
    }

    function openTab(evt, tabId) {
        // Hide all tab contents
        const allContents = document.querySelectorAll('.tab-content');
        allContents.forEach(content => {
            content.classList.remove('active');
        });

        // Remove active class from all tab buttons
        const allButtons = document.querySelectorAll('.tab-button');
        allButtons.forEach(button => {
            button.classList.remove('active');
        });

        // Show the clicked tab's content and add active class to the button
        document.getElementById(tabId).classList.add('active');
        evt.currentTarget.classList.add('active');
    }
    </script>
    """
