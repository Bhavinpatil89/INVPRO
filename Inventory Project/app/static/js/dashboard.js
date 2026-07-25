// dashboard.js - Client Side Rendering for Dashboard

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadRecentBills();
});

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const stats = await response.json();

        document.getElementById('totalRevenue').textContent = '₹' + stats.total_revenue.toLocaleString('en-IN', { minimumFractionDigits: 2 });
        document.getElementById('totalProfit').textContent = '₹' + stats.total_profit.toLocaleString('en-IN', { minimumFractionDigits: 2 });
        document.getElementById('totalBills').textContent = stats.total_bills;
        document.getElementById('stockValue').textContent = '₹' + stats.stock_value.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadRecentBills() {
    const tbody = document.getElementById('recentBillsBody');

    try {
        const response = await fetch('/api/dashboard/recent-bills');
        const bills = await response.json();

        tbody.innerHTML = '';

        if (bills.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center py-4 text-muted">
                        No transactions yet. Start selling!
                    </td>
                </tr>
            `;
            return;
        }

        bills.forEach(bill => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="fw-medium">${bill.bill_number}</td>
                <td class="text-muted">${new Date(bill.date).toLocaleDateString('en-IN')}</td>
                <td class="text-end fw-bold">₹${bill.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                <td class="text-center">
                    <span class="badge bg-success">Paid</span>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading bills:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-danger py-4">
                    Failed to load transactions
                </td>
            </tr>
        `;
    }
}
