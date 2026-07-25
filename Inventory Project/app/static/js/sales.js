// sales.js - Enterprise Financial Logging & Resolution

let salesChartInstance = null;
let taxChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    loadSalesData();
});

function filterSalesByTime() {
    loadSalesData();
}

function exportSales() {
    const filter = document.getElementById('salesTimeFilter').value;
    window.location.href = `/sales/export?filter=${filter}`;
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        // SQLite returns "YYYY-MM-DD HH:MM:SS" (UTC). 
        // Converting to "YYYY-MM-DDTHH:MM:SSZ" ensures JS treats it as UTC.
        const normalizedDate = dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T') + 'Z';
        const utcDate = new Date(normalizedDate);
        if (isNaN(utcDate.getTime())) return dateStr;

        return utcDate.toLocaleString('en-IN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (e) {
        console.error('Date parsing failed:', e);
        return dateStr;
    }
}

async function loadSalesData() {
    const filter = document.getElementById('salesTimeFilter').value;
    const tbody = document.getElementById('salesTableBody');

    // 1. Load Table and KPI Data
    try {
        const response = await fetch(`/sales/api/history?filter=${filter}`);
        const bills = await response.json();

        tbody.innerHTML = '';
        if (!bills || bills.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-32 text-center text-slate-400 italic font-medium">No sales found for this period.</td></tr>`;
            updateKPIs({ revenue: 0, profit: 0, tax: 0, transactions: 0 });
            return;
        }

        let runningRevenue = 0;
        let runningProfit = 0;
        let runningTax = 0;

        bills.forEach(bill => {
            runningRevenue += bill.total_amount || 0;
            runningProfit += bill.total_profit || 0;
            runningTax += bill.tax_amount || 0;

            const row = document.createElement('tr');
            row.className = 'group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer';
            row.onclick = () => viewBillResolution(bill.id, bill.bill_number, bill.subtotal_amount, bill.tax_amount, bill.total_amount, bill.creator_name);

            row.innerHTML = `
                <td class="px-8 py-5">
                    <div class="flex flex-col">
                        <span class="font-black text-slate-900 dark:text-white uppercase text-xs tracking-widest">${bill.bill_number}</span>
                        <span class="text-[9px] font-black text-slate-400 uppercase tracking-tighter mt-0.5">ID: ${bill.id.toString().padStart(4, '0')}</span>
                    </div>
                </td>
                <td class="px-8 py-5 text-slate-500 dark:text-slate-400 font-medium text-xs">
                    ${formatDateTime(bill.date)}
                </td>
                <td class="px-8 py-5">
                    <div class="flex items-center gap-2">
                        <div class="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-[10px] font-black text-indigo-600">
                            ${(bill.creator_name || 'U')[0].toUpperCase()}
                        </div>
                        <span class="text-xs font-bold text-slate-600 dark:text-slate-400">${bill.creator_name || 'Unknown'}</span>
                    </div>
                </td>
                <td class="px-8 py-5 text-center">
                    <span class="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-black uppercase tracking-widest ring-1 ring-indigo-600/10">
                        ${bill.item_count || '0'} SKU
                    </span>
                </td>
                <td class="px-8 py-5 text-right font-black text-slate-900 dark:text-white text-sm tracking-tighter">
                    ₹${(bill.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td class="px-8 py-5 text-right">
                    <div class="flex justify-end items-center gap-2">
                         <span class="badge-green">SETTLED</span>
                         <i class="bi bi-chevron-right text-slate-300 group-hover:text-indigo-600 group-hover:translate-x-1 transition-all"></i>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        updateKPIs({
            revenue: runningRevenue,
            profit: runningProfit,
            tax: runningTax,
            transactions: bills.length
        });

    } catch (e) {
        console.error('Ledger Error:', e);
        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-32 text-center text-red-500 font-bold uppercase tracking-widest text-[10px]">Failed to sync Ledger.</td></tr>`;
    }

    // 2. Load Charts
    loadCharts(filter);
}

function updateKPIs(data) {
    document.getElementById('totalSalesCount').textContent = data.transactions;
    document.getElementById('totalRevenueSum').textContent = `₹${(data.revenue || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('totalProfitSum').textContent = `₹${(data.profit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('totalTaxSum').textContent = `₹${(data.tax || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
}

async function loadCharts(filter) {
    try {
        const response = await fetch(`/sales/api/charts?filter=${filter}`);
        const data = await response.json();

        renderRevenueTrend(data);
        renderTaxTrend(data);

    } catch (e) {
        console.error('Chart Error:', e);
    }
}

function renderRevenueTrend(data) {
    const ctx = document.getElementById('salesChartContainer');
    ctx.innerHTML = '<canvas id="revenueChart"></canvas>';

    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#1e293b' : '#f1f5f9';

    if (salesChartInstance) salesChartInstance.destroy();

    if (!data.labels || data.labels.length === 0) {
        ctx.innerHTML = '<div class="flex items-center justify-center h-full text-slate-400 font-bold uppercase text-[10px] tracking-widest">No sales trend data available</div>';
        return;
    }

    ctx.innerHTML = '<canvas id="revenueChart"></canvas>';

    salesChartInstance = new Chart(document.getElementById('revenueChart'), {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Revenue',
                data: data.revenue,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#4f46e5'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: textColor, font: { weight: 'bold', size: 10 } } },
                y: { grid: { color: gridColor }, ticks: { color: textColor, font: { weight: 'bold', size: 10 } } }
            }
        }
    });
}

function renderTaxTrend(data) {
    const ctx = document.getElementById('taxChartContainer');
    ctx.innerHTML = '<canvas id="taxChart"></canvas>';

    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#1e293b' : '#f1f5f9';

    if (taxChartInstance) taxChartInstance.destroy();

    taxChartInstance = new Chart(document.getElementById('taxChart'), {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Tax Collection',
                data: data.tax,
                backgroundColor: '#ef4444',
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: textColor, font: { weight: 'bold', size: 10 } } },
                y: { grid: { color: gridColor }, ticks: { color: textColor, font: { weight: 'bold', size: 10 } } }
            }
        }
    });
}

async function viewBillResolution(id, billNum, subtotal, tax, total, creator) {
    const modal = new bootstrap.Modal(document.getElementById('billModal'));

    document.getElementById('modalBillNumber').textContent = billNum;
    document.getElementById('modalSubtotal').textContent = `₹${subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('modalTax').textContent = `+₹${tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('modalTotal').textContent = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    const creatorElement = document.getElementById('modalCreator');
    if (creatorElement) {
        creatorElement.textContent = creator || 'Unknown';
    }

    const listContainer = document.getElementById('modalItemsList');
    listContainer.innerHTML = '<div class="text-center py-4 animate-spin"><i class="bi bi-arrow-repeat text-indigo-600 text-2xl"></i></div>';

    modal.show();

    try {
        const response = await fetch(`/sales/api/bill/${id}`);
        const items = await response.json();

        listContainer.innerHTML = items.map(item => `
            <div class="flex justify-between items-center group/item">
                <div class="flex flex-col">
                    <span class="text-sm font-black text-slate-800 dark:text-slate-200 uppercase tracking-tighter">${item.product_name}</span>
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">${item.quantity} units @ ₹${item.price_at_sale.toLocaleString()}</span>
                </div>
                <div class="text-right">
                    <span class="text-xs font-black text-slate-900 dark:text-white tracking-widest">₹${(item.quantity * item.price_at_sale).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error('Bill Detail Error:', e);
        listContainer.innerHTML = '<p class="text-center text-red-500 text-[10px] font-black uppercase">Failed to load line items.</p>';
    }
}
