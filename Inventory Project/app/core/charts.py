"""
Chart generation utilities using matplotlib.
Creates sales, profit, tax, and inventory charts for analytics.
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

def generate_sales_chart(bills_data, time_period='month'):
    """
    Generate sales chart from bills data.
    Returns base64 encoded image string.
    """
    if not bills_data:
        return None
    
    # Group by date
    dates = {}
    for bill in bills_data:
        date = bill['date'][:10] if isinstance(bill['date'], str) else str(bill['date'])[:10]
        if date not in dates:
            dates[date] = 0
        dates[date] += bill['total_amount']
    
    # Sort by date
    sorted_dates = sorted(dates.items())
    x_labels = [d[0] for d in sorted_dates]
    y_values = [d[1] for d in sorted_dates]
    
    plt.figure(figsize=(10, 6))
    plt.plot(x_labels, y_values, marker='o', linewidth=2, markersize=8, color='#4f46e5')
    plt.fill_between(range(len(y_values)), y_values, alpha=0.3, color='#4f46e5')
    # plt.title('Sales Trend', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Revenue (₹)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

def generate_profit_chart(bills_data):
    """Generate profit vs revenue chart."""
    if not bills_data:
        return None
    
    dates = {}
    for bill in bills_data:
        date = bill['date'][:10] if isinstance(bill['date'], str) else str(bill['date'])[:10]
        if date not in dates:
            dates[date] = {'revenue': 0, 'profit': 0}
        dates[date]['revenue'] += bill['total_amount']
        dates[date]['profit'] += bill.get('total_profit', 0)
    
    sorted_dates = sorted(dates.items())
    x_labels = [d[0] for d in sorted_dates]
    revenue = [d[1]['revenue'] for d in sorted_dates]
    profit = [d[1]['profit'] for d in sorted_dates]
    
    plt.figure(figsize=(10, 6))
    plt.plot(x_labels, revenue, marker='o', label='Revenue', linewidth=2, color='#4f46e5')
    plt.plot(x_labels, profit, marker='s', label='Profit', linewidth=2, color='#10b981')
    # plt.title('Revenue vs Profit', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Amount (₹)', fontsize=12)
    plt.legend()
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

def generate_tax_chart(bills_data):
    """Generate tax collection chart."""
    if not bills_data:
        return None
    
    dates = {}
    for bill in bills_data:
        date = bill['date'][:10] if isinstance(bill['date'], str) else str(bill['date'])[:10]
        if date not in dates:
            dates[date] = 0
        dates[date] += bill.get('tax_amount', 0)
    
    sorted_dates = sorted(dates.items())
    x_labels = [d[0] for d in sorted_dates]
    y_values = [d[1] for d in sorted_dates]
    
    plt.figure(figsize=(10, 6))
    plt.bar(x_labels, y_values, color='#ef4444', alpha=0.7)
    # plt.title('Tax Collection', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Tax Amount (₹)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

def generate_store_comparison_chart(store_data):
    """
    Generate store comparison bar chart.
    store_data: list of {'name': str, 'revenue': float, 'profit': float}
    """
    if not store_data:
        return None
    
    stores = [s['name'] for s in store_data]
    revenue = [s['revenue'] for s in store_data]
    profit = [s['profit'] for s in store_data]
    
    x = range(len(stores))
    width = 0.35
    
    plt.figure(figsize=(12, 6))
    plt.bar([i - width/2 for i in x], revenue, width, label='Revenue', color='#4f46e5', alpha=0.8)
    plt.bar([i + width/2 for i in x], profit, width, label='Profit', color='#10b981', alpha=0.8)
    
    # plt.title('Store Performance Comparison', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Branch', fontsize=12)
    plt.ylabel('Amount (₹)', fontsize=12)
    plt.xticks(x, stores, rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

def generate_inventory_health_chart(products_data):
    """
    Generate inventory health pie chart.
    products_data: list of products with quantity
    """
    if not products_data:
        return None
    
    # Categorize by stock level
    healthy = sum(1 for p in products_data if p['quantity'] > 10)
    low = sum(1 for p in products_data if 1 <= p['quantity'] <= 10)
    out = sum(1 for p in products_data if p['quantity'] == 0)
    
    labels = ['Healthy Stock', 'Low Stock', 'Out of Stock']
    sizes = [healthy, low, out]
    colors = ['#10b981', '#f59e0b', '#ef4444']
    explode = (0.05, 0.05, 0.1)
    
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
    # plt.title('Inventory Health Status', fontsize=16, fontweight='bold', pad=20)
    plt.axis('equal')
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"
