import os
import json

base_dir = r'c:\Users\ACER\ccms'

# 1. Update views.py
views_path = os.path.join(base_dir, 'core', 'views.py')
with open(views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

new_view = """
@login_required
def daily_report_detail_view(request, report_id):
    import json
    from django.shortcuts import get_object_or_404
    
    report = get_object_or_404(DailyReport, id=report_id)
    
    # 1. Progress Data
    progress_percentage = float(report.progress_percentage) if report.progress_percentage else 0.0
    
    # 2. Work Progress Data
    work_items = report.work_progress.all()
    work_labels = []
    work_target = []
    work_actual = []
    for w in work_items:
        work_labels.append(w.item_description or "Unknown")
        work_target.append(float(w.target_volume) if w.target_volume else 0.0)
        work_actual.append(float(w.actual_volume) if w.actual_volume else 0.0)
        
    # 3. Manpower Data
    manpower_items = report.manpower_usages.all()
    mp_roles = []
    mp_counts = []
    for m in manpower_items:
        mp_roles.append(m.role or "Unknown")
        mp_counts.append(int(m.count) if m.count else 0)
        
    # 4. Equipment Data
    equipment_items = report.equipment_usages.all()
    eq_names = []
    eq_hours = []
    for e in equipment_items:
        eq_names.append(e.equipment_name or "Unknown")
        eq_hours.append(float(e.hours_used) if e.hours_used else 0.0)
        
    chart_data = {
        'progress': progress_percentage,
        'work': {
            'labels': work_labels,
            'target': work_target,
            'actual': work_actual,
        },
        'manpower': {
            'labels': mp_roles,
            'data': mp_counts,
        },
        'equipment': {
            'labels': eq_names,
            'data': eq_hours,
        }
    }
    
    context = {
        'report': report,
        'chart_data': json.dumps(chart_data)
    }
    return render(request, 'core/daily_report_detail.html', context)
"""

if 'def daily_report_detail_view(' not in views_content:
    views_content += "\n" + new_view + "\n"
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views_content)
    print("Added daily_report_detail_view to views.py")
else:
    print("daily_report_detail_view already exists in views.py")


# 2. Update urls.py
urls_path = os.path.join(base_dir, 'core', 'urls.py')
with open(urls_path, 'r', encoding='utf-8') as f:
    urls_content = f.read()

new_url = "    path('daily-report/<int:report_id>/', views.daily_report_detail_view, name='daily_report_detail'),\n"
if 'name=\'daily_report_detail\'' not in urls_content:
    urls_content = urls_content.replace(
        "    path('reports/print/', views.print_report, name='print_report'),\n",
        "    path('reports/print/', views.print_report, name='print_report'),\n" + new_url
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls_content)
    print("Added daily_report_detail to urls.py")
else:
    print("daily_report_detail already exists in urls.py")


# 3. Create daily_report_detail.html
template_path = os.path.join(base_dir, 'templates', 'core', 'daily_report_detail.html')
template_content = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Report Analytics - CCMS</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #0b1121; --card: #151f32; --border: #1e293b; --text: #e2e8f0; --muted: #94a3b8;
            --primary: #3b82f6; --success: #10b981; --warning: #f59e0b; --danger: #ef4444;
        }
        body { margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding-bottom: 40px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        .header h1 { margin: 0; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 12px; }
        .header .badge { background: var(--primary); color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
        .btn { padding: 8px 16px; background: var(--primary); color: #fff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; transition: 0.2s; border: none; cursor: pointer; }
        .btn:hover { opacity: 0.9; }
        .btn-secondary { background: #334155; }
        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .card h2 { margin: 0 0 20px 0; font-size: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .chart-wrapper { position: relative; height: 300px; width: 100%; }
        
        .summary-info { display: flex; gap: 30px; margin-bottom: 30px; }
        .info-item { background: var(--card); padding: 15px 24px; border-radius: 12px; border: 1px solid var(--border); flex: 1; }
        .info-item .label { display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; margin-bottom: 6px; }
        .info-item .val { font-size: 18px; font-weight: bold; color: white; }
    </style>
</head>
<body>

    <div class="header">
        <h1>
            Daily Report Analytics 
            <span class="badge">{{ report.project.name }}</span>
            <span class="badge" style="background:#475569;">{{ report.date|date:"d M Y" }}</span>
        </h1>
        <a href="{% url 'dashboard' %}" class="btn btn-secondary">Back to Dashboard</a>
    </div>

    <div class="container">
        
        <div class="summary-info">
            <div class="info-item">
                <span class="label">Reporter</span>
                <span class="val">{{ report.reporter.get_full_name|default:report.reporter.username }}</span>
            </div>
            <div class="info-item">
                <span class="label">Weather</span>
                <span class="val">{{ report.weather|default:"N/A" }}</span>
            </div>
            <div class="info-item">
                <span class="label">Total Manpower</span>
                <span class="val">{{ report.manpower_count }}</span>
            </div>
            <div class="info-item">
                <span class="label">Status</span>
                <span class="val" style="color:var(--success);">{{ report.status }}</span>
            </div>
        </div>

        <div class="grid">
            
            <!-- 1. Progress Gauge -->
            <div class="card">
                <h2>Progress Hari Ini</h2>
                <div class="chart-wrapper" style="height: 250px;">
                    <canvas id="progressChart"></canvas>
                    <div style="position: absolute; top: 60%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                        <div style="font-size: 36px; font-weight: 800; color: white;" id="progressText">0%</div>
                        <div style="font-size: 12px; color: var(--muted);">Pencapaian</div>
                    </div>
                </div>
            </div>

            <!-- 2. Manpower Donut -->
            <div class="card">
                <h2>Komposisi Tenaga Kerja</h2>
                <div class="chart-wrapper">
                    <canvas id="manpowerChart"></canvas>
                </div>
            </div>

            <!-- 3. Work Progress Horizontal Bar -->
            <div class="card" style="grid-column: span 2;">
                <h2>Progres Pekerjaan Aktual vs Target</h2>
                <div class="chart-wrapper">
                    <canvas id="workChart"></canvas>
                </div>
            </div>

            <!-- 4. Equipment Bar -->
            <div class="card" style="grid-column: span 2;">
                <h2>Jam Kerja Alat Berat</h2>
                <div class="chart-wrapper">
                    <canvas id="equipmentChart"></canvas>
                </div>
            </div>

        </div>
    </div>

    {{ chart_data|json_script:"chart-data" }}
    
    <script>
        const rawData = JSON.parse(document.getElementById('chart-data').textContent);
        
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Inter';
        
        // 1. Progress Gauge (Half Doughnut)
        const progCtx = document.getElementById('progressChart').getContext('2d');
        const progressVal = rawData.progress;
        document.getElementById('progressText').innerText = progressVal + '%';
        
        new Chart(progCtx, {
            type: 'doughnut',
            data: {
                labels: ['Progress', 'Sisa'],
                datasets: [{
                    data: [progressVal, 100 - progressVal],
                    backgroundColor: ['#10b981', '#1e293b'],
                    borderWidth: 0,
                    borderRadius: [10, 0]
                }]
            },
            options: {
                rotation: -90,
                circumference: 180,
                cutout: '80%',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });

        // 2. Manpower Donut
        const mpCtx = document.getElementById('manpowerChart').getContext('2d');
        new Chart(mpCtx, {
            type: 'doughnut',
            data: {
                labels: rawData.manpower.labels,
                datasets: [{
                    data: rawData.manpower.data,
                    backgroundColor: ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4'],
                    borderWidth: 2,
                    borderColor: '#151f32',
                    hoverOffset: 6,
                    borderRadius: 4
                }]
            },
            options: {
                cutout: '70%',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { color: '#e2eaf6' } }
                }
            }
        });

        // 3. Work Progress Horizontal Bar
        const workCtx = document.getElementById('workChart').getContext('2d');
        new Chart(workCtx, {
            type: 'bar',
            data: {
                labels: rawData.work.labels,
                datasets: [
                    {
                        label: 'Target Volume',
                        data: rawData.work.target,
                        backgroundColor: 'rgba(148, 163, 184, 0.2)',
                        borderColor: '#94a3b8',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'Actual Volume',
                        data: rawData.work.actual,
                        backgroundColor: '#3b82f6',
                        borderColor: '#2563eb',
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { color: '#1e293b' } },
                    y: { grid: { display: false }, ticks: { color: '#e2eaf6' } }
                },
                plugins: {
                    legend: { position: 'top', labels: { color: '#e2eaf6' } }
                }
            }
        });

        // 4. Equipment Vertical Bar
        const eqCtx = document.getElementById('equipmentChart').getContext('2d');
        new Chart(eqCtx, {
            type: 'bar',
            data: {
                labels: rawData.equipment.labels,
                datasets: [{
                    label: 'Jam Operasi',
                    data: rawData.equipment.data,
                    backgroundColor: '#8b5cf6',
                    borderRadius: 6,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#e2eaf6' } },
                    y: { grid: { color: '#1e293b' } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    </script>
</body>
</html>"""
with open(template_path, 'w', encoding='utf-8') as f:
    f.write(template_content)
print("Created daily_report_detail.html")
