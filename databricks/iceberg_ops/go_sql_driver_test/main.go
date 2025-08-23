package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	_ "github.com/databricks/databricks-sql-go"
	"github.com/databricks/databricks-sql-go/driverctx"
	"github.com/databricks/databricks-sql-go/logger"
)

func main() {
	// Set up logging to capture detailed timing information
	logger.SetLogLevel("debug")

	// Get connection details from environment variables
	token := os.Getenv("DATABRICKS_TOKEN")
	hostname := os.Getenv("DATABRICKS_HOSTNAME")
	endpoint := os.Getenv("DATABRICKS_ENDPOINT")

	if token == "" || hostname == "" || endpoint == "" {
		log.Fatal("Please set DATABRICKS_TOKEN, DATABRICKS_HOSTNAME, and DATABRICKS_ENDPOINT environment variables")
	}

	// Create DSN (Data Source Name)
	dsn := fmt.Sprintf("token:%s@%s:443/sql/1.0/endpoints/%s", token, hostname, endpoint)

	// Open connection
	db, err := sql.Open("databricks", dsn)
	if err != nil {
		log.Fatal("Failed to open connection:", err)
	}
	defer db.Close()

	// Test connection
	if err := db.Ping(); err != nil {
		log.Fatal("Failed to ping database:", err)
	}

	fmt.Println("Successfully connected to Databricks!")

	// Create context with correlation ID for tracking
	correlationID := fmt.Sprintf("go-test-%d", time.Now().Unix())
	ctx := driverctx.NewContextWithCorrelationId(context.Background(), correlationID)

	// Set up callbacks to capture query and connection IDs
	queryIDCallback := func(id string) {
		fmt.Printf("Query ID: %s\n", id)
	}

	connectionIDCallback := func(id string) {
		fmt.Printf("Connection ID: %s\n", id)
	}

	ctx = driverctx.NewContextWithQueryIdCallback(ctx, queryIDCallback)
	ctx = driverctx.NewContextWithConnIdCallback(ctx, connectionIDCallback)

	// Execute a simple query and capture timing
	executeQueryWithTiming(ctx, db, "SELECT 1 as test_column")

	// Test the system.query.history query as requested
	executeQueryWithTiming(ctx, db, "SELECT * FROM system.query.history LIMIT 10")

	// Execute query with current timestamp to see timing differences
	executeQueryWithTiming(ctx, db, "SELECT current_timestamp() as query_time, 'test' as message")
}

func executeQueryWithTiming(ctx context.Context, db *sql.DB, query string) {
	fmt.Printf("\n=== Executing Query: %s ===\n", query)

	// Record start time
	startTime := time.Now()
	fmt.Printf("Query Start Time: %s\n", startTime.Format(time.RFC3339Nano))

	// Use logger.Track for built-in timing
	msg, logStart := logger.Track("Query Execution")
	defer logger.Duration(msg, logStart)

	// Execute query
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		log.Printf("Query failed: %v", err)
		return
	}
	defer rows.Close()

	// Record end time after query execution
	endTime := time.Now()
	fmt.Printf("Query End Time: %s\n", endTime.Format(time.RFC3339Nano))
	fmt.Printf("Total Execution Duration: %s\n", endTime.Sub(startTime))

	// Process results
	columns, err := rows.Columns()
	if err != nil {
		log.Printf("Failed to get columns: %v", err)
		return
	}

	fmt.Printf("Columns: %v\n", columns)

	// Read all rows and measure total processing time
	processingStart := time.Now()
	rowCount := 0
	for rows.Next() {
		rowCount++
		// Create slice to hold column values
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			log.Printf("Failed to scan row: %v", err)
			continue
		}

		// Print first few rows for verification
		if rowCount <= 3 {
			fmt.Printf("Row %d: %v\n", rowCount, values)
		}
	}

	if err := rows.Err(); err != nil {
		log.Printf("Row iteration error: %v", err)
	}

	processingEnd := time.Now()
	fmt.Printf("Processed %d rows in %s\n", rowCount, processingEnd.Sub(processingStart))
	fmt.Printf("Total Time (Query + Processing): %s\n", processingEnd.Sub(startTime))

	// Print timing summary
	fmt.Printf("\n--- Timing Summary ---\n")
	fmt.Printf("Start: %s\n", startTime.Format("15:04:05.000000"))
	fmt.Printf("End: %s\n", endTime.Format("15:04:05.000000"))
	fmt.Printf("Query Execution: %s\n", endTime.Sub(startTime))
	fmt.Printf("Data Processing: %s\n", processingEnd.Sub(endTime))
	fmt.Printf("Total Duration: %s\n", processingEnd.Sub(startTime))
}