import os
import re

file_path = r'c:\Users\ACER\ccms\templates\core\dashboard.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Layout and CSS
css_replacements = {
    # Layout and Sidebar
    '.layout { display: flex; min-height: 100vh; }': '.layout { display: flex; flex-direction: column; min-height: 100vh; }',
    '.sidebar {\n            width: 210px;\n            background: linear-gradient(180deg, #07182d 0%, #0c2b45 100%);\n            border-right: 0;\n            padding: 0 0 16px;\n            position: sticky;\n            top: 0;\n            height: 100vh;\n            overflow-y: auto;\n            box-shadow: 8px 0 22px rgba(7, 24, 45, 0.18);\n        }': '.sidebar {\n            width: 230px;\n            background: #152238;\n            padding: 0 0 16px;\n            height: 100%;\n            overflow-y: auto;\n            flex-shrink: 0;\n        }',
    # Brand and Topbar
    '.brand {\n            font-weight: 900;\n            font-size: 20px;\n            margin: 0;\n            padding: 14px 18px 4px;\n            color: #fff;\n            letter-spacing: 0;\n        }': '.brand { display: none; }',
    '.topbar {\n            display: flex;\n            justify-content: space-between;\n            align-items: center;\n            gap: 16px;\n            margin-bottom: 0;\n            padding: 14px 22px;\n            background: #061426;\n            border: 0;\n            border-radius: 0;\n            min-height: 92px;\n        }': '.topbar {\n            display: flex;\n            justify-content: space-between;\n            align-items: center;\n            gap: 16px;\n            padding: 14px 24px;\n            background: #0B192C;\n            width: 100%;\n            min-height: 70px;\n        }',
    '.content { flex: 1; padding: 0; min-width: 0; background: #f4f6f8; }': '.content { flex: 1; padding: 16px 24px; min-width: 0; background: #eef2f6; overflow-y: auto; }',
    # Menu Item
    '.menu-item {\n            width: 100%;\n            border: 0;\n            background: transparent;\n            color: #eef6ff;\n            text-align: left;\n            padding: 12px 18px;\n            border-radius: 0;\n            cursor: pointer;\n            margin-bottom: 0;\n            font-size: 13px;\n            font-weight: 600;\n        }': '.menu-item {\n            width: 100%;\n            border: 0;\n            background: transparent;\n            color: #eef6ff;\n            text-align: left;\n            padding: 14px 24px;\n            cursor: pointer;\n            font-size: 13px;\n            font-weight: 500;\n            border-left: 3px solid transparent;\n        }',
    '.menu-item:hover, .menu-item.active {\n            background: linear-gradient(90deg, #0877ee, #0566d4);\n            color: #fff;\n        }': '.menu-item:hover { background: rgba(255,255,255,0.05); }\n        .menu-item.active {\n            background: #1a73e8;\n            color: #fff;\n            font-weight: 700;\n            border-left-color: #60a5fa;\n        }',
    # Stat Card
    '.stat-card {\n            background: #fff;\n            border: 1px solid #edf0f4;\n            border-radius: 3px;\n            padding: 12px;\n            min-height: 126px;\n            text-align: center;\n            display: flex;\n            flex-direction: column;\n            align-items: center;\n            justify-content: center;\n            gap: 6px;\n        }': '.stat-card {\n            background: #fff;\n            border-radius: 6px;\n            padding: 16px;\n            min-height: 126px;\n            text-align: center;\n            display: flex;\n            flex-direction: column;\n            align-items: center;\n            justify-content: center;\n            gap: 6px;\n            box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n        }',
    # Grid classes
    '.dashboard-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }': '.dashboard-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }',
    '.chart-card { grid-column: span 6; min-height: 320px; }': '.chart-card { background: #fff; border-radius: 6px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); grid-column: span 6; min-height: 320px; }',
    '.chart-card.large { grid-column: span 8; }': '.chart-card.half { grid-column: span 6; }',
    '.chart-card.side { grid-column: span 4; }': '.chart-card.side { grid-column: span 6; }',
    '.chart-card.quarter { grid-column: span 3; }': '.chart-card.quarter { grid-column: span 3; min-height: 280px; }',
    '.chart-card.third { grid-column: span 4; }': '.chart-card.third { grid-column: span 4; min-height: 280px; }',
    '.stat-card.blue { background: #e8f2ff; }': '.stat-card.blue { background: #e0f2fe; }',
    '.stat-card.green { background: #ecf9df; }': '.stat-card.green { background: #dcfce7; }',
    '.stat-card.yellow { background: #fff4d9; }': '.stat-card.yellow { background: #fef9c3; }',
    '.stat-card.pink { background: #ffe5ea; }': '.stat-card.pink { background: #fee2e2; }',
    '.stat-card.purple { background: #f0e9fb; }': '.stat-card.purple { background: #f3e8ff; }',
    '.stat-card.cyan { background: #e6f4ff; }': '.stat-card.cyan { background: #e0f2fe; }',
    '.stat-card.orange { background: #fff0d8; }': '.stat-card.orange { background: #ffedd5; }',
    '.stat-card.mint { background: #dff6ee; }': '.stat-card.mint { background: #d1fae5; }',
    # Topbar text
    'h1 { font-size: 28px; margin: 0; color: #fff; font-weight: 900; letter-spacing: 0; }': 'h1 { font-size: 24px; margin: 0; color: #fff; font-weight: 700; letter-spacing: 0; }',
    '.page-kicker { color: #fff; font-size: 21px; margin-top: 6px; font-weight: 700; }': '.page-kicker { color: #e2e8f0; font-size: 16px; margin-top: 4px; font-weight: 500; }',
    '.company-mark { color:#fff; text-align:center; font-size:11px; line-height:1.1; font-weight:800; }': '.company-mark { color:#fff; text-align:center; font-size:12px; line-height:1.2; font-weight:700; letter-spacing:1px; }',
    '.company-mark .building { font-size:34px; display:block; line-height:1; }': '.company-mark .building { font-size:28px; display:block; line-height:1.1; margin-bottom: 2px; }',
    # Card Panel
    '.card-panel {\n            background: var(--panel);\n            border: 1px solid #edf0f4;\n            border-radius: 2px;\n            padding: 14px;\n            margin-bottom: 12px;\n            box-shadow: 0 1px 4px rgba(16, 24, 40, 0.04);\n        }': '.card-panel {\n            background: #fff;\n            border-radius: 6px;\n            padding: 16px;\n            margin-bottom: 16px;\n            box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n        }',
}

for k, v in css_replacements.items():
    content = content.replace(k, v)

# HTML Structure Replacements
# Move topbar out of content and wrap sidebar+content in main-container
html_old = """    <div class="layout">
        <aside class="sidebar">"""
html_new = """    <div class="layout">
        <div class="topbar">
            <div>
                <h1 id="header-page-title">CENTRALIZED CONSTRUCTION MANAGEMENT SYSTEM (CCMS)</h1>
                <div class="page-kicker">Executive Dashboard</div>
            </div>
            <div class="topbar-controls">
                <select id="topProjectSelect" class="form-control" onchange="syncDashboardProject(this.value)">
                    <option value="">All Project</option>
                    {% for p in raw_projects %}
                    <option value="{{ p.id }}">{{ p.name }}</option>
                    {% endfor %}
                </select>
                <input type="date" class="form-control" value="2026-06-10">
                <div class="company-mark"><span class="building">▥</span>CONSTRUCTION<br>COMPANY</div>
            </div>
        </div>
        <div style="display:flex; flex:1; overflow:hidden;">
        <aside class="sidebar">"""
content = content.replace(html_old, html_new)

# Remove the old topbar from inside content
old_topbar = """            <div class="topbar">
                <div>
                    <h1 id="header-page-title">CENTRALIZED CONSTRUCTION MANAGEMENT SYSTEM (CCMS)</h1>
                    <div class="page-kicker">Executive Dashboard</div>
                </div>
                <div class="topbar-controls">
                    <select id="topProjectSelect" class="form-control" onchange="syncDashboardProject(this.value)">
                        <option value="">All Project</option>
                        {% for p in raw_projects %}
                        <option value="{{ p.id }}">{{ p.name }}</option>
                        {% endfor %}
                    </select>
                    <input type="date" class="form-control" value="2026-06-10">
                    <div class="company-mark"><span class="building">▥</span>CONSTRUCTION<br>COMPANY</div>
                </div>
            </div>"""
content = content.replace(old_topbar, "")

# Close the new flex wrapper at the bottom before </div> </body>
content = content.replace('        </main>\n    </div>\n\n    {{ dashboard_chart_data', '        </main>\n        </div>\n    </div>\n\n    {{ dashboard_chart_data')

# Update Dashboard Grid sizes
# Change `large` and `side` to half
content = content.replace('<div class="card-panel chart-card large">', '<div class="card-panel chart-card half">')
content = content.replace('<div class="card-panel chart-card side">', '<div class="card-panel chart-card half">')

# Reorder KPI icons to match the image layout (Label top, Value/Icon middle, Sub bottom)
def format_kpi(label, icon, value_code, mini_note, color):
    return f'''                    <div class="stat-card {color}">
                        <span class="label" style="align-self:flex-start; color:#334155; font-size:11px;">{label}</span>
                        <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                            <span class="stat-icon" style="font-size:28px; color:#475569;">{icon}</span>
                            <span class="value" style="font-size:32px;">{value_code}</span>
                        </div>
                        <span class="mini-note" style="align-self:flex-end;">{mini_note}</span>
                    </div>'''

kpi_grid_old = """                <div class="grid kpi-grid">
                    <div class="stat-card blue"><span class="label">Total Project</span><span class="stat-icon">▥</span><span class="value">{{ stats.total_projects }}</span><span class="mini-note">Project</span></div>
                    <div class="stat-card green"><span class="label">Active Project</span><span class="stat-icon">♜</span><span class="value">{{ stats.active_projects }}</span><span class="mini-note">Project</span></div>
                    <div class="stat-card yellow"><span class="label">Overall Progress</span><span class="stat-icon">▟</span><span class="value">{{ stats.avg_progress|floatformat:2 }}%</span><span class="mini-note">Average</span></div>
                    <div class="stat-card pink"><span class="label">Budget Used</span><span class="stat-icon">$</span><span id="kpiBudgetUsed" class="value">0%</span><span class="mini-note">of Total Budget</span></div>
                    <div class="stat-card purple"><span class="label">Total Labor Today</span><span class="stat-icon">●●●</span><span id="kpiLaborToday" class="value">0</span><span class="mini-note">Workers</span></div>
                    <div class="stat-card cyan"><span class="label">Pending Material Request</span><span class="stat-icon">◈</span><span class="value">{{ stats.material_requests_count }}</span><span class="mini-note">Request</span></div>
                    <div class="stat-card orange"><span class="label">Open RFI</span><span class="stat-icon">▤</span><span class="value">{{ stats.open_rfi_count }}</span><span class="mini-note">RFI</span></div>
                    <div class="stat-card mint"><span class="label">Open NCR / Issue</span><span class="stat-icon">⚠</span><span class="value">{{ stats.open_ncr_count }}</span><span class="mini-note">Issue</span></div>
                </div>"""

kpi_grid_new = f"""                <div class="grid kpi-grid">
{format_kpi('TOTAL PROJECT', '🏢', '{{ stats.total_projects }}', 'Project', 'blue')}
{format_kpi('ACTIVE PROJECT', '🏗️', '{{ stats.active_projects }}', 'Project', 'green')}
{format_kpi('OVERALL PROGRESS', '📈', '{{ stats.avg_progress|floatformat:2 }}%', 'Average', 'yellow')}
{format_kpi('BUDGET USED', '💰', '<span id="kpiBudgetUsed">0%</span>', 'of Total Budget', 'pink')}
{format_kpi('TOTAL LABOR TODAY', '👷', '<span id="kpiLaborToday">0</span>', 'Workers', 'purple')}
{format_kpi('PENDING MATERIAL REQUEST', '📦', '{{ stats.material_requests_count }}', 'Request', 'cyan')}
{format_kpi('OPEN RFI', '📋', '{{ stats.open_rfi_count }}', 'RFI', 'orange')}
{format_kpi('OPEN NCR / ISSUE', '⚠️', '{{ stats.open_ncr_count }}', 'Issue', 'mint')}
                </div>"""

content = content.replace(kpi_grid_old, kpi_grid_new)


# Reorder Bottom Charts
# Change the grid structure
charts_old = """                <div class="dashboard-grid">
                    <div class="card-panel chart-card half">
                        <h3>Project Progress Overview</h3>
                        <div class="table-responsive">
                            <table class="custom-table">
                                <thead><tr><th>Project</th><th>Planned Progress</th><th>Actual Progress</th><th>Progress %</th><th>Status</th></tr></thead>
                                <tbody>
                                    {% for p in projects %}
                                    <tr>
                                        <td>{{ p.project.project_code|default:"PRJ" }} - {{ p.project.name|truncatechars:24 }}</td>
                                        <td>{{ p.overall_progress|floatformat:2 }}%</td>
                                        <td>{{ p.overall_progress|floatformat:2 }}%</td>
                                        <td>
                                            <div style="display:flex; align-items:center; gap:10px;">
                                                <div class="progress-bar-bg" style="width:120px;"><div class="progress-bar-fill" data-width="{{ p.overall_progress }}%"></div></div>
                                                <span>{{ p.overall_progress|floatformat:2 }}%</span>
                                            </div>
                                        </td>
                                        <td><span class="status-badge">{% if p.overall_progress >= 50 %}On Track{% else %}Behind{% endif %}</span></td>
                                    </tr>
                                    {% empty %}
                                    <tr><td colspan="5">Belum ada project.</td></tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card-panel chart-card half">
                        <h3>Overall Progress Curve (Average)</h3>
                        <div class="chart-wrap"><canvas id="progressCurveChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card third">
                        <h3>Labor Trend (Last 7 Days)</h3>
                        <div class="chart-wrap"><canvas id="laborTrendChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card third">
                        <h3>Material Request Status</h3>
                        <div class="chart-wrap"><canvas id="materialStatusChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card third">
                        <h3>RFI Status</h3>
                        <div class="chart-wrap"><canvas id="rfiStatusChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>Cost Performance</h3>
                        <div class="chart-wrap" style="height:190px;"><canvas id="costPerformanceChart"></canvas></div>
                        <div style="text-align:center; margin-top:8px;"><strong>Budget Used</strong> <span id="costUsed" class="value" style="font-size:28px; color:#1f65c8;">0%</span></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>Cost Trend / S-Curve</h3>
                        <div class="chart-wrap"><canvas id="costCurveChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>Top 5 Cost Category (Actual)</h3>
                        <div class="chart-wrap"><canvas id="costCategoryChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>Safety Summary (MTD)</h3>
                        <div class="safety-row"><span>🔴 Total Incident</span><strong>{{ stats.incident_count }}</strong></div>
                        <div class="safety-row"><span>⚠ Near Miss</span><strong>0</strong></div>
                        <div class="safety-row"><span>♨ Unsafe Act</span><strong>0</strong></div>
                        <div class="safety-row"><span>△ Unsafe Condition</span><strong>0</strong></div>
                        <div style="text-align:center; margin-top:18px; color:#143c75; font-size:20px;"><strong>Total</strong> <span style="color:#e3342f; font-size:30px; font-weight:900;">{{ stats.incident_count }}</span></div>
                    </div>
                </div>"""

charts_new = """                <div class="dashboard-grid">
                    <div class="card-panel chart-card half">
                        <h3>PROJECT PROGRESS OVERVIEW</h3>
                        <div class="table-responsive">
                            <table class="custom-table">
                                <thead><tr><th>Project</th><th>Planned Progress</th><th>Actual Progress</th><th>Progress %</th><th>Status</th></tr></thead>
                                <tbody>
                                    {% for p in projects %}
                                    <tr>
                                        <td>{{ p.project.project_code|default:"PRJ" }} - {{ p.project.name|truncatechars:24 }}</td>
                                        <td>{{ p.overall_progress|floatformat:2 }}%</td>
                                        <td>{{ p.overall_progress|floatformat:2 }}%</td>
                                        <td>
                                            <div style="display:flex; align-items:center; gap:10px;">
                                                <div class="progress-bar-bg" style="width:80px;"><div class="progress-bar-fill" data-width="{{ p.overall_progress }}%"></div></div>
                                                <span>{{ p.overall_progress|floatformat:2 }}%</span>
                                            </div>
                                        </td>
                                        <td><span class="status-badge" style="{% if p.overall_progress < 50 %}background:#fee2e2; color:#ef4444;{% endif %}">{% if p.overall_progress >= 50 %}On Track{% else %}Behind{% endif %}</span></td>
                                    </tr>
                                    {% empty %}
                                    <tr><td colspan="5">Belum ada project.</td></tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card-panel chart-card half">
                        <h3>OVERALL PROGRESS CURVE (AVERAGE)</h3>
                        <div class="chart-wrap"><canvas id="progressCurveChart"></canvas></div>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <div class="card-panel chart-card third">
                        <h3>LABOR TREND (LAST 7 DAYS)</h3>
                        <div class="chart-wrap"><canvas id="laborTrendChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card third">
                        <h3>MATERIAL REQUEST STATUS</h3>
                        <div class="chart-wrap"><canvas id="materialStatusChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card third">
                        <h3>RFI STATUS</h3>
                        <div class="chart-wrap"><canvas id="rfiStatusChart"></canvas></div>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <div class="card-panel chart-card quarter">
                        <h3>COST PERFORMANCE</h3>
                        <div class="chart-wrap" style="height:190px;"><canvas id="costPerformanceChart"></canvas></div>
                        <div style="text-align:center; margin-top:8px;"><strong>Budget Used</strong> <span id="costUsed" class="value" style="font-size:28px; color:#1d4ed8;">0%</span></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>COST TREND (S-CURVE)</h3>
                        <div class="chart-wrap"><canvas id="costCurveChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>TOP 5 COST CATEGORY (ACTUAL)</h3>
                        <div class="chart-wrap"><canvas id="costCategoryChart"></canvas></div>
                    </div>
                    <div class="card-panel chart-card quarter">
                        <h3>SAFETY SUMMARY (MTD)</h3>
                        <div class="safety-row"><span>🔴 Total Incident</span><strong>{{ stats.incident_count }}</strong></div>
                        <div class="safety-row"><span>⚠️ Near Miss</span><strong>0</strong></div>
                        <div class="safety-row"><span>🔧 Unsafe Act</span><strong>0</strong></div>
                        <div class="safety-row"><span>🚧 Unsafe Condition</span><strong>0</strong></div>
                        <div style="text-align:center; margin-top:24px; color:#1e293b; font-size:18px;"><strong>Total</strong> <span style="color:#ef4444; font-size:28px; font-weight:800; float:right;">{{ stats.incident_count }}</span></div>
                    </div>
                </div>"""

# Replace 'large' and 'side' to 'half' for charts_old string since we replaced them earlier in content
charts_old = charts_old.replace('<div class="card-panel chart-card large">', '<div class="card-panel chart-card half">')
charts_old = charts_old.replace('<div class="card-panel chart-card side">', '<div class="card-panel chart-card half">')

content = content.replace(charts_old, charts_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")
