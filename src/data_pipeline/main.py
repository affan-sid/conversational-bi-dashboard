"""
Main ETL Pipeline for PostgreSQL
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.extract import DataExtractor
from data_pipeline.transform import DataTransformer
from data_pipeline.load import DataLoader
from data_pipeline.schema_builder import StarSchemaBuilder
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ETLPipeline:
    """Complete ETL pipeline for PostgreSQL"""
    
    def __init__(self, raw_data_path='data/raw'):
        self.extractor = DataExtractor(data_path=raw_data_path)
        self.transformer = DataTransformer()
        self.loader = DataLoader()
        self.schema_builder = StarSchemaBuilder()
    
    def run_full_pipeline(self):
        """Execute the complete ETL pipeline"""
        logger.info("="*60)
        logger.info("Starting ETL Pipeline for PostgreSQL")
        logger.info("="*60)
        
        # Step 1: Extract data
        logger.info("\n Step 1: Extracting raw data...")
        raw_data = self.extractor.extract_all()
        
        # Step 2: Transform data
        logger.info("\n Step 2: Transforming data...")
        cleaned_data = self.transformer.clean_all(raw_data)
        
        # Step 3: Build star schema
        logger.info("\n️ Step 3: Building star schema...")
        star_schema = self.schema_builder.create_star_schema(cleaned_data)
        
        # Step 4: Load to PostgreSQL
        logger.info("\n Step 4: Loading to PostgreSQL...")
        self.loader.create_star_schema(star_schema)
        
        # Step 5: Create indexes for performance
        logger.info("\n Step 5: Creating indexes...")
        self.loader.create_indexes()
        
        # Step 6: Create business views
        logger.info("\n️ Step 6: Creating business views...")
        self.loader.create_views()
        
        logger.info("\n" + "="*60)
        logger.info(" ETL Pipeline completed successfully!")
        logger.info("="*60)
        
        return star_schema
    
    def test_queries(self):
        """Test common queries on PostgreSQL"""
        
        test_queries = {
            "Total Revenue": """
                SELECT SUM(total_amount) as total_revenue 
                FROM orders 
                WHERE status = 'completed'
            """,
            
            "Daily Sales Trend": """
                SELECT 
                    DATE(order_date) as date,
                    COUNT(*) as order_count,
                    SUM(total_amount) as revenue
                FROM orders
                WHERE status = 'completed'
                GROUP BY DATE(order_date)
                ORDER BY date DESC
                LIMIT 10
            """,
            
            "Top Products": """
                SELECT 
                    p.product_name,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.line_total) as revenue
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                GROUP BY p.product_id, p.product_name
                ORDER BY revenue DESC
                LIMIT 5
            """,
            
            "Cash Runway": """
                WITH monthly_expenses AS (
                    SELECT 
                        DATE_TRUNC('month', date) as month,
                        SUM(amount) as total_expenses
                    FROM expenses
                    GROUP BY DATE_TRUNC('month', date)
                    ORDER BY month DESC
                    LIMIT 3
                ),
                avg_burn_rate AS (
                    SELECT AVG(total_expenses) as avg_monthly_burn
                    FROM monthly_expenses
                ),
                current_cash AS (
                    SELECT closing_balance as cash_balance
                    FROM cash_balances
                    ORDER BY date DESC
                    LIMIT 1
                )
                SELECT 
                    c.cash_balance,
                    a.avg_monthly_burn,
                    CASE 
                        WHEN a.avg_monthly_burn > 0 
                        THEN c.cash_balance / a.avg_monthly_burn 
                        ELSE 999 
                    END as cash_runway_months
                FROM current_cash c, avg_burn_rate a
            """
        }
        
        logger.info("\n Testing common queries on PostgreSQL:")
        for name, query in test_queries.items():
            try:
                result = self.loader.execute_query(query)
                logger.info(f"\n  {name}:")
                print(result.to_string(index=False))
            except Exception as e:
                logger.error(f"  ✗ {name} failed: {e}")

if __name__ == "__main__":
    pipeline = ETLPipeline(raw_data_path='data/raw')
    
    # Run the pipeline
    star_schema = pipeline.run_full_pipeline()
    
    # Test queries
    pipeline.test_queries()
