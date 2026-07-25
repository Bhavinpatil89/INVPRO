// billing.js - Strategic POS Transaction Layer

// Audio Feedback for POS
const successSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
const errorSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2955/2955-preview.mp3');

let cart = [];
let allProducts = [];

function playSuccessSound() {
    successSound.play().catch(e => console.log('Audio playback failed'));
}

function playErrorSound() {
    errorSound.play().catch(e => console.log('Audio playback failed'));
}

function generateWhatsAppReceipt(billNumber, items, subtotal, tax, total, customerName) {
    const storeName = 'Inventory Pro';
    let message = `*Receipt from ${storeName}*\n\n`;
    message += `Customer: ${customerName || 'Valued Guest'}\n`;
    message += `Bill: ${billNumber}\n`;
    message += `Date: ${new Date().toLocaleDateString('en-IN')}\n\n`;
    message += `*Items:*\n`;

    items.forEach(item => {
        const lineTotal = (item.price * item.qty * (1 + item.tax_rate / 100)).toFixed(2);
        message += `\u2022 ${item.qty}x ${item.name} - \u20b9${lineTotal}\n`;
    });

    message += `\n*Subtotal:* \u20b9${subtotal.toFixed(2)}\n`;
    message += `*Tax:* \u20b9${tax.toFixed(2)}\n`;
    message += `*Total:* \u20b9${total.toFixed(2)}\n\n`;
    message += `Thank you for your business!`;

    return `https://wa.me/?text=${encodeURIComponent(message)}`;
}

document.addEventListener('DOMContentLoaded', () => {
    initBillingTerminal();

    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => filterBillingProducts(e.target.value));
    }

    const checkoutBtn = document.getElementById('checkoutBtn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', processTerminalCheckout);
    }
});

async function initBillingTerminal() {
    const dateEl = document.getElementById('billDate');
    if (dateEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    }

    try {
        const response = await fetch('/inventory/api/products');
        const data = await response.json();

        if (data.error) {
            document.getElementById('productGrid').innerHTML = `
                <div class="col-span-full py-20 text-center">
                    <div class="w-16 h-16 bg-amber-50 dark:bg-amber-900/20 text-amber-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="bi bi-exclamation-triangle text-2xl"></i>
                    </div>
                    <p class="text-sm font-black text-slate-800 dark:text-white uppercase tracking-widest">${data.error}</p>
                </div>`;
            return;
        }

        allProducts = Array.isArray(data) ? data : [];
        renderSelectionGrid(allProducts);
    } catch (error) {
        console.error('Terminal Sync Error:', error);
        document.getElementById('productGrid').innerHTML = `<div class="col-span-full py-20 text-center text-red-500 font-bold italic">Network Outage: Registry synchronization failed.</div>`;
    }
}

function renderSelectionGrid(products) {
    const grid = document.getElementById('productGrid');
    grid.innerHTML = '';

    if (products.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-10 text-center text-slate-400 text-xs italic">No SKU matches found.</div>`;
        return;
    }

    products.forEach(p => {
        const isLow = p.quantity <= 0;

        const card = document.createElement('div');
        card.className = `p-3 rounded-xl border ${isLow ? 'opacity-50 grayscale pointer-events-none' : 'cursor-pointer hover:border-indigo-600/50 hover:shadow-lg hover:shadow-indigo-600/5 active:scale-95'} bg-white dark:bg-slate-900 border-slate-100 dark:border-slate-800 transition-all flex flex-col justify-between h-36 select-none`;
        card.onclick = () => addToBatch(p.id);

        card.innerHTML = `
            <div>
                <h4 class="text-[11px] font-black text-slate-800 dark:text-white leading-tight mb-0.5 truncate">${p.name}</h4>
                <div class="flex justify-between items-center mb-2">
                    <span class="text-[8px] font-black text-slate-400 uppercase tracking-widest">₹${p.selling_price.toFixed(2)} / un</span>
                    <span class="text-[7px] font-bold ${p.quantity <= 5 ? 'text-red-500' : 'text-slate-400'}">Qty: ${p.quantity}</span>
                </div>
            </div>
            <div class="pt-2 border-t border-slate-50 dark:border-slate-800 flex justify-between items-center">
                <span class="text-xs font-black text-slate-900 dark:text-white tracking-tighter">₹${p.selling_price.toFixed(2)}</span>
                <div class="w-6 h-6 bg-indigo-50 dark:bg-indigo-900/40 rounded-lg flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                    <i class="bi bi-plus text-base"></i>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterBillingProducts(term) {
    const filtered = allProducts.filter(p =>
        p.name.toLowerCase().includes(term.toLowerCase()) ||
        p.id.toString().includes(term)
    );
    renderSelectionGrid(filtered);
}

function addToBatch(id) {
    const product = allProducts.find(p => p.id === id);
    if (!product || product.quantity <= 0) return;

    product.quantity--;

    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.qty++;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.selling_price,
            qty: 1,
            max_limit: product.quantity + 1,
            tax_rate: product.effective_tax || 0
        });
    }
    renderTerminalCart();
    const searchTerm = document.getElementById('productSearch')?.value || '';
    filterBillingProducts(searchTerm);
}

function renderTerminalCart() {
    const body = document.getElementById('cartBody');
    const emptyMsg = document.getElementById('emptyCartMessage');
    const totalEl = document.getElementById('cartTotal');
    const subtotalEl = document.getElementById('subtotalDisplay');
    const taxEl = document.getElementById('taxDisplay');
    const countEl = document.getElementById('itemCount');
    const taxRate = parseFloat(totalEl.dataset.taxRate || 0);

    body.innerHTML = '';
    let subtotal = 0;
    let totalTax = 0;

    if (cart.length === 0) {
        if (emptyMsg) emptyMsg.classList.remove('hidden');
    } else {
        if (emptyMsg) emptyMsg.classList.add('hidden');
        cart.forEach((item, index) => {
            const rowSubtotal = item.price * item.qty;
            const rowTax = rowSubtotal * (item.tax_rate / 100);

            subtotal += rowSubtotal;
            totalTax += rowTax;

            const div = document.createElement('div');
            div.className = 'bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm flex items-center gap-4 group';
            div.innerHTML = `
                <div class="flex-1 min-w-0">
                    <h5 class="text-xs font-black text-slate-800 dark:text-white truncate mb-0.5">${item.name}</h5>
                    <div class="flex items-center gap-2">
                         <p class="text-[9px] font-bold text-slate-400 uppercase tracking-widest">₹${item.price.toFixed(2)}</p>
                         ${item.tax_rate > 0 ? `<span class="text-[8px] font-black text-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 px-1.5 py-0.5 rounded">${item.tax_rate}% Tax</span>` : ''}
                    </div>
                </div>
                <div class="flex items-center bg-slate-50 dark:bg-slate-950 rounded-xl p-1 gap-1">
                    <button onclick="updateQty(${index}, -1)" class="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-red-600 transition-colors"><i class="bi bi-dash"></i></button>
                    <span class="w-6 text-center text-[10px] font-black text-slate-700 dark:text-slate-300">${item.qty}</span>
                    <button onclick="updateQty(${index}, 1)" class="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-emerald-600 transition-colors"><i class="bi bi-plus"></i></button>
                    <div class="border-l border-slate-200 dark:border-slate-800 h-4 mx-1"></div>
                    <button onclick="updateQty(${index}, 5)" class="px-1.5 py-0.5 text-[8px] font-black text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded transition-colors">+5</button>
                    <button onclick="updateQty(${index}, 10)" class="px-1.5 py-0.5 text-[8px] font-black text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded transition-colors">+10</button>
                </div>
                <div class="text-right min-w-[70px]">
                    <p class="text-xs font-black text-slate-900 dark:text-white tracking-tighter">₹${rowSubtotal.toFixed(2)}</p>
                    <button onclick="removeFromCart(${index})" class="text-[8px] font-black text-red-400 uppercase tracking-widest hover:text-red-600">Remove</button>
                </div>
            `;
            body.appendChild(div);
        });
    }

    const grandTotal = subtotal + totalTax;

    if (subtotalEl) subtotalEl.textContent = '₹' + subtotal.toFixed(2);
    if (taxEl) taxEl.textContent = '+₹' + totalTax.toFixed(2);
    totalEl.textContent = grandTotal.toFixed(2);
    if (countEl) countEl.textContent = cart.length + (cart.length === 1 ? ' Item' : ' Items');
}

function updateQty(index, delta) {
    const item = cart[index];
    const product = allProducts.find(p => p.id === item.id);

    if (delta > 0) {
        const available = product ? product.quantity : 0;
        const toAdd = Math.min(delta, available);
        if (toAdd > 0) {
            item.qty += toAdd;
            if (product) product.quantity -= toAdd;
            if (toAdd < delta) {
                showAlert('Stock Limit: Only ' + toAdd + ' more items available.', 'warning', 'Stock Limit');
            }
        } else {
            showAlert('Stock Limit: Cannot exceed physical inventory.', 'error', 'Stock Limit');
        }
    } else if (delta < 0) {
        const toRemove = Math.min(Math.abs(delta), item.qty);
        item.qty -= toRemove;
        if (product) product.quantity += toRemove;

        if (item.qty <= 0) {
            cart.splice(index, 1);
        }
    }

    renderTerminalCart();
    const searchTerm = document.getElementById('productSearch')?.value || '';
    filterBillingProducts(searchTerm);
}

function removeFromCart(index) {
    const item = cart[index];
    const product = allProducts.find(p => p.id === item.id);
    if (product) {
        product.quantity += item.qty;
    }
    cart.splice(index, 1);
    renderTerminalCart();
    const searchTerm = document.getElementById('productSearch')?.value || '';
    filterBillingProducts(searchTerm);
}

async function processTerminalCheckout() {
    if (cart.length === 0) {
        showAlert('Cart is empty. Please add items before checkout.', 'warning', 'Empty Cart');
        return;
    }

    const btn = document.getElementById('checkoutBtn');
    if (btn.disabled) return;

    const originalContent = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span> Processing Sale...`;

    let customerName = document.getElementById('customerName')?.value.trim();
    let customerPhone = document.getElementById('customerPhone')?.value.trim();

    if (!customerName || !customerPhone) {
        playErrorSound();
        showAlert('Customer details are mandatory. Please provide a Name and Phone Number.', 'warning', 'Details Missing');
        btn.disabled = false;
        btn.innerHTML = originalContent;
        return;
    }

    try {
        const response = await fetch('/billing/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                items: cart,
                customerName: customerName,
                customerPhone: customerPhone
            })
        });

        const result = await response.json();

        if (result.success) {
            const modalBody = document.querySelector('#invoiceModal .modal-body');

            // Use Server Data for Source of Truth if available, fallback to client calc
            // Note: client 'cart' is still used for item list names until server returns full item breakdown
            const serverData = result.bill_details || {};

            const subtotal = serverData.subtotal !== undefined ? serverData.subtotal : cart.reduce((s, i) => s + (i.price * i.qty), 0);
            const totalTax = serverData.tax !== undefined ? serverData.tax : cart.reduce((s, i) => s + (i.price * i.qty * (i.tax_rate / 100)), 0);
            const total = serverData.total !== undefined ? serverData.total : (subtotal + totalTax);
            const billNumber = result.bill_number;

            const modal = new bootstrap.Modal(document.getElementById('invoiceModal'));

            // Setup receipt handlers safely
            window.lastSaleData = {
                billNumber: billNumber,
                items: JSON.parse(JSON.stringify(cart)),
                subtotal,
                totalTax,
                total,
                customerName: customerName || 'Guest',
                customerPhone: customerPhone || 'N/A'
            };

            modal.show();

            modalBody.innerHTML = `
                <div class="animate-bounce w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i class="bi bi-patch-check-fill text-3xl"></i>
                </div>
                <h2 class="text-2xl font-black text-slate-900 dark:text-white mb-1">Sale Complete</h2>
                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-8">Payment Successful</p>
                
                <div class="bg-white dark:bg-slate-950 p-6 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 text-left mb-8 shadow-inner">
                    <div class="text-center mb-10">
                        <p class="text-[9px] font-black text-indigo-600 uppercase tracking-[0.3em] mb-2">Transaction At</p>
                        <h1 class="text-3xl font-black text-slate-900 dark:text-white tracking-tighter uppercase mb-4">${SESSION_DATA.storeName}</h1>
                        <div class="w-16 h-1 bg-gradient-to-r from-indigo-600 to-transparent mx-auto rounded-full"></div>
                    </div>

                    <div class="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-slate-200/50 dark:border-slate-800">
                        <div>
                            <p class="text-[8px] font-black text-slate-400 uppercase tracking-widest">Bill Details</p>
                            <p class="text-xs font-black text-indigo-600">#${billNumber}</p>
                            <p class="text-[10px] font-bold text-slate-900 dark:text-white">${new Date().toLocaleDateString('en-IN')} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-[8px] font-black text-slate-400 uppercase tracking-widest">Customer</p>
                            <p class="text-xs font-black text-slate-900 dark:text-white">${window.lastSaleData.customerName}</p>
                            <p class="text-[10px] font-bold text-slate-500">${window.lastSaleData.customerPhone}</p>
                        </div>
                    </div>
                    
                    <div class="max-h-48 overflow-y-auto space-y-3 mb-6 pr-2 custom-scrollbar">
                        ${cart.map(i => {
                // Visual only - the totals below are from server
                const lineSub = i.price * i.qty;
                const lineTax = lineSub * (i.tax_rate / 100);
                return `
                                <div class="flex justify-between items-start text-xs border-b border-slate-100 dark:border-slate-800 pb-2">
                                    <div class="pr-4">
                                        <p class="font-bold text-slate-700 dark:text-slate-300">${i.qty} x ${i.name}</p>
                                        ${i.tax_rate > 0 ? `<p class="text-[8px] text-slate-400 uppercase tracking-tighter">Tax Incl. (${i.tax_rate}%)</p>` : ''}
                                    </div>
                                    <span class="font-black text-slate-900 dark:text-white shrink-0">₹${(lineSub + lineTax).toFixed(2)}</span>
                                </div>
                            `;
            }).join('')}
                    </div>

                    <div class="pt-4 space-y-2">
                        <div class="flex justify-between text-[10px] font-bold text-slate-400 uppercase">
                            <span>Subtotal</span>
                            <span>₹${subtotal.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between text-[10px] font-bold text-red-500 uppercase">
                            <span>Tax</span>
                            <span>+₹${totalTax.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between items-end pt-2 border-t-2 border-dashed border-slate-200 dark:border-slate-800">
                            <span class="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-widest">Total</span>
                            <span class="text-2xl font-black text-indigo-600">₹${total.toFixed(2)}</span>
                        </div>
                    </div>
                </div>

                <div class="space-y-2">
                    <button id="whatsappBtn" class="w-full py-2.5 bg-emerald-600 text-white rounded-xl font-black text-[10px] uppercase tracking-widest shadow-lg hover:scale-[1.02] transition-all">
                        <i class="bi bi-whatsapp me-2"></i> Send via WhatsApp
                    </button>
                    <button onclick="window.print()" class="w-full py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-black text-[10px] uppercase tracking-widest shadow-lg hover:scale-[1.02] transition-all">
                        <i class="bi bi-printer me-2"></i> Print Receipt
                    </button>
                    <button onclick="window.location.reload()" class="w-full py-2 text-[9px] font-black text-slate-400 hover:text-indigo-600 uppercase tracking-[0.2em] transition-colors">
                        Next Customer
                    </button>
                </div>
            `;

            document.getElementById('whatsappBtn').onclick = () => {
                const url = generateWhatsAppReceipt(
                    window.lastSaleData.billNumber,
                    window.lastSaleData.items,
                    window.lastSaleData.subtotal,
                    window.lastSaleData.totalTax,
                    window.lastSaleData.total,
                    window.lastSaleData.customerName
                );
                window.open(url, '_blank');
            };
            playSuccessSound();
            if (window.confetti) confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
        } else {
            playErrorSound();
            showAlert('Sale Failed: ' + result.message, 'error', 'Checkout Error');
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }
    } catch (error) {
        playErrorSound();
        showAlert('Connection Error: Order packet lost or server unreachable.', 'error', 'Network Outage');
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}
