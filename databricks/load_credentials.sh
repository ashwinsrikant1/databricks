#!/bin/bash
# Source this file to load your local databricks credentials
# Usage: source load_credentials.sh

# Load databricks-utils credentials
if [ -f "databricks-utils/.env.local" ]; then
    export $(grep -v '^#' databricks-utils/.env.local | xargs)
    echo "Loaded databricks-utils credentials"
fi

# Load iceberg_ops credentials
if [ -f "iceberg_ops/.env.local" ]; then
    export $(grep -v '^#' iceberg_ops/.env.local | xargs)
    echo "Loaded iceberg_ops credentials"
fi

echo "Environment loaded. Current DATABRICKS_HOST: ${DATABRICKS_HOST:-not set}"