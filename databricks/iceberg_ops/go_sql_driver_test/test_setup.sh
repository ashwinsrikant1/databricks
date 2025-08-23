#!/bin/bash

# Test setup script for Databricks Go SQL Driver timing test
# This script shows how to set up environment variables and run the test

echo "=== Databricks Go SQL Driver Timing Test Setup ==="
echo ""

# Check if environment variables are set
if [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ DATABRICKS_TOKEN is not set"
    echo "   Set it with: export DATABRICKS_TOKEN='your_token_here'"
    MISSING_ENV=true
else
    echo "✅ DATABRICKS_TOKEN is set"
fi

if [ -z "$DATABRICKS_HOSTNAME" ]; then
    echo "❌ DATABRICKS_HOSTNAME is not set"
    echo "   Set it with: export DATABRICKS_HOSTNAME='your_workspace.databricks.com'"
    MISSING_ENV=true
else
    echo "✅ DATABRICKS_HOSTNAME is set"
fi

if [ -z "$DATABRICKS_ENDPOINT" ]; then
    echo "❌ DATABRICKS_ENDPOINT is not set"
    echo "   Set it with: export DATABRICKS_ENDPOINT='your_sql_endpoint_id'"
    MISSING_ENV=true
else
    echo "✅ DATABRICKS_ENDPOINT is set"
fi

echo ""

if [ "$MISSING_ENV" = true ]; then
    echo "Please set the missing environment variables and run this script again."
    echo ""
    echo "Example setup:"
    echo "export DATABRICKS_TOKEN='dapi_your_token_here'"
    echo "export DATABRICKS_HOSTNAME='your-workspace.databricks.com'"
    echo "export DATABRICKS_ENDPOINT='1234567890abcdef'"
    echo ""
    exit 1
fi

echo "=== Environment Setup Complete ==="
echo ""

# Build the application
echo "Building application..."
if go build -o timing-test main.go; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "=== Ready to run timing test ==="
echo "Run: ./timing-test"
echo ""
echo "This will execute several test queries and show detailed timing information including:"
echo "- Query start and end times (nanosecond precision)"
echo "- Total execution duration"
echo "- Data processing time"
echo "- Query and Connection IDs"
echo "- Built-in driver timing logs"