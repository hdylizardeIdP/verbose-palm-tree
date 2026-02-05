/* ── Schwab Investment Dashboard JS ─────────────────────────── */

// ── Utilities ────────────────────────────────────────────────

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value);
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
}

function pnlClass(value) {
    return value >= 0 ? 'text-profit' : 'text-loss';
}

function timeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + 'm ago';
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return hours + 'h ago';
    return date.toLocaleDateString();
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const id = 'toast-' + Date.now();
    const bgClass = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-primary',
    }[type] || 'bg-primary';

    const html = `
        <div id="${id}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, { delay: 4000 });
    toast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

async function apiFetch(url, options = {}) {
    try {
        const resp = await fetch(url, options);
        const data = await resp.json();
        if (data.status === 'error') {
            throw new Error(data.message || 'Unknown error');
        }
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('show');
}

// ── Last Updated ─────────────────────────────────────────────

function updateTimestamp() {
    const el = document.getElementById('last-updated');
    if (el) {
        el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
    }
}

// ── Global Refresh ───────────────────────────────────────────

function refreshData() {
    // Each page defines its own loadData function
    if (typeof loadData === 'function') {
        loadData();
        updateTimestamp();
        showToast('Data refreshed', 'success');
    }
}

// ── Dashboard Page ───────────────────────────────────────────

let allocationChart = null;

async function loadDashboardData() {
    // Load account info
    try {
        const info = await apiFetch('/api/account-info');
        const bal = info.balances || {};

        // Update stat cards
        setStatValue('stat-portfolio', formatCurrency(info.totalValue || 0));
        setStatValue('stat-cash', formatCurrency(bal.cashAvailableForTrading || 0));
        setStatValue('stat-buying-power', formatCurrency(bal.buyingPower || 0));
        setStatValue('stat-positions', info.positionCount || 0);

        // Allocation chart
        if (info.allocation && Object.keys(info.allocation).length > 0) {
            renderAllocationChart(info.allocation);
        }
    } catch (e) {
        console.error('Failed to load account info:', e);
    }

    // Load positions for top-holdings table
    try {
        const posData = await apiFetch('/api/positions');
        renderTopPositions(posData.data || []);
        if (posData.summary) {
            const s = posData.summary;
            setStatChange('stat-portfolio', s.totalPnl, s.totalPnlPct);
        }
    } catch (e) {
        console.error('Failed to load positions:', e);
    }

    // Load recent activity
    try {
        const act = await apiFetch('/api/activity?limit=5');
        renderRecentActivity(act.data || []);
    } catch (e) {
        console.error('Failed to load activity:', e);
    }

    updateTimestamp();
}

function setStatValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function setStatChange(id, pnl, pnlPct) {
    const el = document.getElementById(id + '-change');
    if (!el) return;
    const cls = pnl >= 0 ? 'text-profit' : 'text-loss';
    el.className = 'stat-change ' + cls;
    el.textContent = formatCurrency(pnl) + ' (' + formatPercent(pnlPct) + ')';
}

function renderAllocationChart(allocation) {
    const ctx = document.getElementById('allocationChart');
    if (!ctx) return;

    const labels = Object.keys(allocation);
    const values = Object.values(allocation);
    const colors = generateColors(labels.length);

    if (allocationChart) {
        allocationChart.data.labels = labels;
        allocationChart.data.datasets[0].data = values;
        allocationChart.data.datasets[0].backgroundColor = colors;
        allocationChart.update();
    } else {
        allocationChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: 'rgba(255,255,255,0.7)',
                            padding: 12,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                            font: { size: 12 },
                            generateLabels: function(chart) {
                                const data = chart.data;
                                const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                return data.labels.map((label, i) => {
                                    const value = data.datasets[0].data[i];
                                    const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return {
                                        text: label + '  ' + pct + '%',
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i,
                                        pointStyle: 'circle',
                                    };
                                });
                            },
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ' + formatCurrency(ctx.raw);
                            },
                        },
                    },
                },
            },
        });
    }
}

function renderTopPositions(positions) {
    const tbody = document.getElementById('top-positions-body');
    if (!tbody) return;

    // Sort by market value descending
    const sorted = [...positions].sort((a, b) => b.marketValue - a.marketValue);

    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No positions</td></tr>';
        return;
    }

    tbody.innerHTML = sorted.map(p => `
        <tr>
            <td><strong>${p.symbol}</strong></td>
            <td class="text-end">${p.quantity}</td>
            <td class="text-end">${formatCurrency(p.avgPrice)}</td>
            <td class="text-end">${formatCurrency(p.marketValue)}</td>
            <td class="text-end ${pnlClass(p.pnl)}">
                ${formatCurrency(p.pnl)} (${formatPercent(p.pnlPct)})
            </td>
        </tr>
    `).join('');
}

function renderRecentActivity(items) {
    const container = document.getElementById('recent-activity');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-3">No recent activity</div>';
        return;
    }

    container.innerHTML = items.map(a => `
        <div class="activity-item">
            <div class="activity-badge ${a.status}"></div>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between">
                    <strong class="small">${a.action}</strong>
                    <span class="activity-time">${timeAgo(a.timestamp)}</span>
                </div>
                <div class="small text-muted">${a.details}</div>
            </div>
        </div>
    `).join('');
}

// ── Positions Page ───────────────────────────────────────────

async function loadPositionsData() {
    try {
        const data = await apiFetch('/api/positions');
        renderPositionsTable(data.data || []);
        if (data.summary) {
            const s = data.summary;
            document.getElementById('positions-summary').innerHTML = `
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Total Value</div>
                        <div class="stat-value">${formatCurrency(s.totalValue)}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Total Cost</div>
                        <div class="stat-value">${formatCurrency(s.totalCost)}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Total P/L</div>
                        <div class="stat-value ${pnlClass(s.totalPnl)}">${formatCurrency(s.totalPnl)}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Total Return</div>
                        <div class="stat-value ${pnlClass(s.totalPnlPct)}">${formatPercent(s.totalPnlPct)}</div>
                    </div>
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to load positions:', e);
    }
    updateTimestamp();
}

function renderPositionsTable(positions) {
    const tbody = document.getElementById('positions-table-body');
    if (!tbody) return;

    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No positions found</td></tr>';
        return;
    }

    const sorted = [...positions].sort((a, b) => b.marketValue - a.marketValue);
    const total = sorted.reduce((sum, p) => sum + p.marketValue, 0);

    tbody.innerHTML = sorted.map(p => {
        const weight = total > 0 ? ((p.marketValue / total) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td><strong>${p.symbol}</strong> <small class="text-muted">${p.assetType}</small></td>
                <td class="text-end">${p.quantity}</td>
                <td class="text-end">${formatCurrency(p.avgPrice)}</td>
                <td class="text-end">${formatCurrency(p.costBasis)}</td>
                <td class="text-end">${formatCurrency(p.marketValue)}</td>
                <td class="text-end ${pnlClass(p.pnl)}">${formatCurrency(p.pnl)}</td>
                <td class="text-end ${pnlClass(p.pnlPct)}">${formatPercent(p.pnlPct)}</td>
                <td class="text-end">${weight}%</td>
            </tr>
        `;
    }).join('');
}

// ── Strategy Execution ───────────────────────────────────────

async function executeStrategy(strategyName, endpoint, payload) {
    const btn = document.getElementById('btn-' + strategyName);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Running...';
    }

    try {
        const data = await apiFetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const mode = data.dryRun ? 'Dry Run' : 'Live';
        showToast(`${strategyName} (${mode}) completed`, data.dryRun ? 'warning' : 'success');
        showStrategyResults(strategyName, data.results || [], data.dryRun);
        return data;
    } catch (e) {
        showToast(`${strategyName} failed: ${e.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = getButtonLabel(strategyName);
        }
    }
}

function getButtonLabel(name) {
    const labels = {
        DCA: '<i class="bi bi-play-fill me-1"></i>Run DCA',
        DRIP: '<i class="bi bi-play-fill me-1"></i>Run DRIP',
        Rebalance: '<i class="bi bi-play-fill me-1"></i>Rebalance',
        Opportunistic: '<i class="bi bi-play-fill me-1"></i>Scan & Buy',
        'Covered Calls': '<i class="bi bi-play-fill me-1"></i>Sell Calls',
        'Protective Puts': '<i class="bi bi-play-fill me-1"></i>Buy Puts',
    };
    return labels[name] || '<i class="bi bi-play-fill me-1"></i>Execute';
}

function showStrategyResults(name, results, dryRun) {
    const container = document.getElementById('strategy-results');
    if (!container) return;

    const badge = dryRun
        ? '<span class="dry-run-badge">DRY RUN</span>'
        : '<span class="live-badge">LIVE</span>';

    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="card-panel mt-3">
                <div class="panel-header">
                    <h6>${name} Results ${badge}</h6>
                </div>
                <div class="panel-body text-center text-muted py-3">
                    No results - nothing to execute
                </div>
            </div>
        `;
        return;
    }

    // Build a results table dynamically based on the keys
    const keys = Object.keys(results[0]);
    const headers = keys.map(k => `<th>${k}</th>`).join('');
    const rows = results.map(r => {
        const cells = keys.map(k => {
            let val = r[k];
            if (typeof val === 'number') {
                if (k.toLowerCase().includes('price') || k.toLowerCase().includes('amount') ||
                    k.toLowerCase().includes('value') || k.toLowerCase().includes('premium') ||
                    k.toLowerCase().includes('cost')) {
                    val = formatCurrency(val);
                } else if (k.toLowerCase().includes('dip') || k.toLowerCase().includes('pct')) {
                    val = (val * 100).toFixed(2) + '%';
                }
            }
            if (k === 'status') {
                const cls = val === 'success' ? 'text-profit' : (val === 'error' ? 'text-loss' : 'text-warning');
                return `<td class="${cls}">${val}</td>`;
            }
            return `<td>${val}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');

    container.innerHTML = `
        <div class="card-panel mt-3">
            <div class="panel-header">
                <h6>${name} Results ${badge}</h6>
            </div>
            <div class="panel-body p-0">
                <div class="table-responsive">
                    <table class="table table-dashboard mb-0">
                        <thead><tr>${headers}</tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// ── Activity Page ────────────────────────────────────────────

async function loadActivityData() {
    try {
        const data = await apiFetch('/api/activity?limit=100');
        renderActivityList(data.data || []);
    } catch (e) {
        console.error('Failed to load activity:', e);
    }
    updateTimestamp();
}

function renderActivityList(items) {
    const container = document.getElementById('activity-list');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No activity recorded yet</div>';
        return;
    }

    container.innerHTML = items.map(a => `
        <div class="activity-item">
            <div class="activity-badge ${a.status}"></div>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between">
                    <strong class="small">${a.action}</strong>
                    <span class="activity-time">${timeAgo(a.timestamp)}</span>
                </div>
                <div class="small text-muted">${a.details}</div>
            </div>
        </div>
    `).join('');
}

// ── Settings Page ────────────────────────────────────────────

async function loadSettingsData() {
    try {
        const data = await apiFetch('/api/config');
        renderSettings(data.data || {});
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    updateTimestamp();
}

function renderSettings(cfg) {
    const container = document.getElementById('settings-content');
    if (!container) return;

    function enabledBadge(val) {
        return val
            ? '<span class="badge bg-success">Enabled</span>'
            : '<span class="badge bg-secondary">Disabled</span>';
    }

    function configRow(key, value) {
        return `<div class="config-item"><span class="config-key">${key}</span><span class="config-value">${value}</span></div>`;
    }

    const dca = cfg.dca || {};
    const drip = cfg.drip || {};
    const rebal = cfg.rebalance || {};
    const opp = cfg.opportunistic || {};
    const opt = cfg.options || {};
    const log = cfg.logging || {};

    let allocHtml = '';
    if (rebal.targetAllocation) {
        allocHtml = Object.entries(rebal.targetAllocation)
            .map(([sym, pct]) => `<span class="badge bg-primary me-1">${sym}: ${(pct * 100).toFixed(0)}%</span>`)
            .join(' ');
    }

    container.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Dollar Cost Averaging</h6>${enabledBadge(dca.enabled)}</div>
                    <div class="panel-body">
                        ${configRow('Amount', formatCurrency(dca.amount || 0))}
                        ${configRow('Frequency', dca.frequency || '-')}
                        ${configRow('Symbols', (dca.symbols || []).join(', '))}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Dividend Reinvestment</h6>${enabledBadge(drip.enabled)}</div>
                    <div class="panel-body">
                        ${configRow('Status', drip.enabled ? 'Auto-reinvest dividends' : 'Manual reinvestment')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Portfolio Rebalancing</h6>${enabledBadge(rebal.enabled)}</div>
                    <div class="panel-body">
                        ${configRow('Threshold', ((rebal.threshold || 0) * 100).toFixed(1) + '%')}
                        ${configRow('Target Allocation', allocHtml || '-')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Opportunistic Buying</h6>${enabledBadge(opp.enabled)}</div>
                    <div class="panel-body">
                        ${configRow('Dip Threshold', ((opp.dipThreshold || 0) * 100).toFixed(1) + '%')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Options Trading</h6>${enabledBadge(opt.enabled)}</div>
                    <div class="panel-body">
                        ${configRow('Covered Calls', opt.enabled ? 'Available' : 'Disabled')}
                        ${configRow('Protective Puts', opt.enabled ? 'Available' : 'Disabled')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card-panel">
                    <div class="panel-header"><h6>Logging</h6></div>
                    <div class="panel-body">
                        ${configRow('Level', log.level || 'INFO')}
                        ${configRow('File', log.file || '-')}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── Chart Color Generator ────────────────────────────────────

function generateColors(count) {
    const palette = [
        '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
        '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0',
        '#6c757d', '#4a86c8', '#e83e8c', '#17a2b8', '#28a745',
    ];
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(palette[i % palette.length]);
    }
    return colors;
}
