"""
Configuration file for Iceberg benchmarking system.
Modify these variables to control dataset generation and benchmarking behavior.
"""

# Database Configuration
DEFAULT_SCHEMA = "users.ashwin_srikant"  # Target schema for all tables

# Dataset Generation Configuration
DEFAULT_NUM_ROWS = 10000  # Number of rows to generate
DEFAULT_TEXT_LENGTH = 1024  # Length of text column in bytes (1KB)
DEFAULT_TABLE_NAME = "iceberg_benchmark_optimized_test"  # Default table name

# Alternative size-based configuration
TARGET_SIZE_GB = None  # Set to a float value (e.g., 1.5) to generate by size instead of row count

# Batch Configuration for Large Datasets
BATCH_SIZE = 10000  # Number of rows to insert per batch (for memory management)

# Text Generation Configuration
TEXT_GENERATION_SEED = 42  # Seed for reproducible text generation
USE_RANDOM_SEED_PER_ROW = True  # Use row ID as seed for varied but reproducible text

# Benchmarking Configuration
BENCHMARK_SAMPLE_PERCENT = 1  # Percentage for random sample queries
BENCHMARK_TOP_N_LIMIT = 100  # Limit for top N queries
BENCHMARK_RANGE_START = 1  # Start ID for range scans
BENCHMARK_RANGE_END = 1000  # End ID for range scans
BENCHMARK_TEXT_SEARCH_PATTERN = "data_"  # Pattern to search for in text

# Performance Configuration
ENABLE_QUERY_CACHING = False  # Whether to enable Spark query caching
SHOW_QUERY_PLANS = False  # Whether to show query execution plans