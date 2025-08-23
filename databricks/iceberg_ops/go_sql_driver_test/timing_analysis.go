package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"reflect"

	_ "github.com/databricks/databricks-sql-go"
	"github.com/databricks/databricks-sql-go/driverctx"
)

func main() {
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

	fmt.Println("=== Analyzing Databricks Go Driver for Timing Information ===")
	fmt.Println()

	// Create context with correlation ID for tracking
	ctx := driverctx.NewContextWithCorrelationId(context.Background(), "timing-analysis")

	// Execute a query and analyze what metadata is available
	analyzeQueryMetadata(ctx, db, "SELECT current_timestamp() as query_time")
}

func analyzeQueryMetadata(ctx context.Context, db *sql.DB, query string) {
	fmt.Printf("=== Query: %s ===\n", query)

	// Execute query
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		log.Printf("Query failed: %v", err)
		return
	}
	defer rows.Close()

	// Analyze the rows object using reflection
	fmt.Println("\n1. Analyzing sql.Rows object:")
	analyzeObjectFields(rows, "sql.Rows")

	// Check if rows implements the custom Databricks rows interface using type assertion
	fmt.Println("\n2. Checking for Databricks extensions...")
	
	// Try to access the underlying implementation through reflection
	rowsValue := reflect.ValueOf(rows)
	if rowsValue.Kind() == reflect.Ptr {
		rowsValue = rowsValue.Elem()
	}
	
	// Check if we can find GetArrowBatches method
	if method := rowsValue.MethodByName("GetArrowBatches"); method.IsValid() {
		fmt.Println("   ✓ GetArrowBatches method found!")
		
		// Try to call it (though we may not be able to due to interface constraints)
		if method.Type().NumIn() == 1 { // Expecting context parameter
			results := method.Call([]reflect.Value{reflect.ValueOf(ctx)})
			if len(results) == 2 {
				if !results[1].IsNil() { // Check error
					fmt.Printf("   Error calling GetArrowBatches: %v\n", results[1].Interface())
				} else {
					fmt.Println("   Successfully called GetArrowBatches")
					if !results[0].IsNil() {
						analyzeObjectFields(results[0].Interface(), "ArrowBatchIterator")
					}
				}
			}
		}
	} else {
		fmt.Println("   ✗ No GetArrowBatches method found")
	}

	// Check for any additional metadata methods
	fmt.Println("\n3. Checking for timing/metadata methods...")
	checkForTimingMethods(rows)

	// Process results to complete the query
	columns, err := rows.Columns()
	if err != nil {
		log.Printf("Failed to get columns: %v", err)
		return
	}
	fmt.Printf("\n4. Query executed successfully, columns: %v\n", columns)

	// Read one row to complete the query cycle
	if rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		if err := rows.Scan(valuePtrs...); err == nil {
			fmt.Printf("   Sample result: %v\n", values)
		}
	}
}

func analyzeObjectFields(obj interface{}, typeName string) {
	if obj == nil {
		fmt.Printf("   %s is nil\n", typeName)
		return
	}

	val := reflect.ValueOf(obj)
	typ := reflect.TypeOf(obj)

	// If it's a pointer, get the underlying element
	if val.Kind() == reflect.Ptr {
		if val.IsNil() {
			fmt.Printf("   %s pointer is nil\n", typeName)
			return
		}
		val = val.Elem()
		typ = typ.Elem()
	}

	fmt.Printf("   %s type: %s\n", typeName, typ.Name())

	// Look for any fields that might contain timing information
	timingKeywords := []string{"time", "duration", "start", "end", "elapsed", "timing", "metadata", "stat", "perf"}
	
	// Check methods
	fmt.Printf("   Methods containing timing-related keywords:\n")
	foundTimingMethods := false
	for i := 0; i < typ.NumMethod(); i++ {
		method := typ.Method(i)
		methodName := method.Name
		for _, keyword := range timingKeywords {
			if containsIgnoreCase(methodName, keyword) {
				fmt.Printf("     - %s\n", methodName)
				foundTimingMethods = true
				break
			}
		}
	}
	if !foundTimingMethods {
		fmt.Printf("     No timing-related methods found\n")
	}

	// Check fields (if accessible)
	if val.Kind() == reflect.Struct {
		fmt.Printf("   Fields containing timing-related keywords:\n")
		foundTimingFields := false
		for i := 0; i < val.NumField(); i++ {
			field := typ.Field(i)
			if field.IsExported() { // Only check exported fields
				fieldName := field.Name
				for _, keyword := range timingKeywords {
					if containsIgnoreCase(fieldName, keyword) {
						fmt.Printf("     - %s (%s)\n", fieldName, field.Type)
						foundTimingFields = true
						break
					}
				}
			}
		}
		if !foundTimingFields {
			fmt.Printf("     No accessible timing-related fields found\n")
		}
	}
}

func checkForTimingMethods(rows *sql.Rows) {
	// Check if the rows object has any methods that might return timing information
	val := reflect.ValueOf(rows)
	typ := reflect.TypeOf(rows)

	// List of method names that might contain timing info
	possibleTimingMethods := []string{
		"GetExecutionTime", "GetStartTime", "GetEndTime", "GetDuration",
		"GetMetadata", "GetStatistics", "GetQueryInfo", "GetTiming",
		"ExecutionTime", "StartTime", "EndTime", "Duration",
	}

	fmt.Printf("   Checking for specific timing methods:\n")
	foundAny := false
	for _, methodName := range possibleTimingMethods {
		method := val.MethodByName(methodName)
		if method.IsValid() {
			fmt.Printf("     ✓ Found method: %s\n", methodName)
			foundAny = true
		}
	}
	if !foundAny {
		fmt.Printf("     ✗ No timing-specific methods found\n")
	}

	// Check the exact type
	fmt.Printf("   Underlying type: %s\n", typ.String())
}

func containsIgnoreCase(s, substr string) bool {
	s = toLower(s)
	substr = toLower(substr)
	return contains(s, substr)
}

func toLower(s string) string {
	result := make([]rune, len(s))
	for i, r := range s {
		if r >= 'A' && r <= 'Z' {
			result[i] = r + 32
		} else {
			result[i] = r
		}
	}
	return string(result)
}

func contains(s, substr string) bool {
	if len(substr) > len(s) {
		return false
	}
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}