"""
Simple dataset generator for Iceberg benchmarking.
Creates tables with schema: id BIGINT, text STRING
"""

import sys
import os
import random
import string
import hashlib
import time
import json
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any, Union
from decimal import Decimal

# Add databricks-utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'databricks-utils'))
from cluster_execution import get_e2_demo_client, execute_query_on_cluster

# Import configuration
from config import (
    DEFAULT_SCHEMA,
    DEFAULT_NUM_ROWS,
    DEFAULT_TEXT_LENGTH,
    DEFAULT_TABLE_NAME,
    TARGET_SIZE_GB,
    BATCH_SIZE,
    TEXT_GENERATION_SEED,
    USE_RANDOM_SEED_PER_ROW
)


# Cache for base 1KB string to avoid regenerating
_BASE_1KB_STRING = None

# Supported data types and their configurations
SUPPORTED_TYPES = {
    'bigint': {'sql_type': 'BIGINT', 'python_type': int},
    'int': {'sql_type': 'INT', 'python_type': int},
    'smallint': {'sql_type': 'SMALLINT', 'python_type': int},
    'tinyint': {'sql_type': 'TINYINT', 'python_type': int},
    'double': {'sql_type': 'DOUBLE', 'python_type': float},
    'float': {'sql_type': 'FLOAT', 'python_type': float},
    'decimal': {'sql_type': 'DECIMAL(10,2)', 'python_type': Decimal},
    'string': {'sql_type': 'STRING', 'python_type': str},
    'varchar': {'sql_type': 'VARCHAR(255)', 'python_type': str},
    'char': {'sql_type': 'CHAR(10)', 'python_type': str},
    'boolean': {'sql_type': 'BOOLEAN', 'python_type': bool},
    'date': {'sql_type': 'DATE', 'python_type': date},
    'timestamp': {'sql_type': 'TIMESTAMP', 'python_type': datetime},
    'binary': {'sql_type': 'BINARY', 'python_type': bytes},
    'variant': {'sql_type': 'VARIANT', 'python_type': dict}
}

# Default schema configurations for quick testing
DEFAULT_SCHEMAS = {
    'simple': [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'text', 'type': 'string', 'length': 1024}
    ],
    'mixed_types': [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'name', 'type': 'string', 'length': 50},
        {'name': 'age', 'type': 'int', 'min_value': 18, 'max_value': 100},
        {'name': 'salary', 'type': 'decimal', 'min_value': 30000, 'max_value': 200000},
        {'name': 'is_active', 'type': 'boolean'},
        {'name': 'created_date', 'type': 'date'},
        {'name': 'last_login', 'type': 'timestamp'}
    ],
    'with_json_string': [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'user_name', 'type': 'string', 'length': 30},
        {'name': 'score', 'type': 'double', 'min_value': 0.0, 'max_value': 100.0},
        {'name': 'metadata_json', 'type': 'string', 'length': 500, 'json_data': True},
        {'name': 'created_at', 'type': 'timestamp'}
    ],
    'with_variant': [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'user_name', 'type': 'string', 'length': 30},
        {'name': 'score', 'type': 'double', 'min_value': 0.0, 'max_value': 100.0},
        {'name': 'metadata', 'type': 'variant'},
        {'name': 'created_at', 'type': 'timestamp'}
    ],
    'comprehensive': [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'tiny_num', 'type': 'tinyint', 'min_value': 0, 'max_value': 255},
        {'name': 'small_num', 'type': 'smallint', 'min_value': 0, 'max_value': 32767},
        {'name': 'int_num', 'type': 'int', 'min_value': 1, 'max_value': 1000000},
        {'name': 'big_num', 'type': 'bigint', 'min_value': 1, 'max_value': 9999999999},
        {'name': 'float_num', 'type': 'float', 'min_value': 0.0, 'max_value': 1000.0},
        {'name': 'double_num', 'type': 'double', 'min_value': 0.0, 'max_value': 10000.0},
        {'name': 'decimal_num', 'type': 'decimal', 'precision': 12, 'scale': 3, 'min_value': 0, 'max_value': 999999},
        {'name': 'name', 'type': 'string', 'length': 100},
        {'name': 'code', 'type': 'varchar', 'length': 20},
        {'name': 'category', 'type': 'char', 'length': 10},
        {'name': 'is_active', 'type': 'boolean'},
        {'name': 'birth_date', 'type': 'date'},
        {'name': 'last_seen', 'type': 'timestamp'},
        {'name': 'binary_data', 'type': 'binary', 'length': 50}
    ]
}

def generate_base_1kb_string(seed: int = 42) -> str:
    """Generate a base 1KB string that will be repeated to create larger text."""
    random.seed(seed)
    
    # Mix of different character sets to reduce compression
    chars = string.ascii_letters + string.digits + string.punctuation + ' \n\t'
    
    # Generate 512 bytes of random characters
    base_text = ''.join(random.choices(chars, k=512))
    
    # Add 512 bytes of structured content with hash patterns
    structured_parts = []
    for i in range(5):  # 5 hash blocks ~= 320 chars
        hash_input = f"base_{seed}_{i}_{random.random()}"
        hash_val = hashlib.sha256(hash_input.encode()).hexdigest()
        structured_parts.append(f"data_{hash_val}_{i} ")
    
    structured_text = ''.join(structured_parts)
    
    # Combine and pad to exactly 1KB (1024 bytes)
    combined = base_text + structured_text
    if len(combined) > 1024:
        combined = combined[:1024]
    elif len(combined) < 1024:
        # Pad with random chars to reach exactly 1024 bytes
        padding_needed = 1024 - len(combined)
        combined += ''.join(random.choices(chars, k=padding_needed))
    
    return combined


def generate_variant_data(seed: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate random JSON-like data for VARIANT columns.
    Creates nested objects, arrays, and various data types.
    """
    if seed is not None:
        random.seed(seed)
    
    # Different variant patterns
    patterns = [
        # Simple flat object
        lambda: {
            'type': random.choice(['user', 'order', 'product', 'event']),
            'value': random.randint(1, 1000),
            'status': random.choice(['active', 'inactive', 'pending'])
        },
        # Nested object
        lambda: {
            'user': {
                'id': random.randint(1000, 9999),
                'preferences': {
                    'theme': random.choice(['dark', 'light']),
                    'notifications': random.choice([True, False])
                }
            },
            'timestamp': datetime.now().isoformat()
        },
        # Array with mixed types
        lambda: {
            'items': [random.randint(1, 100) for _ in range(random.randint(2, 5))],
            'tags': [f'tag_{i}' for i in range(random.randint(1, 4))],
            'metadata': {
                'version': f'{random.randint(1, 5)}.{random.randint(0, 9)}',
                'source': random.choice(['api', 'web', 'mobile'])
            }
        },
        # Complex nested structure
        lambda: {
            'analytics': {
                'page_views': random.randint(100, 10000),
                'bounce_rate': round(random.uniform(0.1, 0.8), 2),
                'geo': {
                    'country': random.choice(['US', 'CA', 'UK', 'DE', 'FR']),
                    'city': random.choice(['New York', 'London', 'Paris', 'Berlin'])
                }
            },
            'features': [f'feature_{chr(97+i)}' for i in range(random.randint(2, 6))]
        }
    ]
    
    return random.choice(patterns)()


def generate_random_value(column_config: Dict[str, Any], seed: Optional[int] = None) -> Any:
    """
    Generate a random value based on column configuration.
    
    Args:
        column_config: Dictionary containing column type and constraints
        seed: Random seed for reproducible results
    
    Returns:
        Generated value of appropriate type
    """
    if seed is not None:
        random.seed(seed)
    
    col_type = column_config['type'].lower()
    
    if col_type in ['bigint', 'int', 'smallint', 'tinyint']:
        min_val = column_config.get('min_value', 1)
        max_val = column_config.get('max_value', 1000000)
        if col_type == 'tinyint':
            max_val = min(max_val, 255)
        elif col_type == 'smallint':
            max_val = min(max_val, 32767)
        return random.randint(min_val, max_val)
    
    elif col_type in ['double', 'float']:
        min_val = column_config.get('min_value', 0.0)
        max_val = column_config.get('max_value', 1000.0)
        return round(random.uniform(min_val, max_val), 3)
    
    elif col_type == 'decimal':
        min_val = float(column_config.get('min_value', 0.0))
        max_val = float(column_config.get('max_value', 1000.0))
        value = round(random.uniform(min_val, max_val), 2)
        return Decimal(str(value))
    
    elif col_type in ['string', 'varchar', 'char']:
        length = column_config.get('length', 100)
        
        # Check if this should be JSON data stored as string
        if column_config.get('json_data', False):
            json_obj = generate_variant_data(seed)
            json_str = json.dumps(json_obj, separators=(',', ':'))  # Compact JSON
            # Truncate if too long
            if len(json_str) > length:
                json_str = json_str[:length-3] + '...'
            return json_str
        
        if col_type == 'char':
            # CHAR fields should be exactly the specified length
            return generate_random_text(length, seed)
        else:
            # STRING and VARCHAR can be variable length up to max
            actual_length = random.randint(1, length)
            return generate_random_text(actual_length, seed)
    
    elif col_type == 'boolean':
        return random.choice([True, False])
    
    elif col_type == 'date':
        # Generate dates within last 5 years
        start_date = date.today() - timedelta(days=5*365)
        random_days = random.randint(0, 5*365)
        return start_date + timedelta(days=random_days)
    
    elif col_type == 'timestamp':
        # Generate timestamps within last year
        start_time = datetime.now() - timedelta(days=365)
        random_seconds = random.randint(0, 365*24*3600)
        return start_time + timedelta(seconds=random_seconds)
    
    elif col_type == 'binary':
        length = column_config.get('length', 20)
        return random.randbytes(length)
    
    elif col_type == 'variant':
        return generate_variant_data(seed)
    
    else:
        raise ValueError(f"Unsupported column type: {col_type}")


def generate_random_text(length: int, seed: Optional[int] = None) -> str:
    """
    Generate random text of specified length by repeating a base 1KB string.
    Much faster than generating unique content for each position.
    """
    global _BASE_1KB_STRING
    
    # Generate base 1KB string once and cache it
    if _BASE_1KB_STRING is None:
        base_seed = seed if seed is not None else TEXT_GENERATION_SEED
        _BASE_1KB_STRING = generate_base_1kb_string(base_seed)
    
    if length <= 1024:
        # For small lengths, just return a portion of the base string
        return _BASE_1KB_STRING[:length]
    
    # For larger lengths, repeat the 1KB string
    full_repeats = length // 1024
    remainder = length % 1024
    
    # Build the text by repeating the base string
    result = _BASE_1KB_STRING * full_repeats
    
    # Add remainder if needed
    if remainder > 0:
        result += _BASE_1KB_STRING[:remainder]
    
    # Add a small unique identifier based on seed to make each row slightly different
    if seed is not None:
        # Replace a small portion with seed-specific content to maintain some uniqueness
        unique_marker = f"_row_{seed}_"
        if len(result) >= len(unique_marker):
            # Insert unique marker at a position based on seed
            pos = seed % (len(result) - len(unique_marker)) if len(result) > len(unique_marker) else 0
            result = result[:pos] + unique_marker + result[pos + len(unique_marker):]
    
    return result


def format_sql_value(value: Any, col_type: str) -> str:
    """
    Format a Python value as a SQL literal string.
    
    Args:
        value: The value to format
        col_type: The column type
    
    Returns:
        SQL literal string
    """
    if value is None:
        return 'NULL'
    
    col_type = col_type.lower()
    
    if col_type in ['bigint', 'int', 'smallint', 'tinyint', 'double', 'float', 'decimal']:
        return str(value)
    
    elif col_type in ['string', 'varchar', 'char']:
        # Escape single quotes
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"
    
    elif col_type == 'boolean':
        return 'true' if value else 'false'
    
    elif col_type == 'date':
        return f"DATE '{value.strftime('%Y-%m-%d')}'"
    
    elif col_type == 'timestamp':
        return f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    
    elif col_type == 'binary':
        # Convert bytes to hex representation
        hex_str = value.hex()
        return f"X'{hex_str}'"
    
    elif col_type == 'variant':
        # Convert dict/object to JSON string for VARIANT type
        json_str = json.dumps(value).replace("'", "''")
        return f"PARSE_JSON('{json_str}')"
    
    else:
        # Fallback: treat as string
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"


def create_table_ddl(table_name: str, schema_config: List[Dict[str, Any]], table_format: str = 'ICEBERG') -> str:
    """
    Generate CREATE TABLE DDL from schema configuration.
    
    Args:
        table_name: Name of the table
        schema_config: List of column configurations
        table_format: 'ICEBERG' or 'DELTA'
    
    Returns:
        DDL string
    """
    # Validate table format
    table_format = table_format.upper()
    if table_format not in ['ICEBERG', 'DELTA']:
        raise ValueError(f"Unsupported table format: {table_format}. Use 'ICEBERG' or 'DELTA'")
    
    # Check for VARIANT in Iceberg tables
    if table_format == 'ICEBERG':
        variant_cols = [col['name'] for col in schema_config if col['type'].lower() == 'variant']
        if variant_cols:
            raise ValueError(f"VARIANT columns not supported in Iceberg tables: {variant_cols}. Use DELTA format instead.")
    
    column_definitions = []
    
    for col in schema_config:
        col_name = col['name']
        col_type = col['type'].lower()
        
        if col_type not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported column type: {col_type}")
        
        sql_type = SUPPORTED_TYPES[col_type]['sql_type']
        
        # Handle special type configurations
        if col_type == 'decimal' and 'precision' in col:
            precision = col['precision']
            scale = col.get('scale', 2)
            sql_type = f'DECIMAL({precision},{scale})'
        elif col_type == 'varchar' and 'length' in col:
            sql_type = f'VARCHAR({col["length"]})'
        elif col_type == 'char' and 'length' in col:
            sql_type = f'CHAR({col["length"]})'
        
        column_definitions.append(f'    {col_name} {sql_type}')
    
    columns_ddl = ',\n'.join(column_definitions)
    
    return f"""
    CREATE OR REPLACE TABLE {table_name}
    (
{columns_ddl}
    )
    USING {table_format}
    """


def calculate_rows_for_size(target_size_gb: float, schema_config: List[Dict[str, Any]]) -> int:
    """
    Calculate number of rows needed to achieve target size.
    
    Args:
        target_size_gb: Target table size in GB
        avg_text_length: Average length of text field
    
    Returns:
        Number of rows needed
    """
    # Estimate bytes per row based on schema
    estimated_bytes_per_row = 50  # Base overhead
    
    for col in schema_config:
        col_type = col['type'].lower()
        if col_type in ['bigint']:
            estimated_bytes_per_row += 8
        elif col_type in ['int', 'float']:
            estimated_bytes_per_row += 4
        elif col_type in ['smallint']:
            estimated_bytes_per_row += 2
        elif col_type in ['tinyint', 'boolean']:
            estimated_bytes_per_row += 1
        elif col_type in ['double', 'timestamp']:
            estimated_bytes_per_row += 8
        elif col_type in ['date']:
            estimated_bytes_per_row += 4
        elif col_type in ['decimal']:
            estimated_bytes_per_row += 16
        elif col_type in ['string', 'varchar']:
            estimated_bytes_per_row += col.get('length', 100)
        elif col_type == 'char':
            estimated_bytes_per_row += col.get('length', 10)
        elif col_type == 'binary':
            estimated_bytes_per_row += col.get('length', 20)
        elif col_type == 'variant':
            estimated_bytes_per_row += 200  # Estimate for JSON objects
    
    target_bytes = target_size_gb * 1024 * 1024 * 1024
    return int(target_bytes / estimated_bytes_per_row)


def create_table_with_schema(
    client,
    table_name: str,
    schema_config: List[Dict[str, Any]],
    num_rows: int = DEFAULT_NUM_ROWS,
    database_schema: str = DEFAULT_SCHEMA,
    table_format: str = 'ICEBERG'
) -> dict:
    """
    Create a table (Iceberg or Delta) with custom schema and measure write performance.
    
    Args:
        client: Databricks client
        table_name: Name of the table to create
        schema_config: List of column configurations defining the table schema
        num_rows: Number of rows to generate
        database_schema: Target database schema name
        table_format: 'ICEBERG' or 'DELTA'
    
    Returns:
        Dictionary with performance metrics and results
    """
    full_table_name = f"{database_schema}.{table_name}"
    
    print(f"Creating {table_format} table {full_table_name} with {num_rows:,} rows...")
    print(f"Schema: {[f'{col["name"]}:{col["type"]}' for col in schema_config]}")
    
    # Calculate estimated data size based on schema
    estimated_row_size = sum(
        col.get('length', 100) if col['type'] in ['string', 'varchar'] else 50 
        for col in schema_config
    )
    
    # Initialize performance tracking
    performance_metrics = {
        "table_name": full_table_name,
        "num_rows": num_rows,
        "schema_config": schema_config,
        "estimated_row_size_bytes": estimated_row_size,
        "batch_size": min(BATCH_SIZE, num_rows),
        "total_data_size_mb": (num_rows * estimated_row_size) / (1024 * 1024),
        "batch_metrics": [],
        "data_generation_time_seconds": 0,
        "table_creation_time_seconds": 0,
        "total_insert_time_seconds": 0,
        "total_time_seconds": 0
    }
    
    overall_start_time = time.time()
    
    # Create table structure using schema configuration
    create_query = create_table_ddl(full_table_name, schema_config, table_format)
    
    print("Creating table structure...")
    table_create_start = time.time()
    execute_query_on_cluster(client, create_query)
    performance_metrics["table_creation_time_seconds"] = time.time() - table_create_start
    print(f"✓ Table structure created in {performance_metrics['table_creation_time_seconds']:.3f}s")
    print(f"  Columns: {', '.join([f'{col["name"]} ({col["type"]})' for col in schema_config])}")
    
    # Insert data in batches to avoid memory issues
    batch_size = min(BATCH_SIZE, num_rows)
    batches = (num_rows + batch_size - 1) // batch_size
    
    print(f"Inserting data in {batches} batches of {batch_size:,} rows each...")
    print("Performance tracking: [Batch] Data Gen Time | Insert Time | Throughput")
    
    insert_start_time = time.time()
    total_data_gen_time = 0
    
    for batch in range(batches):
        start_id = batch * batch_size + 1
        end_id = min((batch + 1) * batch_size, num_rows)
        current_batch_size = end_id - start_id + 1
        
        print(f"\nBatch {batch + 1}/{batches} (rows {start_id:,} to {end_id:,}):")
        
        # Time data generation for this batch
        data_gen_start = time.time()
        values_list = []
        for i in range(current_batch_size):
            row_id = start_id + i
            # Generate values for each column
            row_values = []
            for col in schema_config:
                # Use row_id combined with column name as seed for reproducible but varied data
                col_seed = hash(f"{row_id}_{col['name']}") % (2**31)
                
                # Handle primary key columns specially
                if col.get('primary_key', False):
                    value = row_id
                else:
                    value = generate_random_value(col, seed=col_seed)
                
                formatted_value = format_sql_value(value, col['type'])
                row_values.append(formatted_value)
            
            values_list.append(f"({', '.join(row_values)})")
        
        data_gen_time = time.time() - data_gen_start
        total_data_gen_time += data_gen_time
        
        values_clause = ",\n".join(values_list)
        
        insert_query = f"""
        INSERT INTO {full_table_name}
        VALUES
        {values_clause}
        """
        
        # Time the actual INSERT operation
        insert_batch_start = time.time()
        execute_query_on_cluster(client, insert_query)
        insert_batch_time = time.time() - insert_batch_start
        
        # Calculate throughput metrics
        batch_data_mb = (current_batch_size * estimated_row_size) / (1024 * 1024)
        total_batch_time = data_gen_time + insert_batch_time
        rows_per_second = current_batch_size / total_batch_time if total_batch_time > 0 else 0
        mb_per_second = batch_data_mb / total_batch_time if total_batch_time > 0 else 0
        
        # Store batch metrics
        batch_metrics = {
            "batch_number": batch + 1,
            "rows_in_batch": current_batch_size,
            "data_generation_time": data_gen_time,
            "insert_time": insert_batch_time,
            "total_batch_time": total_batch_time,
            "batch_data_mb": batch_data_mb,
            "rows_per_second": rows_per_second,
            "mb_per_second": mb_per_second
        }
        performance_metrics["batch_metrics"].append(batch_metrics)
        
        print(f"  Data gen: {data_gen_time:.3f}s | Insert: {insert_batch_time:.3f}s | {rows_per_second:.1f} rows/s | {mb_per_second:.2f} MB/s")
    
    performance_metrics["total_insert_time_seconds"] = time.time() - insert_start_time
    performance_metrics["data_generation_time_seconds"] = total_data_gen_time
    performance_metrics["total_time_seconds"] = time.time() - overall_start_time
    
    # Get final table stats - generic query that works with any schema
    stats_query = f"SELECT COUNT(*) as row_count FROM {full_table_name}"
    
    stats_result = execute_query_on_cluster(client, stats_query)
    performance_metrics["table_stats"] = stats_result
    
    # Calculate overall performance metrics
    total_time = performance_metrics["total_time_seconds"]
    insert_time = performance_metrics["total_insert_time_seconds"]
    data_gen_time = performance_metrics["data_generation_time_seconds"]
    total_data_mb = performance_metrics["total_data_size_mb"]
    
    overall_rows_per_second = num_rows / total_time if total_time > 0 else 0
    overall_mb_per_second = total_data_mb / total_time if total_time > 0 else 0
    insert_rows_per_second = num_rows / insert_time if insert_time > 0 else 0
    insert_mb_per_second = total_data_mb / insert_time if insert_time > 0 else 0
    
    performance_metrics.update({
        "overall_rows_per_second": overall_rows_per_second,
        "overall_mb_per_second": overall_mb_per_second,
        "insert_rows_per_second": insert_rows_per_second,
        "insert_mb_per_second": insert_mb_per_second
    })
    
    # Print comprehensive performance summary
    print("\n" + "="*80)
    print("📊 WRITE PERFORMANCE SUMMARY")
    print("="*80)
    print(f"Table: {full_table_name}")
    print(f"Rows inserted: {num_rows:,}")
    print(f"Schema: {len(schema_config)} columns")
    print(f"Estimated row size: {estimated_row_size:,} bytes")
    print(f"Total data size: {total_data_mb:.2f} MB")
    print(f"Batch size: {batch_size:,} rows")
    print(f"Number of batches: {batches}")
    print()
    print("📋 SCHEMA DETAILS:")
    for col in schema_config:
        extra_info = []
        if 'length' in col:
            extra_info.append(f"length={col['length']}")
        if col.get('primary_key'):
            extra_info.append("PK")
        extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
        print(f"  {col['name']}: {col['type'].upper()}{extra_str}")
    print()
    print("⏱️  TIMING BREAKDOWN:")
    print(f"Table creation:    {performance_metrics['table_creation_time_seconds']:8.3f}s")
    print(f"Data generation:   {data_gen_time:8.3f}s ({(data_gen_time/total_time)*100:.1f}%)")
    print(f"Insert operations: {insert_time:8.3f}s ({(insert_time/total_time)*100:.1f}%)")
    print(f"Total time:        {total_time:8.3f}s")
    print()
    print("🚀 THROUGHPUT METRICS:")
    print(f"Overall:     {overall_rows_per_second:8.1f} rows/s | {overall_mb_per_second:8.2f} MB/s")
    print(f"Insert only: {insert_rows_per_second:8.1f} rows/s | {insert_mb_per_second:8.2f} MB/s")
    print()
    print("📈 BATCH PERFORMANCE:")
    print("Batch | Rows | Data Gen | Insert | Total | Throughput")
    print("-" * 62)
    for batch_data in performance_metrics["batch_metrics"]:
        print(f"{batch_data['batch_number']:5} | {batch_data['rows_in_batch']:4} | "
              f"{batch_data['data_generation_time']:8.3f}s | {batch_data['insert_time']:7.3f}s | "
              f"{batch_data['total_batch_time']:6.3f}s | {batch_data['rows_per_second']:4.1f} rows/s")
    print("="*80)
    
    return performance_metrics


# Convenience functions that maintain backward compatibility
def create_iceberg_table_simple(
    client,
    table_name: str,
    num_rows: int = DEFAULT_NUM_ROWS,
    text_length: int = DEFAULT_TEXT_LENGTH,
    schema: str = DEFAULT_SCHEMA
) -> dict:
    """
    Create a simple Iceberg table with id/text schema (backward compatibility).
    """
    simple_schema = [
        {'name': 'id', 'type': 'bigint', 'primary_key': True},
        {'name': 'text', 'type': 'string', 'length': text_length}
    ]
    return create_table_with_schema(client, table_name, simple_schema, num_rows, schema, 'ICEBERG')


def create_table_with_custom_schema(
    table_name: str,
    schema_config: List[Dict[str, Any]],
    num_rows: int = DEFAULT_NUM_ROWS,
    database_schema: str = DEFAULT_SCHEMA,
    table_format: str = 'ICEBERG'
) -> dict:
    """
    Create table with custom schema configuration.
    
    Args:
        table_name: Name of the table to create
        schema_config: List of column configurations
        num_rows: Number of rows to generate
        database_schema: Target database schema name
        table_format: 'ICEBERG' or 'DELTA'
    
    Returns:
        Performance metrics dictionary
    """
    client = get_e2_demo_client()
    return create_table_with_schema(client, table_name, schema_config, num_rows, database_schema, table_format)


def create_table_by_size(
    table_name: str = DEFAULT_TABLE_NAME,
    target_size_gb: float = TARGET_SIZE_GB,
    schema_config: Optional[List[Dict[str, Any]]] = None,
    database_schema: str = DEFAULT_SCHEMA,
    table_format: str = 'ICEBERG'
) -> dict:
    """
    Create table targeting a specific size in GB.
    
    Args:
        table_name: Name of the table to create
        target_size_gb: Target size in GB
        schema_config: Schema configuration (defaults to simple id/text schema)
        database_schema: Target database schema name
        table_format: 'ICEBERG' or 'DELTA'
    
    Returns:
        Query execution results
    """
    if schema_config is None:
        schema_config = DEFAULT_SCHEMAS['simple']
    
    client = get_e2_demo_client()
    num_rows = calculate_rows_for_size(target_size_gb, schema_config)
    
    print(f"Target size: {target_size_gb} GB")
    print(f"Calculated rows needed: {num_rows:,}")
    print(f"Schema: {len(schema_config)} columns")
    print(f"Format: {table_format}")
    
    return create_table_with_schema(client, table_name, schema_config, num_rows, database_schema, table_format)


def create_table_by_rows(
    table_name: str = DEFAULT_TABLE_NAME,
    num_rows: int = DEFAULT_NUM_ROWS,
    schema_config: Optional[List[Dict[str, Any]]] = None,
    database_schema: str = DEFAULT_SCHEMA,
    table_format: str = 'ICEBERG'
) -> dict:
    """
    Create table with a specific number of rows.
    
    Args:
        table_name: Name of the table to create
        num_rows: Number of rows to generate
        schema_config: Schema configuration (defaults to simple id/text schema)
        database_schema: Target database schema name
        table_format: 'ICEBERG' or 'DELTA'
    
    Returns:
        Query execution results
    """
    if schema_config is None:
        schema_config = DEFAULT_SCHEMAS['simple']
    
    client = get_e2_demo_client()
    return create_table_with_schema(client, table_name, schema_config, num_rows, database_schema, table_format)


def create_table_with_config(schema_name: str = 'simple', table_format: str = 'ICEBERG'):
    """
    Create table using configuration variables and specified schema.
    
    Args:
        schema_name: Name of predefined schema ('simple', 'mixed_types', 'with_json_string', 'comprehensive')
        table_format: 'ICEBERG' or 'DELTA'
    """
    schema_config = DEFAULT_SCHEMAS.get(schema_name, DEFAULT_SCHEMAS['simple'])
    
    if TARGET_SIZE_GB:
        print(f"Creating table by size: {TARGET_SIZE_GB} GB with '{schema_name}' schema using {table_format}")
        return create_table_by_size(schema_config=schema_config, table_format=table_format)
    else:
        print(f"Creating table by rows: {DEFAULT_NUM_ROWS:,} with '{schema_name}' schema using {table_format}")
        return create_table_by_rows(schema_config=schema_config, table_format=table_format)


if __name__ == "__main__":
    # Example usage with different schema configurations
    print("Available schemas:")
    for name, config in DEFAULT_SCHEMAS.items():
        print(f"  {name}: {len(config)} columns - {', '.join([f'{col["name"]}:{col["type"]}' for col in config])}")
    
    print("\nCreating table with 'mixed_types' schema...")
    result = create_table_with_config('mixed_types')
    print("Done!")