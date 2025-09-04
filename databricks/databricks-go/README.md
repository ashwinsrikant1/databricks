# Databricks Go SQL Driver Query History API Test

This Go application demonstrates how to use the Databricks Go SQL driver to execute queries and retrieve detailed timing information using the undocumented Query History REST API. This approach provides immediate access to precise query timing data without the delays associated with `system.query.history`.

## Features

- Execute SQL queries using the Databricks Go SQL driver
- Capture query IDs via driver callbacks
- Retrieve detailed query timing information using the Query History REST API (`/api/2.0/sql/history/queries/{id}`)
- Compare client-side timing measurements with server-side execution data
- Real-time access to query metadata and performance metrics

## What This Code Does

The application performs the following steps:

1. **Execute Query**: Runs a SQL query using the Databricks Go driver and captures the query ID
2. **Client Timing**: Records client-side execution timing using Go's `time.Now()`
3. **REST API Call**: Immediately calls the undocumented Query History API to retrieve server-side timing data
4. **Compare Results**: Shows both client-side and server-side timing measurements

## Query History API Details

The code uses the public but undocumented REST API endpoint:
```
GET /api/2.0/sql/history/queries/{query_id}
```

### API Response Structure

The API returns a JSON object with comprehensive query information:

```json
{
  "query_id": "01f08938-cb0b-1cab-8942-4fad144663d3",
  "status": "FINISHED",
  "query_text": "SELECT current_timestamp() as query_time, 'test' as test_id, 42 as magic_number",
  "query_start_time_ms": 1756953746624,
  "execution_end_time_ms": 1756953746739,
  "query_end_time_ms": 1756953746739,
  "duration": 115,
  "user_id": 4122156771554631,
  "user_name": "ashwin.srikant@databricks.com",
  "user_display_name": "Ashwin Srikant",
  "endpoint_id": "8baced1ff014912d",
  "warehouse_id": "8baced1ff014912d",
  "rows_produced": 1,
  "statement_type": "SELECT",
  "client_application": "Databricks SQL Driver for Go",
  "channel_used": {
    "name": "CHANNEL_NAME_PREVIEW",
    "dbsql_version": "2025.25"
  },
  "plans_state": "EXISTS",
  "is_final": true,
  "is_cancelable": false,
  "canSubscribeToLiveQuery": true
}
```

### Key Timing Fields

- **`query_start_time_ms`**: Precise server-side query start time (Unix timestamp in milliseconds)
- **`execution_end_time_ms`**: When query execution completed on the server
- **`query_end_time_ms`**: When query fully completed (including result processing)
- **`duration`**: Total execution duration in milliseconds

### Advantages Over `system.query.history`

1. **Immediate Availability**: Data is available immediately after query completion
2. **No Delay**: Unlike `system.query.history` which can have significant delays
3. **Precise Timestamps**: Millisecond-precision timing data
4. **Rich Metadata**: Comprehensive query execution details
5. **Real-time Access**: No need to poll or wait for data propagation

## Setup

1. **Configure credentials in the code**: Edit the variables at the top of each `.go` file and replace the empty strings with your values:
   ```go
   // TODO: Configure your Databricks workspace credentials below
   var (
       // TODO: Replace with your Databricks Personal Access Token
       databricksToken = "dapi..."
       
       // TODO: Replace with your workspace hostname (without https://)
       databricksHostname = "your-workspace.cloud.databricks.com"
       
       // TODO: Replace with your SQL warehouse endpoint ID
       databricksEndpoint = "your-endpoint-id"
   )
   ```

2. Ensure your SQL warehouse is running

3. Run the application (no environment variables needed):
   ```bash
   go run query_timing.go
   ```

## Example Output

```
=== Testing Undocumented REST API: /sql/history/queries/{id} ===
🚀 Executing test query: SELECT current_timestamp() as query_time, 'rest_api_test_1756953746' as test_id, 42 as magic_number
📋 Captured Query ID: 01f08938-cb0b-1cab-8942-4fad144663d3
✅ Query executed in 621.979917ms
📄 Result: 2025-09-04T02:42:26.690184Z | rest_api_test_1756953746 | 42

🌐 Testing REST API endpoint with Query ID: 01f08938-cb0b-1cab-8942-4fad144663d3
📊 HTTP Status: 200
✅ Success! Server-side timing data:
   Query ID: 01f08938-cb0b-1cab-8942-4fad144663d3
   Status: FINISHED
   Start Time: 1756953746624ms (server-side)
   End Time: 1756953746739ms (server-side) 
   Server Duration: 115ms
   Client Duration: 621ms
   Rows Produced: 1
```

## Files

- **`query_timing.go`**: Main application that executes a query and retrieves timing data via REST API
- **`README.md`**: This documentation file
- **`go.mod`** / **`go.sum`**: Go module dependencies

## Technical Notes

- The API endpoint requires Bearer token authentication
- Query IDs are captured using the driver's `QueryIdCallback` mechanism
- The API is marked as `PUBLIC_UNDOCUMENTED` in Databricks internal documentation
- Response is immediate - no polling or waiting required
- Works with all SQL warehouses and compute endpoints