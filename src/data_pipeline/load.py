"""
Data Loading Module
Handles loading data into database
"""
from sqlalchemy import create_engine, text
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """Load data into database"""
    
    def __init__(self, db_url='sqlite:///data/bi_dashboard.db'):
        self.engine = create_engine(db_url)
    
    def create_star_schema(self, star_schema):
        """Create star schema tables in database"""
        
        for table_name, df in star_schema.items():
            df.to_sql(table_name, self.engine, if_exists='replace', index=False)
            logger.info(f"✓ Loaded {table_name}: {len(df)} rows")
    
    def execute_sql(self, sql_query):
        """Execute SQL query"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            return result

if __name__ == "__main__":
    loader = DataLoader()
    # Load star_schema (you'd create this first)
