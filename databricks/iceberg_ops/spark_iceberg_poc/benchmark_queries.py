"""
Benchmarking query framework for Iceberg tables.
Provides common query patterns for performance testing.
"""

import sys
import os
import time
from typing import Dict, List, Optional, Tuple

# Add databricks-utils to path (relative to current repo structure)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'databricks-utils'))
from cluster_execution import get_e2_demo_client, execute_query_on_cluster

# Import configuration
from config import (
    DEFAULT_SCHEMA,
    BENCHMARK_SAMPLE_PERCENT,
    BENCHMARK_TOP_N_LIMIT,
    BENCHMARK_RANGE_START,
    BENCHMARK_RANGE_END,
    BENCHMARK_TEXT_SEARCH_PATTERN
)


class BenchmarkQuery:
    """Represents a single benchmark query with metadata."""
    
    def __init__(self, name: str, description: str, query_template: str, expected_result_type: str = "rows"):
        self.name = name
        self.description = description
        self.query_template = query_template
        self.expected_result_type = expected_result_type
    
    def format_query(self, table_name: str, **kwargs) -> str:
        """Format the query template with table name and other parameters."""
        return self.query_template.format(table_name=table_name, **kwargs)


class BenchmarkRunner:
    """Runs benchmark queries and collects performance metrics."""
    
    def __init__(self, schema: str = DEFAULT_SCHEMA):
        self.client = get_e2_demo_client()
        self.schema = schema
        self.results = []
    
    def run_query(self, query: BenchmarkQuery, table_name: str, **kwargs) -> Dict:
        """
        Run a single benchmark query and collect performance metrics.
        
        Returns:
            Dict with query results and performance metrics
        """
        full_table_name = f"{self.schema}.{table_name}"
        formatted_query = query.format_query(full_table_name, **kwargs)
        
        print(f"Running benchmark: {query.name}")
        print(f"Description: {query.description}")
        print(f"Query: {formatted_query[:200]}...")
        
        # Time the query execution
        start_time = time.time()
        
        try:
            result = execute_query_on_cluster(self.client, formatted_query)
            execution_time = time.time() - start_time
            
            # Extract metrics from result - cluster execution returns dict format
            if result.get('status') == 'success':
                # Parse the raw output - this is a simplified approach
                raw_output = result.get('raw_output', '')
                row_count = 1  # For now, assume queries return results
                first_row = {"raw_result": raw_output}
            else:
                row_count = 0
                first_row = {}
            
            benchmark_result = {
                "query_name": query.name,
                "description": query.description,
                "table_name": table_name,
                "execution_time_seconds": round(execution_time, 3),
                "row_count": row_count,
                "status": "success",
                "result_preview": first_row,
                "full_result": result
            }
            
            print(f"✓ Completed in {execution_time:.3f}s, returned {row_count} rows")
            
        except Exception as e:
            execution_time = time.time() - start_time
            benchmark_result = {
                "query_name": query.name,
                "description": query.description,
                "table_name": table_name,
                "execution_time_seconds": round(execution_time, 3),
                "row_count": 0,
                "status": "error",
                "error": str(e),
                "full_result": None
            }
            print(f"✗ Failed after {execution_time:.3f}s: {e}")
        
        self.results.append(benchmark_result)
        return benchmark_result
    
    def create_join_table(self, base_table_name: str, join_table_suffix: str = "_join") -> str:
        """Create a second table for join testing."""
        join_table_name = base_table_name + join_table_suffix
        full_base_table = f"{self.schema}.{base_table_name}"
        full_join_table = f"{self.schema}.{join_table_name}"
        
        print(f"Creating join table {full_join_table} from {full_base_table}...")
        
        # Create join table with slightly modified data
        create_join_query = f"""
        CREATE OR REPLACE TABLE {full_join_table}
        USING ICEBERG
        AS
        SELECT 
            id,
            CONCAT('join_', text) as text
        FROM {full_base_table}
        WHERE id <= (SELECT COUNT(*) * 0.8 FROM {full_base_table})
        """
        
        execute_query_on_cluster(self.client, create_join_query)
        print(f"✓ Join table created: {full_join_table}")
        return join_table_name
    
    def run_benchmark_suite(self, table_name: str, queries: List[BenchmarkQuery]) -> List[Dict]:
        """Run a suite of benchmark queries."""
        print(f"\n=== Running Benchmark Suite on {self.schema}.{table_name} ===\n")
        
        suite_results = []
        for query in queries:
            result = self.run_query(query, table_name)
            suite_results.append(result)
            print()  # Add spacing between queries
        
        self._print_summary(suite_results)
        return suite_results
    
    def _print_summary(self, results: List[Dict]):
        """Print a summary of benchmark results."""
        print("=== Benchmark Summary ===")
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]
        
        print(f"Total queries: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            total_time = sum(r["execution_time_seconds"] for r in successful)
            avg_time = total_time / len(successful)
            print(f"Total execution time: {total_time:.3f}s")
            print(f"Average execution time: {avg_time:.3f}s")
            
            print("\nPerformance breakdown:")
            for result in successful:
                print(f"  {result['query_name']}: {result['execution_time_seconds']:.3f}s")
        
        if failed:
            print(f"\nFailed queries:")
            for result in failed:
                print(f"  {result['query_name']}: {result['error']}")


# Predefined benchmark queries
BENCHMARK_QUERIES = {
    "full_scan": BenchmarkQuery(
        name="Full Table Scan",
        description="Count all rows in the table",
        query_template="SELECT COUNT(*) as row_count FROM {table_name}"
    ),
    
    "text_search": BenchmarkQuery(
        name="Text Search",
        description="Search for specific text pattern in the text column",
        query_template="SELECT COUNT(*) as matches FROM {table_name} WHERE text LIKE '%{search_pattern}%'",
    ),
    
    "range_scan": BenchmarkQuery(
        name="ID Range Scan",
        description="Select rows within an ID range",
        query_template="SELECT COUNT(*) as count FROM {table_name} WHERE id BETWEEN {start_id} AND {end_id}"
    ),
    
    "top_n": BenchmarkQuery(
        name="Top N Rows",
        description="Select top N rows ordered by ID",
        query_template="SELECT id, LEFT(text, 100) as text_preview FROM {table_name} ORDER BY id LIMIT {limit}"
    ),
    
    "aggregation": BenchmarkQuery(
        name="Text Length Aggregation",
        description="Aggregate statistics on text length",
        query_template="""
        SELECT 
            MIN(LENGTH(text)) as min_length,
            MAX(LENGTH(text)) as max_length,
            AVG(LENGTH(text)) as avg_length,
            COUNT(*) as total_rows
        FROM {table_name}
        """
    ),
    
    "random_sample": BenchmarkQuery(
        name="Random Sample",
        description="Select a random sample of rows",
        query_template="SELECT id, LEFT(text, 50) as text_preview FROM {table_name} TABLESAMPLE ({sample_percent} PERCENT) LIMIT {limit}"
    ),
    
    "deduplication": BenchmarkQuery(
        name="Deduplication Analysis",
        description="Analyze duplicate text values and test DISTINCT performance",
        query_template="""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT text) as unique_texts,
            COUNT(*) - COUNT(DISTINCT text) as duplicate_count,
            ROUND((COUNT(*) - COUNT(DISTINCT text)) * 100.0 / COUNT(*), 2) as duplicate_percentage
        FROM {table_name}
        """
    ),
    
    "join_test": BenchmarkQuery(
        name="Inner Join Test",
        description="Join with a second table on primary key",
        query_template="""
        SELECT 
            *
        FROM {table_name} a
        JOIN {join_table_name} b ON a.id = b.id
        """
    )
}


def run_standard_benchmark(table_name: str, schema: str = DEFAULT_SCHEMA) -> List[Dict]:
    """
    Run a standard set of benchmark queries on a table.
    
    Args:
        table_name: Name of the table to benchmark
        schema: Schema containing the table
    
    Returns:
        List of benchmark results
    """
    runner = BenchmarkRunner(schema)
    
    # Create join table for join test
    join_table_name = runner.create_join_table(table_name)
    
    # Define standard benchmark suite
    queries = [
        BENCHMARK_QUERIES["full_scan"],
        BENCHMARK_QUERIES["aggregation"],
        create_parameterized_query(BENCHMARK_QUERIES["range_scan"], start_id=BENCHMARK_RANGE_START, end_id=BENCHMARK_RANGE_END),
        create_parameterized_query(BENCHMARK_QUERIES["top_n"], limit=BENCHMARK_TOP_N_LIMIT),
        create_parameterized_query(BENCHMARK_QUERIES["text_search"], search_pattern=BENCHMARK_TEXT_SEARCH_PATTERN),
        create_parameterized_query(BENCHMARK_QUERIES["random_sample"], sample_percent=BENCHMARK_SAMPLE_PERCENT, limit=50),
        BENCHMARK_QUERIES["deduplication"],
        create_parameterized_query(BENCHMARK_QUERIES["join_test"], join_table_name=f"{schema}.{join_table_name}")
    ]
    
    return runner.run_benchmark_suite(table_name, queries)


# Helper function to create parameterized queries
def create_parameterized_query(base_query: BenchmarkQuery, **params) -> BenchmarkQuery:
    """Create a new query with parameters pre-filled."""
    formatted_template = base_query.query_template
    for key, value in params.items():
        formatted_template = formatted_template.replace(f"{{{key}}}", str(value))
    
    return BenchmarkQuery(
        name=f"{base_query.name} ({', '.join(f'{k}={v}' for k, v in params.items())})",
        description=base_query.description,
        query_template=formatted_template,
        expected_result_type=base_query.expected_result_type
    )


if __name__ == "__main__":
    # Example usage
    print("Running standard benchmark on a test table...")
    results = run_standard_benchmark("benchmark_test")
    print("Benchmark completed!")