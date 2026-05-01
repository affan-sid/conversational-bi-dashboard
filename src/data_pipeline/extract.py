"""
Data Extraction Module
Handles loading data from CSV files
"""
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractor:
    """Extract data from various sources"""
    
    def __init__(self, data_path='data/raw'):
        self.data_path = Path(data_path)
        self.csv_files = {
            'companies': 'companies.csv',
            'users': 'users.csv',
            'data_sources': 'data_sources.csv',
            'products': 'products.csv',
            'customers': 'customers.csv',
            'campaigns': 'campaigns.csv',
            'orders': 'orders.csv',
            'order_items': 'order_items.csv',
            'marketing_performance': 'marketing_performance.csv',
            'transactions': 'transactions.csv',
            'expenses': 'expenses.csv',
            'cash_balances': 'cash_balances.csv',
            'customer_metrics': 'customer_metrics.csv'
        }
    
    def extract_all(self):
        """Load all CSV files into a dictionary of DataFrames"""
        dataframes = {}
        
        for name, filename in self.csv_files.items():
            file_path = self.data_path / filename
            try:
                df = pd.read_csv(file_path)
                dataframes[name] = df
                logger.info(f"✓ Loaded {name}: {len(df)} rows, {len(df.columns)} columns")
            except FileNotFoundError:
                logger.error(f"✗ File not found: {filename}")
            except Exception as e:
                logger.error(f"✗ Error loading {filename}: {e}")
        
        return dataframes

if __name__ == "__main__":
    extractor = DataExtractor()
    data = extractor.extract_all()
    print(f"Loaded {len(data)} tables")
