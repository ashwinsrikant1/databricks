import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'databricks-utils'))
from query_e2_demo import get_e2_demo_client, execute_query

# Schema definition for Iceberg table
ICEBERG_SCHEMA = {
    'id': 'BIGINT',
    'content': 'STRING',  # long text column
    'created_timestamp': 'TIMESTAMP',
    'status': 'STRING',
    'priority': 'INT',
    'category': 'STRING',
    'score': 'INT',
    'metadata': 'MAP<STRING, STRING>'  # simple key-value map
}

def get_default_schema():
    """Get the default schema from environment variable"""
    return os.getenv('DATABRICKS_DEFAULT_SCHEMA', 'users.ashwin_srikant')

def build_initial_table_query(source_table, target_table):
    """Build CTAS query to create initial Iceberg table from source table"""
    return f"""
CREATE OR REPLACE TABLE {target_table}
USING ICEBERG
AS
SELECT 
    CAST(ROW_NUMBER() OVER (ORDER BY rand()) AS BIGINT) as id,
    trimmed_content as content,
    current_timestamp() as created_timestamp,
    CASE 
        WHEN rand() < 0.3 THEN 'pending'
        WHEN rand() < 0.6 THEN 'active' 
        ELSE 'completed'
    END as status,
    CAST(FLOOR(rand() * 5) + 1 AS INT) as priority,
    CASE 
        WHEN rand() < 0.25 THEN 'research'
        WHEN rand() < 0.5 THEN 'analysis'
        WHEN rand() < 0.75 THEN 'development'
        ELSE 'testing'
    END as category,
    CAST(FLOOR(rand() * 100) AS INT) as score,
    map(
        'source', 'wikipedia_1k',
        'processed_by', 'iceberg_test',
        'batch_id', CAST(FLOOR(rand() * 1000) AS STRING)
    ) as metadata
FROM {source_table}
"""

def create_iceberg_table(client, source_table, target_table):
    """Create Iceberg table using CTAS from source table"""
    print(f"Creating Iceberg table {target_table} from {source_table}...")
    query = build_initial_table_query(source_table, target_table)
    results = execute_query(client, query)
    return results

def main():
    """Execute the CTAS query to create Iceberg table"""
    try:
        print("Starting Iceberg table creation...")
        client = get_e2_demo_client()
        
        # Define table names
        default_schema = get_default_schema()
        source_table = f"{default_schema}.batch_inf_wikipedia_1k"
        target_table = f"{default_schema}.iceberg_test_table"
        
        # Create the Iceberg table
        create_iceberg_table(client, source_table, target_table)
        
        print("Iceberg table creation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()