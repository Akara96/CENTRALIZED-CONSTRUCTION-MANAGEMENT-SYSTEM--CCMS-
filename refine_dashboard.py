import os

file_path = r'c:\Users\ACER\ccms\templates\core\dashboard.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Google Font (Inter)
if 'fonts.googleapis.com' not in content:
    content = content.replace('<title>CCMS Dashboard</title>', '<title>CCMS Dashboard</title>\n    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">')

# 2. Update CSS styles for premium look
css_replacements = {
    'font-family: Arial, Helvetica, sans-serif;': "font-family: 'Inter', sans-serif;",
    '.role { color: #d7e5f5; font-size: 12px; padding: 0 18px 14px; border-bottom: 1px solid rgba(255,255,255,.08); }': '.role { display: none; }',
    '.sidebar {\n            width: 230px;\n            background: #152238;\n            padding: 0 0 16px;\n            height: 100%;\n            overflow-y: auto;\n            flex-shrink: 0;\n        }': '.sidebar {\n            width: 240px;\n            background: #0B162C;\n            padding: 24px 0 16px;\n            height: 100%;\n            overflow-y: auto;\n            flex-shrink: 0;\n            border-right: 1px solid #1a2a40;\n        }',
    '.menu-item {\n            width: 100%;\n            border: 0;\n            background: transparent;\n            color: #eef6ff;\n            text-align: left;\n            padding: 14px 24px;\n            cursor: pointer;\n            font-size: 13px;\n            font-weight: 500;\n            border-left: 3px solid transparent;\n        }': '.menu-item {\n            width: 100%;\n            border: 0;\n            background: transparent;\n            color: #94a3b8;\n            text-align: left;\n            padding: 14px 24px;\n            cursor: pointer;\n            font-size: 14px;\n            font-weight: 600;\n            border-left: 4px solid transparent;\n            transition: all 0.2s;\n        }',
    '.menu-item:hover { background: rgba(255,255,255,0.05); }': '.menu-item:hover { background: rgba(255,255,255,0.05); color: #fff; }',
    '.menu-item.active {\n            background: #1a73e8;\n            color: #fff;\n            font-weight: 700;\n            border-left-color: #60a5fa;\n        }': '.menu-item.active {\n            background: #1d4ed8;\n            color: #ffffff;\n            font-weight: 700;\n            border-left-color: #3b82f6;\n        }',
    'h1 { font-size: 24px; margin: 0; color: #fff; font-weight: 700; letter-spacing: 0; }': 'h1 { font-size: 22px; margin: 0; color: #f8fafc; font-weight: 800; letter-spacing: 0.5px; }',
    '.page-kicker { color: #e2e8f0; font-size: 16px; margin-top: 4px; font-weight: 500; }': '.page-kicker { color: #94a3b8; font-size: 15px; margin-top: 4px; font-weight: 600; }',
    '.card-panel {\n            background: #fff;\n            border-radius: 6px;\n            padding: 16px;\n            margin-bottom: 16px;\n            box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n        }': '.card-panel {\n            background: #fff;\n            border-radius: 8px;\n            padding: 20px;\n            margin-bottom: 16px;\n            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.025);\n            border: 1px solid #f1f5f9;\n        }',
    '.chart-card { background: #fff; border-radius: 6px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); grid-column: span 6; min-height: 320px; }': '.chart-card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.025); grid-column: span 6; min-height: 320px; border: 1px solid #f1f5f9; }',
    'h2, h3 { margin: 0 0 14px; }': 'h2, h3 { margin: 0 0 16px; font-size: 13px; color: #1e293b; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; }',
}

for k, v in css_replacements.items():
    content = content.replace(k, v)

# Update KPI Card styles to match image strictly
kpi_css_old = """        .stat-card.blue { background: #e0f2fe; }
        .stat-card.green { background: #dcfce7; }
        .stat-card.yellow { background: #fef9c3; }
        .stat-card.pink { background: #fee2e2; }
        .stat-card.purple { background: #f3e8ff; }
        .stat-card.cyan { background: #e0f2fe; }
        .stat-card.orange { background: #ffedd5; }
        .stat-card.mint { background: #d1fae5; }
        .stat-icon { font-size: 34px; line-height: 1; }"""

kpi_css_new = """        .stat-card.blue { background: #eff6ff; }
        .stat-card.blue .stat-icon { color: #3b82f6; }
        .stat-card.green { background: #f0fdf4; }
        .stat-card.green .stat-icon { color: #22c55e; }
        .stat-card.yellow { background: #fffbeb; }
        .stat-card.yellow .stat-icon { color: #f59e0b; }
        .stat-card.pink { background: #fef2f2; }
        .stat-card.pink .stat-icon { color: #ef4444; }
        .stat-card.purple { background: #faf5ff; }
        .stat-card.purple .stat-icon { color: #a855f7; }
        .stat-card.cyan { background: #ecfeff; }
        .stat-card.cyan .stat-icon { color: #06b6d4; }
        .stat-card.orange { background: #fff7ed; }
        .stat-card.orange .stat-icon { color: #f97316; }
        .stat-card.mint { background: #ecfdf5; }
        .stat-card.mint .stat-icon { color: #10b981; }
        .stat-icon { font-size: 32px; line-height: 1; opacity: 0.9; }"""

content = content.replace(kpi_css_old, kpi_css_new)

# Update KPI HTML to remove inline styles and use CSS for cleaner look
import re

def replace_kpi(match):
    color = match.group(1)
    label = match.group(2)
    icon = match.group(3)
    val = match.group(4)
    note = match.group(5)
    return f'''                    <div class="stat-card {color}" style="border-radius:8px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); border:1px solid #f1f5f9; position:relative; overflow:hidden;">
                        <span class="label" style="align-self:flex-start; color:#475569; font-size:10px; font-weight:800; letter-spacing:0.5px;">{label}</span>
                        <div style="display:flex; justify-content:space-between; align-items:center; width:100%; margin: 8px 0;">
                            <span class="stat-icon">{icon}</span>
                            <span class="value" style="font-size:28px; font-weight:900; color:#0f172a;">{val}</span>
                        </div>
                        <span class="mini-note" style="align-self:flex-end; color:#64748b; font-size:11px; font-weight:500;">{note}</span>
                    </div>'''

kpi_pattern = r'<div class="stat-card (\w+)"><span class="label" style="[^"]*">([^<]+)</span>\s*<div style="[^"]*">\s*<span class="stat-icon" style="[^"]*">([^<]+)</span>\s*<span class="value" style="[^"]*">(.+?)</span>\s*</div>\s*<span class="mini-note" style="[^"]*">([^<]+)</span>\s*</div>'
content = re.sub(kpi_pattern, replace_kpi, content)

# Additional fix for the "Budget Used" which has a span inside the span.value
content = content.replace(
    '<span class="value" style="font-size:28px; font-weight:900; color:#0f172a;"><span id="kpiBudgetUsed">0%</span></span>',
    '<span class="value" id="kpiBudgetUsed" style="font-size:28px; font-weight:900; color:#0f172a;">0%</span>'
)
content = content.replace(
    '<span class="value" style="font-size:28px; font-weight:900; color:#0f172a;"><span id="kpiLaborToday">0</span></span>',
    '<span class="value" id="kpiLaborToday" style="font-size:28px; font-weight:900; color:#0f172a;">0</span>'
)

# Chart fixes to match Premium Look
content = content.replace(
    "backgroundColor: 'rgba(47,115,216,.10)'",
    "backgroundColor: 'rgba(59, 130, 246, 0.15)', fill: true"
)
content = content.replace(
    "backgroundColor: 'rgba(66,185,72,.10)'",
    "backgroundColor: 'rgba(34, 197, 94, 0.15)', fill: true"
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Refined successfully")
