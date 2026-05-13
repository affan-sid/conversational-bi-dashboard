"""
Data Loading Module for PostgreSQL
Handles loading data into PostgreSQL database
"""
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.types import Integer, Float, String, DateTime, Date, Boolean
import pandas as pd
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """Load data into PostgreSQL database"""
    
    def __init__(self, db_url=None):
        """
        Initialize PostgreSQL connection
        Can use provided URL or build from environment variables
        """
        if db_url:
            self.db_url = db_url
        else:
        #     # Build connection string from environment variables
        #     self.db_url = f"postgresql://{os.getenv('DB_USER', 'saumyabandara')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'bi_dashboard')}"
        
        # self.engine = create_engine(self.db_url, echo=False)
        # logger.info(f"Connected to PostgreSQL: {os.getenv('DB_NAME', 'bi_dashboard')}")
        # Use connection without password for local development
            self.db_url = "postgresql://postgres:1234@localhost:5432/bi_dashboard"
        
        self.engine = create_engine(self.db_url, echo=False)
        logger.info(f"Connected to PostgreSQL: bi_dashboard")
    
    def create_star_schema(self, star_schema, schema_name='public'):
        """
        Create star schema tables in PostgreSQL
        
        Parameters:
        - star_schema: dict of DataFrames to load
        - schema_name: PostgreSQL schema name (default: 'public')
        """
        
        # Define data types for each table to ensure proper PostgreSQL types
        dtype_mappings = {
            'dim_date': {
                'date_id': Integer,
                'date': DateTime,
                'year': Integer,
                'quarter': Integer,
                'month': Integer,
                'is_weekend': Integer
            },
            'fact_sales': {
                'order_item_id': Integer,
                'order_id': Integer,
                'product_id': Integer,
                'quantity': Integer,
                'unit_price': Float,
                'line_total': Float,
                'gross_profit': Float
            }
        }
        
        for table_name, df in star_schema.items():
            try:
                # Use appropriate dtype mapping if exists
                dtype = dtype_mappings.get(table_name, {})
                
                # Load to PostgreSQL
                df.to_sql(
                    table_name, 
                    self.engine, 
                    schema=schema_name,
                    if_exists='replace',  # Use 'append' to add to existing table
                    index=False,
                    dtype=dtype,
                    method='multi',  # Faster loading for larger datasets
                    chunksize=1000   # Load in chunks of 1000 rows
                )
                logger.info(f"✓ Loaded {table_name}: {len(df)} rows into PostgreSQL ({schema_name} schema)")
                
            except Exception as e:
                logger.error(f"✗ Error loading {table_name}: {e}")
    
    def create_indexes(self, schema_name='public'):
        """
        Create indexes for better query performance in PostgreSQL
        """
        with self.engine.connect() as conn:
            # Date dimension indexes
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_dim_date_date 
                ON {schema_name}.dim_date (date);
                CREATE INDEX IF NOT EXISTS idx_dim_date_year_month 
                ON {schema_name}.dim_date (year, month);
            """))
            
            # Sales fact indexes
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_fact_sales_order_date 
                ON {schema_name}.fact_sales (order_date);
                CREATE INDEX IF NOT EXISTS idx_fact_sales_product_id 
                ON {schema_name}.fact_sales (product_id);
                CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_id 
                ON {schema_name}.fact_sales (customer_id);
            """))
            
            # Marketing fact indexes
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_fact_marketing_date 
                ON {schema_name}.fact_marketing (date);
                CREATE INDEX IF NOT EXISTS idx_fact_marketing_campaign_id 
                ON {schema_name}.fact_marketing (campaign_id);
            """))
            
            # Cash flow indexes
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_fact_cash_flow_date 
                ON {schema_name}.fact_cash_flow (date);
                CREATE INDEX IF NOT EXISTS idx_fact_cash_flow_type 
                ON {schema_name}.fact_cash_flow (type);
            """))
            
            conn.commit()
            logger.info("✓ Created indexes on all tables")
    
    def create_views(self, schema_name='public'):
        """
        Create business views in PostgreSQL for common queries
        """
        with self.engine.connect() as conn:
            # Daily revenue view
            conn.execute(text(f"""
                CREATE OR REPLACE VIEW {schema_name}.v_daily_sales AS
                SELECT 
                    o.order_date,
                    COUNT(DISTINCT o.order_id) as order_count,
                    SUM(oi.line_total) as total_revenue,
                    SUM(oi.quantity * oi.cost_price) as total_cogs,
                    SUM(oi.line_total - (oi.quantity * oi.cost_price)) as gross_profit
                FROM {schema_name}.fact_sales oi
                JOIN {schema_name}.orders o ON oi.order_id = o.order_id
                GROUP BY o.order_date
                ORDER BY o.order_date DESC;
            """))
            
            # Customer metrics view
            conn.execute(text(f"""
                CREATE OR REPLACE VIEW {schema_name}.v_customer_metrics AS
                SELECT 
                    c.customer_id,
                    c.full_name,
                    c.segment,
                    COUNT(o.order_id) as total_orders,
                    SUM(o.total_amount) as total_spent,
                    AVG(o.total_amount) as avg_order_value,
                    MAX(o.order_date) as last_order_date
                FROM {schema_name}.customers c
                LEFT JOIN {schema_name}.orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id, c.full_name, c.segment;
            """))
            
            # Marketing ROI view
            conn.execute(text(f"""
                CREATE OR REPLACE VIEW {schema_name}.v_marketing_roi AS
                SELECT 
                    c.campaign_name,
                    c.platform,
                    SUM(mp.spend) as total_spend,
                    SUM(mp.revenue_attributed) as attributed_revenue,
                    CASE 
                        WHEN SUM(mp.spend) > 0 
                        THEN ((SUM(mp.revenue_attributed) - SUM(mp.spend)) / SUM(mp.spend)) * 100 
                        ELSE 0 
                    END as roi_percentage
                FROM {schema_name}.marketing_performance mp
                JOIN {schema_name}.campaigns c ON mp.campaign_id = c.campaign_id
                GROUP BY c.campaign_id, c.campaign_name, c.platform;
            """))
            
            conn.commit()
            logger.info("✓ Created business views")
    
    def execute_query(self, sql_query):
        """Execute custom SQL query and return results as DataFrame"""
        try:
            df = pd.read_sql(sql_query, self.engine)
            logger.info(f"✓ Query executed successfully, returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"✗ Query execution failed: {e}")
            return None
    
    def test_connection(self):
        """Test PostgreSQL connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version();"))
                version = result.fetchone()[0]
                logger.info(f"✓ Successfully connected to PostgreSQL: {version[:50]}...")
                return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False

if __name__ == "__main__":
    # Test the loader
    loader = DataLoader()
    if loader.test_connection():
        print("PostgreSQL connection successful!")
