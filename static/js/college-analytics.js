document.addEventListener("DOMContentLoaded", function () {
    const pageDataUrl = document.getElementById("collegeAnalyticsPage").dataset.apiUrl;
    const timeFilter = document.getElementById("timePeriodFilter");
    
    // Helper to safely parse JSON scripts
    const parseData = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            console.error("Error parsing JSON data for " + id, e);
            return null;
        }
    };

    let charts = {};

    // Chart Options Base
    const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.9)',
                padding: 12,
                titleFont: { size: 13 },
                bodyFont: { size: 14, weight: 'bold' },
                cornerRadius: 8,
                displayColors: false
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: {
                    color: '#f3f4f6',
                    drawBorder: false,
                },
                ticks: { color: '#6b7280', precision: 0 }
            },
            x: {
                grid: { display: false, drawBorder: false },
                ticks: { color: '#6b7280', maxRotation: 45, minRotation: 45 }
            }
        }
    };

    // Render Source Donut Chart
    const renderSourceDonut = (sources) => {
        const ctx = document.getElementById("sourceDonutChart")?.getContext("2d");
        if (!ctx) return;
        
        if (charts.sources) charts.sources.destroy();

        if (!sources || !sources.segments || sources.segments.length === 0) {
            // Show empty state inside canvas container
            ctx.canvas.parentElement.innerHTML = '<div class="icd-empty-state"><i class="bi bi-pie-chart"></i><h3>No Source Data</h3><p>Applications have not been received yet.</p></div>';
            return;
        }

        const labels = sources.segments.map(s => s.label);
        const data = sources.segments.map(s => s.count);
        const bgColors = sources.segments.map(s => {
            const toneMap = { 'primary': '#3b82f6', 'secondary': '#a855f7', 'accent': '#ef4444', 'tertiary': '#10b981' };
            return toneMap[s.tone] || '#c4b5fd';
        });

        charts.sources = new Chart(ctx, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: bgColors, borderWidth: 0, hoverOffset: 4 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8, padding: 20 } },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` ${context.label}: ${context.raw} apps`
                        }
                    }
                }
            }
        });
    };

    // Render Trend Charts
    const renderTrendCharts = (trends) => {
        if (!trends) return;
        
        const labels = trends.labels || [];
        
        // 1. Applications Line Chart
        const appCtx = document.getElementById("applicationsLineChart")?.getContext("2d");
        if (appCtx) {
            if (charts.appsLine) charts.appsLine.destroy();
            
            // Generate gradient
            let gradient = appCtx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(59, 130, 246, 0.2)');
            gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');
            
            charts.appsLine = new Chart(appCtx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Applications',
                        data: trends.applications || [],
                        borderColor: '#3b82f6',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#3b82f6',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: { ...baseOptions }
            });
        }

        // 2. Interview Bar Chart
        const intCtx = document.getElementById("interviewBarChart")?.getContext("2d");
        if (intCtx) {
            if (charts.interviews) charts.interviews.destroy();
            charts.interviews = new Chart(intCtx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Interviews',
                        data: trends.interviews || [],
                        backgroundColor: '#a855f7',
                        borderRadius: 4,
                        barPercentage: 0.6
                    }]
                },
                options: { ...baseOptions }
            });
        }

        // 3. Hiring Area Chart
        const hireCtx = document.getElementById("hiringAreaChart")?.getContext("2d");
        if (hireCtx) {
            if (charts.hiring) charts.hiring.destroy();
            let gradient = hireCtx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.2)');
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');

            charts.hiring = new Chart(hireCtx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Hired Candidates',
                        data: trends.hiring || [],
                        borderColor: '#10b981',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#10b981',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: { ...baseOptions }
            });
        }
    };

    // Render Department Bar Chart
    const renderDeptChart = (deptData) => {
        const ctx = document.getElementById("departmentBarChart")?.getContext("2d");
        if (!ctx) return;
        if (charts.department) charts.department.destroy();

        if (!deptData || deptData.length === 0) {
            ctx.canvas.parentElement.innerHTML = '<div class="icd-empty-state"><i class="bi bi-building"></i><h3>No Hiring Data</h3><p>No candidates have joined yet.</p></div>';
            return;
        }

        const labels = deptData.map(d => d.label);
        const data = deptData.map(d => d.value);

        charts.department = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Joined',
                    data,
                    backgroundColor: '#6366f1',
                    borderRadius: 4,
                }]
            },
            options: {
                ...baseOptions,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, grid: { color: '#f3f4f6' }, ticks: { precision: 0 } },
                    y: { grid: { display: false } }
                }
            }
        });
    };

    // Update KPI UI
    const updateKPIs = (stats) => {
        if (!stats) return;
        stats.forEach(stat => {
            const el = document.getElementById(`kpi-${stat.key}`);
            if (el) el.textContent = stat.value;
        });
    };

    // Update Funnel UI
    const updateFunnel = (funnelData) => {
        const container = document.getElementById("funnelContainer");
        if (!container || !funnelData) return;
        
        container.innerHTML = funnelData.map(step => `
            <div class="icd-funnel-step">
                <div class="icd-funnel-label">${step.label}</div>
                <div class="icd-funnel-bar-wrap">
                    <div class="icd-funnel-bar" style="width: ${step.pct}%"></div>
                </div>
                <div class="icd-funnel-value">${step.value}</div>
            </div>
        `).join("");
    };

    // Fetch and update data
    const fetchAnalytics = async (period) => {
        if (!pageDataUrl) return;
        
        try {
            // Option to show loading state on charts
            const response = await fetch(`${pageDataUrl}?analytics_period=${period}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });
            const result = await response.json();
            
            if (result.success && result.data) {
                const data = result.data;
                updateKPIs(data.stats);
                updateFunnel(data.funnel);
                renderSourceDonut(data.application_sources);
                renderTrendCharts(data.trends);
                renderDeptChart(data.department_hiring);
                // Vacancy table data update omitted for brevity - would re-render tbody rows
            }
        } catch (error) {
            console.error("Failed to load analytics data", error);
        }
    };

    // Event Listeners
    if (timeFilter) {
        timeFilter.addEventListener("change", (e) => {
            fetchAnalytics(e.target.value);
        });
    }

    // Vacancy Table Search/Sort
    const initTableLogic = () => {
        const searchInput = document.getElementById("vacancySearch");
        const tableBody = document.getElementById("vacancyTableBody");
        const thSorts = document.querySelectorAll("#vacancyPerformanceTable th[data-sort]");
        
        if (!searchInput || !tableBody) return;

        // Search
        searchInput.addEventListener("input", (e) => {
            const term = e.target.value.toLowerCase();
            const rows = tableBody.querySelectorAll("tr[data-title]");
            rows.forEach(row => {
                const title = row.getAttribute("data-title");
                if (title.includes(term)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });

        // Sort
        let currentSort = { key: 'applications', desc: true };
        thSorts.forEach(th => {
            th.addEventListener("click", () => {
                const key = th.dataset.sort;
                if (currentSort.key === key) {
                    currentSort.desc = !currentSort.desc;
                } else {
                    currentSort.key = key;
                    currentSort.desc = key !== 'title'; // default string to asc, number to desc
                }
                
                // Update icons
                thSorts.forEach(el => {
                    const icon = el.querySelector('i');
                    if(icon) {
                        icon.className = 'bi bi-arrow-down-up ms-1 text-muted';
                    }
                });
                const activeIcon = th.querySelector('i');
                if (activeIcon) {
                    activeIcon.className = currentSort.desc ? 'bi bi-arrow-down ms-1 text-primary' : 'bi bi-arrow-up ms-1 text-primary';
                }

                // Sort DOM rows
                const rows = Array.from(tableBody.querySelectorAll("tr[data-title]"));
                rows.sort((a, b) => {
                    let valA = a.dataset[key];
                    let valB = b.dataset[key];
                    
                    if (key !== 'title') {
                        valA = parseInt(valA, 10) || 0;
                        valB = parseInt(valB, 10) || 0;
                    }

                    if (valA < valB) return currentSort.desc ? 1 : -1;
                    if (valA > valB) return currentSort.desc ? -1 : 1;
                    return 0;
                });
                
                tableBody.append(...rows);
            });
        });
    };

    // Initial Load
    const sources = parseData("initSourcesData");
    const trends = parseData("initTrendsData");
    const dept = parseData("initDepartmentData");
    
    renderSourceDonut(sources);
    renderTrendCharts(trends);
    renderDeptChart(dept);
    initTableLogic();
});
