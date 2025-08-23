#!/usr/bin/env python3

import os
import time
from pathlib import Path
from databricks.sdk import WorkspaceClient

# Load environment variables from .env.local if it exists
def load_env_local():
    env_file = Path(__file__).parent / '.env.local'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_local()

# User can modify this query as needed
USER_QUERY = """
select * from system.query.history limit 10
"""

# User can specify SQL Warehouse ID (leave None to auto-select first available)
SQL_WAREHOUSE_ID = None

# Databricks configuration - loads from environment or .env.local
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST', 'https://your-workspace.cloud.databricks.com')

def get_e2_demo_client():
    """Initialize Databricks client - works both locally and in Databricks notebooks"""
    
    # Check if we're in a Databricks environment by looking for specific env vars
    if 'DATABRICKS_RUNTIME_VERSION' in os.environ or 'DB_HOME' in os.environ:
        print("Running in Databricks environment - using default authentication")
        try:
            # In Databricks notebooks, use default auth
            return WorkspaceClient()
        except Exception as e:
            print(f"Default auth failed, trying with explicit host: {e}")
            return WorkspaceClient(host=DATABRICKS_HOST)
    else:
        # We're running locally - use PAT token
        print("Running locally - using PAT token authentication")
        
        # Get token at function call time (not module import time)
        databricks_e2_demo_token = os.getenv('E2_DEMO_FIELD_ENG_PAT')
        
        # Check if token is available
        if not databricks_e2_demo_token:
            raise ValueError("E2_DEMO_FIELD_ENG_PAT environment variable is not set or is None. Please check your environment configuration.")
        
        # Set environment variables from constants
        os.environ['DATABRICKS_TOKEN'] = databricks_e2_demo_token
        os.environ['DATABRICKS_HOST'] = DATABRICKS_HOST
        
        print(f"Connecting to Databricks at: {DATABRICKS_HOST}")
        return WorkspaceClient(host=DATABRICKS_HOST, token=databricks_e2_demo_token)

def execute_query(client, query, warehouse_id=None):
    """
    Execute a SQL query using Databricks SQL
    
    Args:
        client: WorkspaceClient instance
        query: SQL query string to execute
        warehouse_id: Optional warehouse ID. If not provided, will use default
    
    Returns:
        Query results as a list of dictionaries
    """
    try:
        # If no warehouse_id provided, find a running serverless warehouse
        if not warehouse_id:
            warehouses = list(client.warehouses.list())
            if not warehouses:
                raise ValueError("No SQL warehouses found")
            
            # Filter for running serverless warehouses first
            running_serverless = [w for w in warehouses 
                                if w.state == "RUNNING" and w.warehouse_type == "SERVERLESS"]
            
            if running_serverless:
                warehouse = running_serverless[0]
                warehouse_id = warehouse.id
                print(f"Using running serverless warehouse: {warehouse.name} ({warehouse_id})")
            else:
                # Fallback to any running warehouse
                running_warehouses = [w for w in warehouses if w.state == "RUNNING"]
                if running_warehouses:
                    warehouse = running_warehouses[0]
                    warehouse_id = warehouse.id
                    print(f"Using running warehouse: {warehouse.name} ({warehouse_id})")
                else:
                    # Last resort: use first available warehouse regardless of state
                    warehouse = warehouses[0]
                    warehouse_id = warehouse.id
                    print(f"Using warehouse (may need to start): {warehouse.name} ({warehouse_id})")
        else:
            # User specified warehouse_id, get warehouse info for display
            try:
                warehouse = client.warehouses.get(warehouse_id)
                print(f"Using specified warehouse: {warehouse.name} ({warehouse_id}) - State: {warehouse.state}")
            except Exception:
                print(f"Using specified warehouse ID: {warehouse_id} (unable to get warehouse details)")
        
        # Create and execute the statement
        print(f"Executing query: {query.strip()}")
        
        statement = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout="30s"
        )
        
        # Wait for completion
        while str(statement.status.state) in ["StatementState.PENDING", "StatementState.RUNNING"]:
            print("Query running...")
            time.sleep(1)
            statement = client.statement_execution.get_statement(statement.statement_id)
        
        if str(statement.status.state) == "StatementState.SUCCEEDED":
            print("Query completed successfully!")
            
            # Get results
            result = client.statement_execution.get_statement_result_chunk_n(
                statement_id=statement.statement_id,
                chunk_index=0
            )
            
            # Parse results into list of dictionaries
            if result.data_array:
                columns = [col.name for col in statement.manifest.schema.columns]
                rows = []
                for row in result.data_array:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = value
                    rows.append(row_dict)
                
                print(f"Retrieved {len(rows)} rows")
                return rows
            else:
                print("Query returned no results")
                return []
                
        else:
            error_msg = f"Query failed with state: {statement.status.state}"
            if statement.status.error:
                error_msg += f"\nError: {statement.status.error.message}"
            print(f"Debug: State check failed. State is: {statement.status.state} (type: {type(statement.status.state)})")
            print(f"Debug: String representation: '{str(statement.status.state)}'")
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Error executing query: {e}")
        raise

def main():
    """Main function"""
    try:
        print("Starting Databricks connection...")
        client = get_e2_demo_client()
        print("Databricks E2_DEMO client initialized successfully!")
        
        # Execute the user query
        results = execute_query(client, USER_QUERY, SQL_WAREHOUSE_ID)
        
        # Display results
        if results:
            print("\nQuery Results:")
            print("-" * 50)
            for i, row in enumerate(results, 1):
                print(f"Row {i}: {row}")
        else:
            print("No results returned")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()