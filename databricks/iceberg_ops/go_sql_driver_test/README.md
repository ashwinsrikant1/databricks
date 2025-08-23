# Databricks Go SQL Driver Timing Test

This Go application demonstrates how to use the Databricks Go SQL driver to execute queries and capture detailed timing information including start and end times.

## Features

- Query execution with precise timing measurement
- Built-in logging for detailed operation tracking
- Query ID and Connection ID capture
- Multiple timing measurements (query execution, data processing, total duration)
- Correlation ID tracking for request tracing

## Setup

1. Set the required environment variables:
   ```bash
   export DATABRICKS_TOKEN="your_databricks_token"
   export DATABRICKS_HOSTNAME="your_workspace.databricks.com"
   export DATABRICKS_ENDPOINT="your_sql_endpoint_id"
   ```

2. Run the application:
   ```bash
   go run main.go
   ```

## Key Timing Capabilities

### Built-in Logger Timing
The driver includes `logger.Track()` and `logger.Duration()` functions for built-in timing:
```go
msg, start := logger.Track("Query Execution")
defer logger.Duration(msg, start)
```

### Manual Timing
Precise start/end time capture using Go's `time.Now()`:
```go
startTime := time.Now()
// ... execute query ...
endTime := time.Now()
duration := endTime.Sub(startTime)
```

### Query and Connection ID Tracking
Capture unique identifiers for each query and connection:
```go
queryIDCallback := func(id string) {
    fmt.Printf("Query ID: %s\n", id)
}
ctx = driverctx.NewContextWithQueryIdCallback(ctx, queryIDCallback)
```

## Output Example

The application will output timing information like:
```
=== Executing Query: SELECT 1 as test_column ===
Query Start Time: 2024-01-15T10:30:45.123456789Z
Query ID: 01234567-89ab-cdef-0123-456789abcdef
Query End Time: 2024-01-15T10:30:45.456789012Z
Total Execution Duration: 333.332223ms

--- Timing Summary ---
Start: 10:30:45.123456
End: 10:30:45.456789
Query Execution: 333.332223ms
Data Processing: 1.234567ms
Total Duration: 334.566790ms
```

This provides comprehensive timing data for analyzing query performance and tracking execution patterns.