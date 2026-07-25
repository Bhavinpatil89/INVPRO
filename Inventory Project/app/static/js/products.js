// products.js - Product Inventory Management Logic

let allProducts = [];
let GLOBAL_CTX = null;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/session-context');
        GLOBAL_CTX = await res.json();

        updatePageMetadata();
        renderActionButtons();
        loadProducts();
        loadCategories();
        setupEventListeners();
    } catch (e) {
        console.error("Context Load Failed:", e);
    }
});

function updatePageMetadata() {
    const storeLabel = document.getElementById('ctx-store-label');
    const storeTitle = document.getElementById('title-store-name');
    const badgeContainer = document.getElementById('filter-badge-container');

    if (storeLabel) storeLabel.textContent = `${GLOBAL_CTX.store_name} View`;
    if (storeTitle) storeTitle.textContent = GLOBAL_CTX.store_name;

    if (typeof FILTER_TYPE !== 'undefined' && FILTER_TYPE === 'low') {
        badgeContainer.innerHTML = `
            <span class="bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-widest border border-orange-200 dark:border-orange-800 flex items-center gap-1">
                <i class="bi bi-filter"></i> Low Stock
                <a href="/products" class="hover:text-orange-800 dark:hover:text-orange-200"><i class="bi bi-x-circle-fill"></i></a>
            </span>`;
    }
}

function renderActionButtons() {
    const importBtn = document.getElementById('importBtn');
    const exportBtn = document.getElementById('exportBtn');

    if (['business_admin', 'main_owner', 'branch_admin'].includes(GLOBAL_CTX.role)) {
        if (importBtn) importBtn.classList.remove('hidden');
        if (exportBtn) exportBtn.classList.remove('hidden');
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');

    searchInput.addEventListener('input', filterProducts);
    categoryFilter.addEventListener('change', filterProducts);
}

function loadProducts() {
    const grid = document.getElementById('productsGrid');
    const url = (typeof FILTER_TYPE !== 'undefined' && FILTER_TYPE === 'low') ? '/inventory/api/products?filter=low' : '/inventory/api/products';

    fetch(url)
        .then(response => response.json())
        .then(data => {
            allProducts = data;
            renderProducts(allProducts);
        })
        .catch(error => {
            console.error('Error:', error);
            grid.innerHTML = `<div class="col-span-full py-20 text-center text-red-500 font-bold">Failed to load products. Check your connection.</div>`;
        });
}

function renderProducts(products) {
    const grid = document.getElementById('productsGrid');
    grid.innerHTML = '';

    if (products.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-20 text-center text-slate-400 italic font-medium">No matching products found.</div>`;
        return;
    }

    products.forEach(p => {
        let healthLabel, barColor, healthPercent;

        // Stock health calculation
        const maxStock = 50; // Assume 50 is healthy max for visualization
        healthPercent = Math.min((p.quantity / maxStock) * 100, 100);

        if (p.quantity <= 0) {
            healthLabel = 'OUT OF STOCK';
            barColor = 'bg-red-500';
            healthPercent = 0;
        } else if (p.quantity <= 10) {
            healthLabel = 'LOW STOCK';
            barColor = 'bg-amber-500';
        } else {
            healthLabel = 'HEALTHY';
            barColor = 'bg-emerald-500';
        }

        const profit = p.selling_price - p.cost_price;
        const margin = p.selling_price > 0 ? ((profit / p.selling_price) * 100).toFixed(1) : 0;

        // Velocity classification (based on quantity - simple heuristic)
        let velocity_class = 'MODERATE';
        if (p.quantity > 30) velocity_class = 'SLOW-MOVING';
        else if (p.quantity <= 5 && p.quantity > 0) velocity_class = 'FAST-MOVING';
        else if (p.quantity === 0) velocity_class = 'DEAD STOCK';

        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-slate-900 rounded-[1.5rem] border border-slate-200 dark:border-slate-800 p-6 shadow-sm card-hover-lift flex flex-col justify-between group';

        let actionButtons = '';
        if (['business_admin', 'main_owner', 'branch_admin'].includes(GLOBAL_CTX.role)) {
            actionButtons = `
                <button onclick="editProduct(${p.id})" class="p-1.5 text-indigo-600 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all sm:tooltip-trigger" title="Edit Stock"><i class="bi bi-pencil-square"></i></button>
                <button onclick="deleteProduct(${p.id})" class="p-1.5 text-red-500 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all" title="Remove Product"><i class="bi bi-trash3"></i></button>
            `;
        }

        card.innerHTML = `
            <div>
                <div class="flex justify-between items-start mb-4">
                    <div class="px-2.5 py-1 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-400 dark:text-slate-500 text-[9px] font-black tracking-widest uppercase border border-slate-100 dark:border-slate-800">
                        ID-${p.id.toString().padStart(5, '0')}
                    </div>
                    <div class="flex gap-1 border border-slate-100 dark:border-slate-800 rounded-lg bg-slate-50/50 dark:bg-slate-800/50 p-0.5">
                        ${actionButtons}
                    </div>
                </div>
                
                <h3 class="text-sm font-black text-slate-900 dark:text-white leading-snug mb-1 group-hover:text-indigo-600 transition-colors">${p.name}</h3>
                <div class="flex items-center gap-2 mb-4">
                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">${p.category_name}</p>
                    <span class="badge-indigo text-[9px]"><i class="bi bi-percent mr-1"></i>${p.effective_tax}% Tax</span>
                    ${p.global_product_id ? '<span class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-[8px] font-black text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800 uppercase tracking-widest"><i class="bi bi-link-45deg"></i> Global Link</span>' : ''}
                </div>
                
                <div class="grid grid-cols-2 gap-3 mb-6">
                    <div class="p-3 bg-slate-50 dark:bg-slate-950/50 rounded-xl border border-slate-100 dark:border-slate-800">
                        <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5 whitespace-nowrap">Cost Price</p>
                        <p class="text-xs font-black text-slate-900 dark:text-slate-300">₹${p.cost_price.toFixed(2)}</p>
                    </div>
                    <div class="p-3 bg-indigo-50/50 dark:bg-indigo-900/10 rounded-xl border border-indigo-100/50 dark:border-indigo-900/20">
                        <p class="text-[9px] font-black text-indigo-600/60 dark:text-indigo-400 uppercase tracking-widest mb-0.5 whitespace-nowrap">Selling Price</p>
                        <p class="text-xs font-black text-indigo-600 dark:text-indigo-400">₹${p.selling_price.toFixed(2)}</p>
                    </div>
                </div>
            </div>

            <!-- Enhanced Stock Visualizer -->
            <div class="mb-6">
                <div class="flex justify-between items-end mb-2">
                    <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest">${healthLabel}</p>
                    <span class="text-[11px] font-black ${p.quantity <= 5 ? 'text-red-500 animate-pulse' : 'text-slate-700 dark:text-slate-300'}">${p.quantity} Units</span>
                </div>
                <div class="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div class="${barColor} h-full transition-all duration-1000" style="width: ${healthPercent}%"></div>
                </div>
            </div>

            <div class="pt-5 border-t border-slate-50 dark:border-slate-800 flex items-center justify-between">
                <div class="text-left">
                    <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Profit Margin</p>
                    <span class="text-xs font-black ${profit >= 0 ? 'text-emerald-600' : 'text-red-600'}">
                        ${profit >= 0 ? '+' : ''}${margin}%
                    </span>
                </div>
                <div class="text-right">
                    <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Velocity</p>
                    <span class="text-[10px] font-black ${velocity_class === 'FAST-MOVING' ? 'text-indigo-600' : velocity_class === 'DEAD STOCK' ? 'text-slate-400 opacity-50' : 'text-slate-600'}">
                        ${velocity_class}
                    </span>
                </div>
            </div>
        `;

        if (p.quantity <= 5 && p.quantity > 0) {
            card.classList.add('ring-2', 'ring-amber-500/20');
        }
        grid.appendChild(card);
    });
}

function filterProducts() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const catId = document.getElementById('categoryFilter').value;

    const filtered = allProducts.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(searchTerm);
        const matchesCat = !catId || p.category_id == catId;
        return matchesSearch && matchesCat;
    });

    renderProducts(filtered);
}

function loadCategories() {
    fetch('/inventory/api/categories')
        .then(res => res.json())
        .then(data => {
            const selects = [document.getElementById('addCategorySelect'), document.getElementById('editCategorySelect')];
            const filter = document.getElementById('categoryFilter');

            const optionsHTML = data.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

            selects.forEach(s => {
                if (s) s.innerHTML = '<option value="">Select Category...</option>' + optionsHTML;
            });

            if (filter) {
                filter.innerHTML = '<option value="">All Categories</option>' + optionsHTML;
            }
        });
}

async function submitEditProduct(e) {
    if (e) e.preventDefault();
    const id = document.getElementById('editProductId').value;
    const data = {
        quantity: parseInt(document.getElementById('editQuantity').value),
        cost_price: parseFloat(document.getElementById('editCostPrice').value),
        selling_price: parseFloat(document.getElementById('editSellingPrice').value)
    };

    // Note: Name and Category are kept readonly for Branch Managers to ensure data integrity
    try {
        const res = await fetch(`/inventory/products/edit/${id}`, {
            method: 'POST', // Using POST for compatibility with the blueprint's form-based edit
            body: new URLSearchParams(new FormData(e.target))
        });

        if (res.ok) {
            location.reload();
        } else {
            const result = await res.json();
            alert('Update Failed: ' + (result.error || result.message));
        }
    } catch (e) {
        console.error(e);
        alert('Connection Error');
    }
}

function editProduct(id) {
    const product = allProducts.find(p => p.id == id);
    if (!product) return;

    document.getElementById('editProductId').value = product.id;
    document.getElementById('editName').value = product.name;
    document.getElementById('editCategorySelect').value = product.category_id;
    document.getElementById('editQuantity').value = product.quantity;
    document.getElementById('editCostPrice').value = product.cost_price || 0;
    document.getElementById('editSellingPrice').value = product.selling_price;

    // Wire up the form for AJAX
    const form = document.getElementById('editProductForm');
    form.onsubmit = submitEditProduct;

    new bootstrap.Modal(document.getElementById('editModal')).show();
}

async function confirmDeleteProduct() {
    const id = document.getElementById('deleteProductId').value;
    try {
        const res = await fetch(`/inventory/products/delete/${id}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' } });
        const result = await res.json();
        if (result.success) location.reload();
        else alert('Delete Failed: ' + (result.error || result.message));
    } catch (e) {
        console.error(e);
        alert('Connection Error');
    }
}





function deleteProduct(id) {
    let idInput = document.getElementById('deleteProductId');
    if (!idInput) {
        idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.id = 'deleteProductId';
        document.body.appendChild(idInput);
    }
    idInput.value = id;

    const delForm = document.getElementById('deleteProductForm');
    if (delForm) {
        delForm.onsubmit = (e) => {
            e.preventDefault();
            confirmDeleteProduct();
        };
    }

    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

function exportProducts() {
    window.location.href = '/inventory/products/export';
}

