"""
Centralized calculation logic for the application.
Ensures consistency in profit, tax, and margin calculations.
"""

def calculate_profit_metrics(cost: float, selling: float, qty: int) -> dict:
    """
    Calculate profit, revenue, and margin for a given quantity.
    """
    total_cost = round(cost * qty, 2)
    total_revenue = round(selling * qty, 2)
    profit = round(total_revenue - total_cost, 2)
    margin = round((profit / total_revenue * 100), 2) if total_revenue > 0 else 0.0
    
    return {
        'total_cost': total_cost,
        'total_revenue': total_revenue,
        'profit': profit,
        'margin': margin
    }

def calculate_bill_totals(subtotal: float, tax_rate: float, total_cost: float) -> dict:
    """
    Calculate final bill totals including tax.
    """
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total_revenue = round(subtotal + tax_amount, 2)
    total_profit = round(subtotal - total_cost, 2)
    
    return {
        'subtotal_amount': subtotal,
        'tax_amount': tax_amount,
        'total_amount': total_revenue,
        'total_profit': total_profit
    }
