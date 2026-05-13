"""
Star Schema Builder for PostgreSQL
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StarSchemaBuilder:
    """Build star schema model for data warehouse"""
    
    def create_date_dimension(self, start_date, end_date):
        """Create date dimension table"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        dim_date = pd.DataFrame({
            'date_id': date_range.strftime('%Y%m%d').astype(int),
            'date': date_range,
            'year': date_range.year,
            'quarter': date_range.quarter,
            'month': date_range.month,
            'month_name': date_range.month_name(),
            'week': date_range.isocalendar().week,
            'day_of_month': date_range.day,
            'day_of_week': date_range.dayofweek,
            'day_name': date_range.day_name(),
            'is_weekend': (date_range.dayofweek >= 5).astype(int)
        })
        
        return dim_date
    
    def create_star_schema(self, cleaned_dataframes):
        """Create complete star schema from cleaned data"""
        
        star_schema = {}
        
        # Create date dimension
        all_dates = []
        if 'orders' in cleaned_dataframes:
            all_dates.extend(cleaned_dataframes['orders']['order_date'].dropna())
        if 'transactions' in cleaned_dataframes:
            all_dates.extend(cleaned_dataframes['transactions']['date'].dropna())
        
        if all_dates:
            start_date = min(all_dates)
            end_date = max(all_dates)
            star_schema['dim_date'] = self.create_date_dimension(start_date, end_date)
            logger.info(f"✓ Created dim_date with {len(star_schema['dim_date'])} rows")
        
        # Pass through dimension tables
        dimension_tables = ['customers', 'products', 'campaigns', 'companies', 'users']
        for table in dimension_tables:
            if table in cleaned_dataframes:
                star_schema[f'dim_{table}'] = cleaned_dataframes[table].copy()
                logger.info(f"✓ Created dim_{table} with {len(star_schema[f'dim_{table}'])} rows")
        
        # Create fact_sales
        if 'orders' in cleaned_dataframes and 'order_items' in cleaned_dataframes:
            fact_sales = cleaned_dataframes['order_items'].copy()
            fact_sales = fact_sales.merge(
                cleaned_dataframes['orders'][['order_id', 'order_date', 'customer_id', 'channel', 'status']],
                on='order_id'
            )
            fact_sales['gross_profit'] = fact_sales['line_total'] - (fact_sales['quantity'] * fact_sales['cost_price'])
            star_schema['fact_sales'] = fact_sales
            logger.info(f"✓ Created fact_sales with {len(fact_sales)} rows")
        
        # Create fact_marketing
        if 'marketing_performance' in cleaned_dataframes:
            fact_marketing = cleaned_dataframes['marketing_performance'].copy()
            star_schema['fact_marketing'] = fact_marketing
            logger.info(f"✓ Created fact_marketing with {len(fact_marketing)} rows")
        
        # Create fact_cash_flow
        if 'transactions' in cleaned_dataframes:
            fact_cash_flow = cleaned_dataframes['transactions'].copy()
            star_schema['fact_cash_flow'] = fact_cash_flow
            logger.info(f"✓ Created fact_cash_flow with {len(fact_cash_flow)} rows")
        
        # Create fact_expenses
        if 'expenses' in cleaned_dataframes:
            fact_expenses = cleaned_dataframes['expenses'].copy()
            star_schema['fact_expenses'] = fact_expenses
            logger.info(f"✓ Created fact_expenses with {len(fact_expenses)} rows")
        
        return star_schema
