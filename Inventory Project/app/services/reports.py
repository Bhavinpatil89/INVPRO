from typing import Dict, Any
from ..core.db import get_dashboard_kpi, get_inventory_kpi, get_stock_alerts, get_recent_bills, execute_query
from .base import BaseService
from .configuration import ConfigurationService

class ReportService(BaseService):
    """
    Handles Dashboard and Reporting logic.
    - business_admin: Main Office view.
    - branch_admin: Shop Manager view.
    - branch_staff: Billing view.
    """
    
    def _calculate_trend(self, current: float, previous: float) -> float:
        """Standardized trend calculation."""
        if not previous: return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    def get_store_dashboard_stats(self, time_filter='all') -> Dict[str, Any]:
        """Aggregate stats for the current node context."""
        self.context.ensure_store_access(self.store_id)
        limit = int(float(ConfigurationService(self.context).get_setting('low_stock_threshold', '10')))
        curr_f, prev_f = self._get_date_filters(time_filter)

        kpi = get_dashboard_kpi(self.store_id, date_filter=curr_f)
        rev, prof, tax = kpi[0] or 0.0, kpi[2] or 0.0, kpi[4] or 0.0
        
        rev_trend = prof_trend = 0
        if prev_f:
            p_kpi = get_dashboard_kpi(self.store_id, date_filter=prev_f)
            rev_trend = self._calculate_trend(rev, p_kpi[0] or 0.0)
            prof_trend = self._calculate_trend(prof, p_kpi[2] or 0.0)

        stock = get_inventory_kpi(self.store_id)
        alerts = get_stock_alerts(self.store_id, threshold=limit)
        
        cat_query = f"""
            SELECT c.name, SUM(bi.quantity * bi.price_at_sale) as revenue
            FROM bill_items bi JOIN products p ON bi.product_id = p.id
            JOIN categories c ON p.category_id = c.id JOIN bills b ON bi.bill_id = b.id
            WHERE b.store_id = ? {curr_f.replace('date(date)', 'date(b.date)')}
            GROUP BY c.id ORDER BY revenue DESC LIMIT 5
        """
        return {
            'revenue': rev, 'cost': kpi[1] or 0.0, 'profit': prof, 'tax': tax,
            'revenue_trend': rev_trend, 'profit_trend': prof_trend, 'transactions': kpi[3] or 0,
            'inventory_value': stock[0] or 0.0, 'product_count': stock[1] or 0,
            'low_stock_count': alerts[0], 'in_stock_count': alerts[1],
            'profit_margin': (prof / rev * 100) if rev > 0 else 0,
            'category_stats': [dict(c) for c in execute_query(cat_query, (self.store_id,), fetch_all=True)],
            'recent_bills': [dict(b) for b in get_recent_bills(self.store_id, limit=5)],
            'pending_transfers': self.get_pending_transfers(),
            'low_stock_details': self.get_detailed_low_stock()
        }

    def _get_date_filters(self, time_filter: str) -> tuple[str, str]:
        """Returns (current_filter, previous_filter) for trend comparison."""
        filters = {
            'day': ("= date('now', 'localtime')", "= date('now', 'localtime', '-1 day')"),
            'week': (">= date('now', 'localtime', '-7 days')", ">= date('now', 'localtime', '-14 days') AND date(date, 'localtime') < date('now', 'localtime', '-7 days')"),
            'month': (">= date('now', 'localtime', '-30 days')", ">= date('now', 'localtime', '-60 days') AND date(date, 'localtime') < date('now', 'localtime', '-30 days')"),
            'year': (">= date('now', 'localtime', '-365 days')", ">= date('now', 'localtime', '-730 days') AND date(date, 'localtime') < date('now', 'localtime', '-365 days')")
        }
        curr, prev = filters.get(time_filter, ("", ""))
        return (f"AND date(date, 'localtime') {curr}" if curr else "", f"AND date(date, 'localtime') {prev}" if prev else "")

    def get_enterprise_dashboard_stats(self, time_filter='all', store_id=None) -> Dict[str, Any]:
        """Global stats for HQ, optionally filtered by specific store context."""
        if not self.context.is_business_admin(): raise PermissionError("HQ Access Required.")

        scope = "store_id = ?" if store_id else "store_id IN (SELECT id FROM stores WHERE chain_id = ?)"
        params = [store_id or self.context.chain_id]
        curr_f, prev_f = self._get_date_filters(time_filter)
            
        res = execute_query(f"SELECT SUM(total_amount), SUM(total_profit), COUNT(id), SUM(tax_amount) FROM bills WHERE {scope} {curr_f}", tuple(params), fetch_one=True)
        rev, prof, count, tax = [x or 0.0 for x in res]
        
        rev_trend = prof_trend = 0
        if prev_f:
            p_res = execute_query(f"SELECT SUM(total_amount), SUM(total_profit) FROM bills WHERE {scope} {prev_f}", tuple(params), fetch_one=True)
            rev_trend = self._calculate_trend(rev, p_res[0] or 0.0)
            prof_trend = self._calculate_trend(prof, p_res[1] or 0.0)
        
        stock = execute_query(f"SELECT SUM(cost_price * quantity), COUNT(id) FROM products WHERE {scope}", tuple(params), fetch_one=True)
        stock_val = stock[0] or 0.0
        limit = int(float(ConfigurationService(self.context).get_setting('low_stock_threshold', '10')))
        low_stock_count = execute_query(f"SELECT COUNT(*) FROM products WHERE {scope} AND quantity <= ?", tuple(params + [limit]), fetch_one=True)[0] or 0
        
        branch_query = f"""
            SELECT s.id, s.name, COALESCE(SUM(b.total_amount), 0) as revenue, COALESCE(SUM(b.total_profit), 0) as profit,
                   (SELECT COUNT(*) FROM products WHERE store_id = s.id) as product_count,
                   (SELECT COALESCE(SUM(cost_price * quantity), 0) FROM products WHERE store_id = s.id) as stock_value
            FROM stores s LEFT JOIN bills b ON s.id = b.store_id {curr_f.replace('date(date)', 'date(b.date)')}
            WHERE s.chain_id = ? AND (s.location IS NULL OR s.location != 'HQ')
            GROUP BY s.id ORDER BY revenue DESC
        """
        branches = execute_query(branch_query, (self.context.chain_id,), fetch_all=True)
        
        # 5. Category Stats for HQ
        cat_date_cond = curr_f.replace('date(date)', 'date(b.date)') if curr_f else ""
        cat_query = f"""
            SELECT c.name, SUM(bi.quantity * bi.price_at_sale) as revenue
            FROM bill_items bi
            JOIN products p ON bi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN bills b ON bi.bill_id = b.id
            WHERE b.{scope} {cat_date_cond}
            GROUP BY c.id, c.name
            ORDER BY revenue DESC
            LIMIT 5
        """
        category_stats = execute_query(cat_query, tuple(params), fetch_all=True)

        return {
            'revenue': rev,
            'profit': prof,
            'tax': tax,
            'transactions': int(count) if count else 0,
            'inventory_value': stock_val,
            'low_stock_count': low_stock_count,
            'revenue_trend': rev_trend,
            'profit_trend': prof_trend,
            'branch_count': len(branches),
            'branches': [dict(b) for b in branches],
            'category_stats': [dict(c) for c in category_stats],
            'pending_transfers': self.get_pending_transfers(),
            'low_stock_details': self.get_detailed_low_stock()
        }

    def get_pending_transfers(self) -> list[dict[str, Any]]:
        """Fetch pending transfers relevant to the current context."""
        query = """
            SELECT t.*, 
                   fs.name as from_store_name, 
                   ts.name as to_store_name, 
                   p.name as product_name,
                   u.username as requester_name
            FROM inventory_transfers t
            JOIN stores fs ON t.from_store_id = fs.id
            JOIN stores ts ON t.to_store_id = ts.id
            JOIN products p ON t.product_id = p.id
            JOIN users u ON t.requested_by = u.id
            WHERE t.chain_id = ? AND t.status = 'pending'
        """
        params = [self.context.chain_id]
        
        if not self.context.is_business_admin():
            query += " AND (t.from_store_id = ? OR t.to_store_id = ?)"
            params.extend([self.store_id, self.store_id])
            
        query += " ORDER BY t.created_at DESC"
        results = execute_query(query, tuple(params), fetch_all=True)
        return [dict(r) for r in results]

    def get_detailed_low_stock(self, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch details of products with low stock."""
        config = ConfigurationService(self.context)
        threshold = int(float(config.get_setting('low_stock_threshold', '10')))
        
        query = """
            SELECT p.id, p.name, p.quantity, s.name as store_name, c.name as category_name
            FROM products p
            JOIN stores s ON p.store_id = s.id
            JOIN categories c ON p.category_id = c.id
            WHERE s.chain_id = ? AND p.quantity <= ?
        """
        params = [self.context.chain_id, threshold]
        
        if not self.context.is_business_admin():
            query += " AND p.store_id = ?"
            params.append(self.store_id)
            
        query += " ORDER BY p.quantity ASC LIMIT ?"
        params.append(limit)
        
        results = execute_query(query, tuple(params), fetch_all=True)
        return [dict(r) for r in results]

    def get_chart_data(self, time_filter='month', store_id=None) -> Dict[str, Any]:
        """Aggregate sales data for charts."""
        # Scope determination
        if not self.context.is_business_admin():
            self.context.ensure_store_access(self.store_id)
            where_clause = "store_id = ?"
            params = [self.store_id]
        else:
            if store_id:
                # HQ Filtering
                where_clause = "store_id = ?"
                params = [store_id]
            else:
                where_clause = "store_id IN (SELECT id FROM stores WHERE chain_id = ?)"
                params = [self.context.chain_id]

        # Date Logic
        # Date Logic & Granularity
        time_format = '%Y-%m-%d'

        if time_filter == 'month':
            date_cond = "AND date(date, 'localtime') >= date('now', 'localtime', '-30 days')"
            time_format = '%Y-%m-%d'
        elif time_filter == 'today' or time_filter == 'day':
            date_cond = "AND date(date, 'localtime') = date('now', 'localtime')"
            time_format = '%H:%M' # Minute granularity for Day view
        elif time_filter == 'week':
            date_cond = "AND date(date, 'localtime') >= date('now', 'localtime', '-7 days')"
            time_format = '%Y-%m-%d %H:00' # Hourly granularity for Week view
        elif time_filter == 'year':
            date_cond = "AND date(date, 'localtime') >= date('now', 'localtime', '-365 days')"
            time_format = '%Y-%m-%d'
        else:
            date_cond = ""
            time_format = '%Y-%m-%d'

        query = f"""
            SELECT strftime('{time_format}', datetime("date", 'localtime')) as day_label, 
                   SUM(total_amount) as total_rev, 
                   SUM(total_profit) as total_prof, 
                   SUM(tax_amount) as total_tax
            FROM bills
            WHERE {where_clause} {date_cond}
            GROUP BY day_label
            ORDER BY day_label ASC
        """
        results = execute_query(query, tuple(params), fetch_all=True)
        
        return {
            'labels': [r[0] for r in results],
            'revenue': [r[1] or 0.0 for r in results],
            'profit': [r[2] or 0.0 for r in results],
            'tax': [r[3] or 0.0 for r in results]
        }

    def get_branch_comparison(self, branch_ids: list[int] = None, time_filter: str = 'month') -> Dict[str, Any]:
        """
        Time-series comparison chart data for selected branches.
        Each branch gets its own line showing revenue/profit over time.
        """
        if not self.context.is_business_admin():
             raise PermissionError("Access Denied.")
             
        chain_id = self.context.chain_id
        
        # Determine time range and granularity
        time_format = '%Y-%m-%d'
        date_cond = ""
        
        if time_filter == 'day':
            date_cond = "AND date(b.date, 'localtime') = date('now', 'localtime')"
            time_format = '%H:00'  # Hourly for today
        elif time_filter == 'week':
            date_cond = "AND date(b.date, 'localtime') >= date('now', 'localtime', '-7 days')"
            time_format = '%Y-%m-%d'  # Daily for week
        elif time_filter == 'month':
            date_cond = "AND date(b.date, 'localtime') >= date('now', 'localtime', '-30 days')"
            time_format = '%Y-%m-%d'  # Daily for month
        elif time_filter == 'year':
            date_cond = "AND date(b.date, 'localtime') >= date('now', 'localtime', '-365 days')"
            time_format = '%Y-%m'  # Monthly for year
        # 'all' = no date filter, daily granularity
        
        # Get selected branches or top 10
        filter_clause = ""
        store_params = [chain_id]
        
        if branch_ids:
            placeholders = ','.join(['?'] * len(branch_ids))
            filter_clause = f"AND s.id IN ({placeholders})"
            store_params.extend(branch_ids)
        else:
            # Get top 10 branches by total revenue
            top_branches_query = f"""
                SELECT s.id FROM stores s
                LEFT JOIN bills b ON s.id = b.store_id
                WHERE s.chain_id = ? AND (s.location IS NULL OR s.location != 'HQ')
                GROUP BY s.id
                ORDER BY COALESCE(SUM(b.total_amount), 0) DESC
                LIMIT 10
            """
            top_branches = execute_query(top_branches_query, (chain_id,), fetch_all=True)
            branch_ids = [b[0] for b in top_branches]
            if branch_ids:
                placeholders = ','.join(['?'] * len(branch_ids))
                filter_clause = f"AND s.id IN ({placeholders})"
                store_params.extend(branch_ids)
        
        # Get time-series data for each branch
        query = f"""
            SELECT 
                s.id,
                s.name,
                strftime('{time_format}', datetime(b.date, 'localtime')) as period,
                COALESCE(SUM(b.total_amount), 0) as revenue,
                COALESCE(SUM(b.total_profit), 0) as profit
            FROM stores s
            LEFT JOIN bills b ON s.id = b.store_id {date_cond}
            WHERE s.chain_id = ? AND (s.location IS NULL OR s.location != 'HQ') {filter_clause}
            GROUP BY s.id, s.name, period
            ORDER BY period ASC, s.name ASC
        """
        
        results = execute_query(query, tuple(store_params), fetch_all=True)
        
        # Organize data by branch and period
        branches_data = {}
        all_periods = set()
        
        for row in results:
            store_id, store_name, period, revenue, profit = row
            if period:  # Skip null periods
                all_periods.add(period)
                if store_id not in branches_data:
                    branches_data[store_id] = {
                        'name': store_name,
                        'data': {}
                    }
                branches_data[store_id]['data'][period] = {
                    'revenue': revenue,
                    'profit': profit
                }
        
        # Sort periods chronologically
        sorted_periods = sorted(list(all_periods))
        
        # Build datasets - one line per branch
        datasets = []
        colors = [
            '#0ea5e9', '#d946ef', '#f59e0b', '#10b981', '#ef4444',
            '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1'
        ]
        
        for idx, (store_id, branch_info) in enumerate(branches_data.items()):
            color = colors[idx % len(colors)]
            
            # Combine revenue and profit into data points
            branch_data_points = []
            
            for period in sorted_periods:
                period_data = branch_info['data'].get(period, {'revenue': 0, 'profit': 0})
                branch_data_points.append({
                    'x': period,
                    'y': period_data['revenue'],
                    'profit': period_data['profit']
                })
            
            datasets.append({
                'label': branch_info['name'],
                'data': branch_data_points,
                'borderColor': color,
                'backgroundColor': f"{color}20",
                'branch_id': store_id,
                'branch_name': branch_info['name']
            })
        
        return {
            'labels': sorted_periods,
            'datasets': datasets
        }

    def get_recent_store_bills(self, limit=5):
        self.context.ensure_store_access(self.store_id)
        return get_recent_bills(self.store_id, limit)

    def get_chain_dashboard_stats(self, time_filter='all'):
        return self.get_enterprise_dashboard_stats(time_filter)
