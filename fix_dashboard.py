import os

file_path = r'c:\Users\ACER\ccms\templates\core\dashboard.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find where the error starts.
# It starts right after:
#                             grid: { color: 'rgba(148,163,184,0.11)', drawBorder: false }
#                         }
#                     }
#                 })
#             });
#                 data: {
#                     labels: data.cost_category?.labels || [],

broken_block = """                            grid: { color: 'rgba(148,163,184,0.11)', drawBorder: false }
                        }
                    }
                })
            });
                data: {
                    labels: data.cost_category?.labels || [],"""

fixed_block = """                            grid: { color: 'rgba(148,163,184,0.11)', drawBorder: false }
                        }
                    }
                })
            });

            // --- Labor Trend Chart ---
            makeChart('laborTrendChart', {
                type: 'bar',
                data: {
                    labels: data.labor?.labels || [],
                    datasets: [{
                        label: 'Workers',
                        data: data.labor?.data || [],
                        backgroundColor: 'rgba(96,165,250,0.85)',
                        borderColor: colors.blue,
                        borderWidth: 1.5,
                        borderRadius: 6,
                        borderSkipped: false,
                        barPercentage: 0.5,
                        hoverBackgroundColor: '#3b82f6'
                    }]
                },
                options: baseOptions({ plugins: { legend: { display: false } } })
            });

            // --- Material Status Doughnut ---
            const matColors = [colors.blue, colors.amber, colors.purple, colors.green, colors.cyan];
            makeChart('materialStatusChart', {
                type: 'doughnut',
                data: {
                    labels: data.material?.labels || [],
                    datasets: [{
                        data: data.material?.data || [],
                        backgroundColor: matColors,
                        borderColor: '#071428',
                        borderWidth: 2,
                        borderRadius: 4,
                        spacing: 3,
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    cutout: '75%',
                    animation: { duration: 600 },
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, boxHeight: 10, padding: 12, font: { size: 11 } } },
                        tooltip: { backgroundColor: '#0a1628', borderColor: 'rgba(59,130,246,0.3)', borderWidth: 1, titleColor: '#e2eaf6', bodyColor: '#94a3b8', padding: 10, cornerRadius: 8 }
                    }
                }
            });

            // --- RFI Status Doughnut ---
            makeChart('rfiStatusChart', {
                type: 'doughnut',
                data: {
                    labels: data.rfi?.labels || [],
                    datasets: [{
                        data: data.rfi?.data || [],
                        backgroundColor: [colors.amber, colors.blue, colors.green, colors.red],
                        borderColor: '#071428',
                        borderWidth: 2,
                        borderRadius: 4,
                        spacing: 3,
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    cutout: '75%',
                    animation: { duration: 600 },
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, boxHeight: 10, padding: 12, font: { size: 11 } } },
                        tooltip: { backgroundColor: '#0a1628', borderColor: 'rgba(59,130,246,0.3)', borderWidth: 1, titleColor: '#e2eaf6', bodyColor: '#94a3b8', padding: 10, cornerRadius: 8 }
                    }
                }
            });

            // --- Cost Category Horizontal Bar ---
            makeChart('costCategoryChart', {
                type: 'bar',
                data: {
                    labels: data.cost_category?.labels || [],"""

if broken_block in content:
    content = content.replace(broken_block, fixed_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Dashboard fixed successfully.")
else:
    print("Could not find the broken block.")
