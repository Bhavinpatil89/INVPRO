// categories.js - High-Performance Inventory Accordion Logic

document.addEventListener('DOMContentLoaded', () => {
    initInventoryHub();
});

function toggleCreationPanel() {
    const panel = document.getElementById('creationPanel');
    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        panel.classList.add('hidden');
    }
}

async function initInventoryHub() {
    const grid = document.getElementById('categoriesGrid');
    const searchInput = document.getElementById('inventorySearch');

    try {
        // Parallel fetching for performance
        const [catRes, prodRes] = await Promise.all([
            fetch('/inventory/api/categories'),
            fetch('/inventory/api/products')
        ]);

        const categories = await catRes.json();
        const products = await prodRes.json();

        renderInventory(categories, products);

        // Search logic
        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            const filteredCats = categories.filter(c =>
                c.name.toLowerCase().includes(term) ||
                products.some(p => p.category_id === c.id && p.name.toLowerCase().includes(term))
            );
            renderInventory(filteredCats, products, term);
        });

    } catch (error) {
        console.error('Inventory Hub Error:', error);
        grid.innerHTML = `<div class="col-span-full py-20 text-center text-red-500 font-bold bg-red-50 dark:bg-red-900/10 rounded-3xl border border-red-100 italic">Critical: Connection to master inventory lost.</div>`;
    }
}

function renderInventory(categories, products, searchTerm = '') {
    const grid = document.getElementById('categoriesGrid');
    grid.innerHTML = '';

    if (categories.length === 0) {
        grid.innerHTML = `<div class="py-20 text-center text-slate-400 italic font-medium">No inventory clusters found.</div>`;
        return;
    }

    categories.forEach(cat => {
        const catProducts = products.filter(p => p.category_id === cat.id);
        const totalQty = catProducts.reduce((sum, p) => sum + p.quantity, 0);
        const totalProfit = catProducts.reduce((sum, p) => sum + (p.selling_price - p.cost_price) * p.quantity, 0);

        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-all duration-300';

        // Check if this category matches search or has matching products
        const shouldExpand = searchTerm.length > 0;

        card.innerHTML = `
            <div class="px-6 py-5 cursor-pointer flex items-center justify-between group" onclick="toggleAccordion(this)">
                <div class="flex items-center gap-5">
                    <div class="w-12 h-12 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold group-hover:scale-110 transition-transform">
                        <i class="bi bi-stack text-xl"></i>
                    </div>
                    <div>
                        <h3 class="text-lg font-black text-slate-900 dark:text-white leading-tight">${cat.name}</h3>
                        <div class="flex items-center gap-3 mt-1">
                            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest"><i class="bi bi-box me-1"></i> ${catProducts.length} SKUs</span>
                            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest"><i class="bi bi-layers me-1"></i> ${totalQty} Total Units</span>
                            ${cat.tax_rate ? `<span class="badge-indigo text-[9px]"><i class="bi bi-percent me-1"></i> ${cat.tax_rate}% Tax</span>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="flex items-center gap-6">
                    <div class="hidden sm:flex flex-col items-end">
                        <p class="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] mb-0.5 whitespace-nowrap">Net Yield</p>
                        <span class="text-sm font-black ${totalProfit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600'}">
                            ₹${totalProfit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                    </div>
                    <div class="flex items-center gap-2">
                         <div class="dropdown" onclick="event.stopPropagation()">
                            <button class="p-2 text-slate-300 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-xl transition-all" data-bs-toggle="dropdown">
                                <i class="bi bi-three-dots"></i>
                            </button>
                            <ul class="dropdown-menu border-0 shadow-2xl rounded-2xl p-2">
                                <li><button class="dropdown-item rounded-xl py-2 font-bold" onclick="editCategory(${cat.id}, '${cat.name}', '${cat.tax_rate || ''}')"><i class="bi bi-pencil me-2"></i> Rename / Tax</button></li>
                                <li><button class="dropdown-item rounded-xl py-2 font-bold text-red-500" onclick="deleteCategory(${cat.id}, '${cat.name}')"><i class="bi bi-trash3 me-2"></i> Delete</button></li>
                            </ul>
                        </div>
                        <i class="bi bi-chevron-down text-slate-300 transition-transform duration-300 accordion-arrow ${shouldExpand ? 'rotate-180' : ''}"></i>
                    </div>
                </div>
            </div>
            
            <div class="accordion-content ${shouldExpand ? 'expanded' : ''} bg-slate-50/50 dark:bg-slate-950/20 border-t border-slate-50 dark:border-slate-800">
                <div class="p-4 space-y-3">
                    ${catProducts.length > 0 ? catProducts.map(p => renderProductRow(p)).join('') : `
                        <div class="py-6 text-center text-slate-400 text-xs italic">This cluster is currently void of assets.</div>
                    `}
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderProductRow(p) {
    const profit = (p.selling_price - p.cost_price) * p.quantity;
    const isLow = p.quantity <= 5;

    return `
        <div class="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:border-indigo-600/20">
            <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-xl ${isLow ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-slate-50 text-slate-400 dark:bg-indigo-900/10 dark:text-indigo-400'} flex items-center justify-center font-bold text-xs ring-1 ring-inset ${isLow ? 'ring-red-600/10' : 'ring-slate-900/5'}">
                    SKU
                </div>
                <div>
                    <h4 class="text-sm font-black text-slate-900 dark:text-white mb-0.5 underline decoration-indigo-600/10 decoration-2 underline-offset-4">${p.name}</h4>
                    <div class="flex items-center gap-2">
                         <span class="${isLow ? 'badge-red' : 'badge-indigo'} text-[9px]">${p.quantity} Units</span>
                         <span class="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Cost: ₹${p.cost_price.toFixed(2)}</span>
                    </div>
                </div>
            </div>
            
            <div class="flex items-center justify-between sm:justify-end gap-8 border-t sm:border-t-0 border-slate-50 pt-3 sm:pt-0">
                <div class="text-right">
                    <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Mkt Price</p>
                    <p class="text-xs font-black text-slate-900 dark:text-white">₹${p.selling_price.toFixed(2)}</p>
                </div>
                <div class="text-right">
                    <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Asset Profit</p>
                    <p class="text-xs font-black ${profit >= 0 ? 'text-emerald-600' : 'text-red-600'}">
                        ${profit >= 0 ? '+' : ''}₹${profit.toFixed(2)}
                    </p>
                </div>
            </div>
        </div>
    `;
}

function toggleAccordion(header) {
    const card = header.parentElement;
    const content = card.querySelector('.accordion-content');
    const arrow = header.querySelector('.accordion-arrow');

    content.classList.toggle('expanded');
    arrow.classList.toggle('rotate-180');
}

// Fallbacks for cat management (from previous version)
function editCategory(id, name, tax) {
    const editNameInput = document.getElementById('edit_name');
    const editTaxInput = document.getElementById('edit_tax');
    const editForm = document.getElementById('editForm');
    if (editNameInput) editNameInput.value = name;
    if (editTaxInput) editTaxInput.value = tax;
    if (editForm) editForm.action = `/inventory/categories/edit/${id}`;
    new bootstrap.Modal(document.getElementById('editModal')).show();
}

function deleteCategory(id, name) {
    if (confirm(`CRITICAL ACKNOWLEDGMENT: Purging "${name}" will permanently dissociate products. Proceed?`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/inventory/categories/delete/${id}`;
        document.body.appendChild(form);
        form.submit();
    }
}
