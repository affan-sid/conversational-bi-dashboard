"""
Data Transformation Module
Handles data cleaning and transformation
"""
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataTransformer:
    """Transform and clean data"""
    
    def _hash_email(self, email: str) -> str:
        """One-way hash an email address, keeping the domain for debugging."""
        if not isinstance(email, str):
            return "unknown@anon.local"
        local, _, domain = email.partition("@")
        hashed = hashlib.sha256(local.encode()).hexdigest()[:12]
        return f"{hashed}@anon.local"

    def _mask_phone(self, phone: str) -> str:
        """Keep country code and area code, mask the rest."""
        if not isinstance(phone, str):
            return "***-***-****"
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 10:
            return f"+{digits[0]}-{digits[1:4]}-****"
        return "***-***-****"

    def anonymise_customers(self, df):
        """Mask PII columns before loading to the DB."""
        df_anon = df.copy()
        if "email" in df_anon.columns:
            df_anon["email"] = df_anon["email"].apply(self._hash_email)
        if "phone" in df_anon.columns:
            df_anon["phone"] = df_anon["phone"].apply(self._mask_phone)
        return df_anon

    def clean_companies(self, df):
        """Clean companies table"""
        df_clean = df.copy()
        df_clean['created_at'] = pd.to_datetime(df_clean['created_at'], errors='coerce')
        df_clean['industry'] = df_clean['industry'].fillna('Unknown')
        df_clean['country'] = df_clean['country'].fillna('Unknown')
        df_clean['currency'] = df_clean['currency'].fillna('CAD')
        return df_clean
    
    def clean_orders(self, df):
        """Clean orders table"""
        df_clean = df.copy()
        df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], errors='coerce')
        df_clean['total_amount'] = df_clean['total_amount'].fillna(0)
        df_clean['discount_amount'] = df_clean['discount_amount'].fillna(0)
        df_clean['net_amount'] = df_clean['total_amount'] - df_clean['discount_amount']
        return df_clean
    
    def clean_order_items(self, df):
        """Clean order items table"""
        df_clean = df.copy()
        df_clean['quantity'] = df_clean['quantity'].abs()
        df_clean['unit_price'] = df_clean['unit_price'].abs()
        df_clean['cost_price'] = df_clean['cost_price'].abs()
        # Recalculate line_total
        df_clean['line_total'] = df_clean['quantity'] * df_clean['unit_price']
        return df_clean
    
    def clean_transactions(self, df):
        """Clean transactions table"""
        df_clean = df.copy()
        df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
        df_clean['amount'] = df_clean['amount'].abs()
        df_clean['signed_amount'] = df_clean.apply(
            lambda x: x['amount'] if x['type'] == 'income' else -x['amount'], axis=1
        )
        return df_clean
    
    def clean_services(self, df):
        """Clean services dimension table"""
        df_clean = df.copy()
        df_clean['price'] = df_clean['price'].abs()
        df_clean['duration_minutes'] = df_clean['duration_minutes'].fillna(0).astype(int)
        df_clean['recurring_flag'] = df_clean['recurring_flag'].fillna(0).astype(int)
        df_clean['active_flag'] = df_clean['active_flag'].fillna(1).astype(int)
        df_clean['description'] = df_clean['description'].fillna('')
        return df_clean

    def clean_service_bookings(self, df):
        """Clean service bookings fact table"""
        df_clean = df.copy()
        df_clean['booking_date'] = pd.to_datetime(df_clean['booking_date'], errors='coerce')
        df_clean['sessions'] = df_clean['sessions'].fillna(1).abs().astype(int)
        df_clean['unit_price'] = df_clean['unit_price'].abs()
        df_clean['line_total'] = df_clean['sessions'] * df_clean['unit_price']
        return df_clean

    def clean_all(self, dataframes):
        """Apply all cleaning functions"""
        cleaned_dataframes = {}

        cleaning_map = {
            'companies': self.clean_companies,
            'orders': self.clean_orders,
            'order_items': self.clean_order_items,
            'transactions': self.clean_transactions,
            'services': self.clean_services,
            'service_bookings': self.clean_service_bookings,
        }

        for name, df in dataframes.items():
            if name in cleaning_map:
                cleaned_dataframes[name] = cleaning_map[name](df)
                logger.info(f"✓ Cleaned {name}")
            else:
                cleaned_dataframes[name] = df.copy()

        if 'customers' in cleaned_dataframes:
            cleaned_dataframes['customers'] = self.anonymise_customers(cleaned_dataframes['customers'])
            logger.info("✓ PII anonymised: customers (email hashed, phone masked)")

        return cleaned_dataframes

if __name__ == "__main__":
    # Test with sample data
    from extract import DataExtractor
    extractor = DataExtractor()
    data = extractor.extract_all()
    transformer = DataTransformer()
    cleaned_data = transformer.clean_all(data)
