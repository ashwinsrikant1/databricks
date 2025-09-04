package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	_ "github.com/databricks/databricks-sql-go"
	"github.com/databricks/databricks-sql-go/driverctx"
)

// TODO: Configure your Databricks workspace credentials below
var (
	// TODO: Replace with your Databricks Personal Access Token
	databricksToken = "TODO: Replace with your Databricks Personal Access Token"

	// TODO: Replace with your workspace hostname (without https://)
	databricksHostname = "TODO: Replace with your Hostname"

	// TODO: Replace with your SQL warehouse endpoint ID
	databricksEndpoint = "TODO: Replace with your SQL warehouse endpoint ID"
)

// QueryInfo represents the response structure from the undocumented API
type QueryInfo struct {
	QueryID             string    `json:"query_id"`
	QueryText           string    `json:"query_text"`
	StartTime           time.Time `json:"start_time"`
	EndTime             time.Time `json:"end_time"`
	ExecutionDurationMs int64     `json:"execution_duration_ms"`
	TotalDurationMs     int64     `json:"total_duration_ms"`
	Status              string    `json:"status"`
	UserID              string    `json:"user_id"`
	WarehouseID         string    `json:"warehouse_id"`
	// Add other fields as they appear in the response
}

func main() {
	// Validate that credentials are configured
	if databricksToken == "" || databricksHostname == "" || databricksEndpoint == "" {
		log.Fatal("Please configure your Databricks credentials in the variables at the top of this file")
	}

	dsn := fmt.Sprintf("token:%s@%s:443/sql/1.0/endpoints/%s", databricksToken, databricksHostname, databricksEndpoint)
	db, err := sql.Open("databricks", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Test the undocumented REST API
	testUndocumentedAPI(db, databricksToken, databricksHostname)
}

func testUndocumentedAPI(db *sql.DB, token, hostname string) {
	fmt.Println("=== Testing Undocumented REST API: /sql/history/queries/{id} ===")

	// Create a unique identifier for this test
	uniqueID := fmt.Sprintf("rest_api_test_%d", time.Now().Unix())
	testQuery := fmt.Sprintf("SELECT current_timestamp() as query_time, '%s' as test_id, 42 as magic_number", uniqueID)

	fmt.Printf("🚀 Executing test query: %s\n", testQuery)

	// Execute the test query and capture the query ID
	ctx := driverctx.NewContextWithCorrelationId(context.Background(), "rest-api-test")

	var capturedQueryID string
	queryIDCallback := func(id string) {
		capturedQueryID = id
		fmt.Printf("📋 Captured Query ID: %s\n", id)
	}
	ctx = driverctx.NewContextWithQueryIdCallback(ctx, queryIDCallback)

	startTime := time.Now()
	rows, err := db.QueryContext(ctx, testQuery)
	if err != nil {
		log.Printf("Failed to execute test query: %v", err)
		return
	}

	// Process results
	var queryTime, testID string
	var magicNumber int
	if rows.Next() {
		rows.Scan(&queryTime, &testID, &magicNumber)
	}
	rows.Close()

	executionTime := time.Since(startTime)
	fmt.Printf("✅ Query executed in %s\n", executionTime)
	fmt.Printf("📄 Result: %s | %s | %d\n", queryTime, testID, magicNumber)

	if capturedQueryID == "" {
		fmt.Println("❌ No query ID captured, cannot test REST API")
		return
	}

	// Now test the undocumented REST API endpoint
	fmt.Printf("\n🌐 Testing REST API endpoint with Query ID: %s\n", capturedQueryID)

	// Try immediately first
	testRESTEndpoint(token, hostname, capturedQueryID, "immediate")

	// Wait a bit and try again (in case there's a delay)
	fmt.Println("\n⏳ Waiting 2 seconds before trying again...")
	time.Sleep(2 * time.Second)
	testRESTEndpoint(token, hostname, capturedQueryID, "after 2s delay")

	// Wait longer and try once more
	fmt.Println("\n⏳ Waiting 5 more seconds before final try...")
	time.Sleep(5 * time.Second)
	testRESTEndpoint(token, hostname, capturedQueryID, "after 7s total delay")
}

func testRESTEndpoint(token, hostname, queryID, testLabel string) {
	fmt.Printf("\n--- Testing %s ---\n", testLabel)

	// Construct the REST API URL
	apiURL := fmt.Sprintf("https://%s/api/2.0/sql/history/queries/%s", hostname, queryID)
	fmt.Printf("🔗 API URL: %s\n", apiURL)

	// Create HTTP request
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		fmt.Printf("❌ Failed to create request: %v\n", err)
		return
	}

	// Add authorization header
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	// Make the request
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("❌ Request failed: %v\n", err)
		return
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("❌ Failed to read response: %v\n", err)
		return
	}

	if resp.StatusCode == 200 {
		// Parse the JSON response to extract timing data
		var rawData map[string]interface{}
		if err := json.Unmarshal(body, &rawData); err != nil {
			fmt.Printf("❌ Failed to parse JSON: %v\n", err)
			return
		}

		fmt.Printf("✅ Server-side timing data retrieved:\n")
		fmt.Printf("   Query ID: %s\n", rawData["query_id"])
		fmt.Printf("   Status: %s\n", rawData["status"])

		// Extract timing information
		if startTime, ok := rawData["query_start_time_ms"]; ok {
			fmt.Printf("   Start Time: %v ms\n", startTime)
		}
		if endTime, ok := rawData["query_end_time_ms"]; ok {
			fmt.Printf("   End Time: %v ms\n", endTime)
		}
		if execEndTime, ok := rawData["execution_end_time_ms"]; ok {
			fmt.Printf("   Execution End: %v ms\n", execEndTime)
		}
		if duration, ok := rawData["duration"]; ok {
			fmt.Printf("   Server Duration: %v ms\n", duration)
		}
		if rows, ok := rawData["rows_produced"]; ok {
			fmt.Printf("   Rows Produced: %v\n", rows)
		}
		if client, ok := rawData["client_application"]; ok {
			fmt.Printf("   Client: %s\n", client)
		}
	} else {
		fmt.Printf("❌ API Error (Status %d):\n", resp.StatusCode)

		// Try to parse error as JSON for cleaner error display
		var errorData map[string]interface{}
		if err := json.Unmarshal(body, &errorData); err == nil {
			if msg, ok := errorData["message"]; ok {
				fmt.Printf("   Error: %s\n", msg)
			}
			if code, ok := errorData["error_code"]; ok {
				fmt.Printf("   Code: %s\n", code)
			}
		} else {
			fmt.Printf("   Raw error: %s\n", string(body))
		}
	}
}
