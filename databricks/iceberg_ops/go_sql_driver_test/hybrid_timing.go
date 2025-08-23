package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	_ "github.com/databricks/databricks-sql-go"
	"github.com/databricks/databricks-sql-go/driverctx"
)

// StatementExecutionResponse represents the Databricks Statement Execution API response
type StatementExecutionResponse struct {
	StatementID string `json:"statement_id"`
	Status      struct {
		State string `json:"state"`
	} `json:"status"`
	Manifest struct {
		Format string `json:"format"`
		Schema struct {
			ColumnCount int `json:"column_count"`
		} `json:"schema"`
		TotalChunkCount int `json:"total_chunk_count"`
		TotalRowCount   int `json:"total_row_count"`
	} `json:"manifest"`
	Result struct {
		ChunkIndex int `json:"chunk_index"`
		RowOffset  int `json:"row_offset"`
		RowCount   int `json:"row_count"`
	} `json:"result"`
}

// GetStatementResponse represents the response from getting statement details
type GetStatementResponse struct {
	StatementID string `json:"statement_id"`
	Status      struct {
		State string `json:"state"`
	} `json:"status"`
	StatementResponse *StatementExecutionResponse `json:"statement_response,omitempty"`
}

// TimingInfo represents extracted timing information
type TimingInfo struct {
	QueryID       string    `json:"query_id"`
	State         string    `json:"state"`
	StartTime     time.Time `json:"start_time,omitempty"`
	EndTime       time.Time `json:"end_time,omitempty"`
	Duration      string    `json:"duration,omitempty"`
	RowCount      int       `json:"row_count"`
	ChunkCount    int       `json:"chunk_count"`
	ColumnCount   int       `json:"column_count"`
	ErrorMessage  string    `json:"error_message,omitempty"`
}

// DatabricksRESTClient handles REST API calls to get timing information
type DatabricksRESTClient struct {
	hostname    string
	token       string
	warehouseID string
	httpClient  *http.Client
}

// NewDatabricksRESTClient creates a new REST client
func NewDatabricksRESTClient(hostname, token, warehouseID string) *DatabricksRESTClient {
	return &DatabricksRESTClient{
		hostname:    hostname,
		token:       token,
		warehouseID: warehouseID,
		httpClient:  &http.Client{Timeout: 30 * time.Second},
	}
}

// GetStatementTiming retrieves timing information for a statement using the REST API
func (c *DatabricksRESTClient) GetStatementTiming(statementID string) (*TimingInfo, error) {
	// Construct the API URL
	url := fmt.Sprintf("https://%s/api/2.0/sql/statements/%s", c.hostname, statementID)

	// Create the request
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.token))
	req.Header.Set("Content-Type", "application/json")

	// Make the request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Read the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response
	var getResp GetStatementResponse
	if err := json.Unmarshal(body, &getResp); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	// Extract timing information
	timingInfo := &TimingInfo{
		QueryID: statementID,
		State:   getResp.Status.State,
	}

	if getResp.StatementResponse != nil {
		timingInfo.RowCount = getResp.StatementResponse.Manifest.TotalRowCount
		timingInfo.ChunkCount = getResp.StatementResponse.Manifest.TotalChunkCount
		timingInfo.ColumnCount = getResp.StatementResponse.Manifest.Schema.ColumnCount
	}

	return timingInfo, nil
}

// ExecuteStatementWithREST executes a statement via REST API to get full timing info
func (c *DatabricksRESTClient) ExecuteStatementWithREST(statement string) (*TimingInfo, error) {
	// Construct the API URL
	url := fmt.Sprintf("https://%s/api/2.0/sql/statements/", c.hostname)

	// Create the request payload
	payload := map[string]interface{}{
		"statement":    statement,
		"warehouse_id": c.warehouseID,
		"wait_timeout": "30s", // Wait up to 30 seconds for completion
		"format":       "JSON_ARRAY",
		"disposition":  "INLINE",
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal payload: %w", err)
	}

	// Record start time
	startTime := time.Now()

	// Create the request
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(payloadBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.token))
	req.Header.Set("Content-Type", "application/json")

	// Make the request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Record end time
	endTime := time.Now()

	// Read the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response
	var execResp StatementExecutionResponse
	if err := json.Unmarshal(body, &execResp); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	// Extract timing information
	timingInfo := &TimingInfo{
		QueryID:     execResp.StatementID,
		State:       execResp.Status.State,
		StartTime:   startTime,
		EndTime:     endTime,
		Duration:    endTime.Sub(startTime).String(),
		RowCount:    execResp.Manifest.TotalRowCount,
		ChunkCount:  execResp.Manifest.TotalChunkCount,
		ColumnCount: execResp.Manifest.Schema.ColumnCount,
	}

	return timingInfo, nil
}

func main() {
	// Get connection details from environment variables
	token := os.Getenv("DATABRICKS_TOKEN")
	hostname := os.Getenv("DATABRICKS_HOSTNAME")
	endpoint := os.Getenv("DATABRICKS_ENDPOINT")

	if token == "" || hostname == "" || endpoint == "" {
		log.Fatal("Please set DATABRICKS_TOKEN, DATABRICKS_HOSTNAME, and DATABRICKS_ENDPOINT environment variables")
	}

	fmt.Println("=== Hybrid Approach: Go Driver + REST API Timing ===")
	fmt.Println()

	// Create REST client for timing information
	restClient := NewDatabricksRESTClient(hostname, token, endpoint)

	// Test 1: Go Driver execution with query ID capture + REST API timing lookup
	fmt.Println("🔄 Test 1: Go Driver + REST API Timing Lookup")
	executeHybridApproach(token, hostname, endpoint, restClient)

	fmt.Println()

	// Test 2: Pure REST API execution for comparison
	fmt.Println("🔄 Test 2: Pure REST API Execution (for comparison)")
	executePureRESTApproach(restClient)
}

func executeHybridApproach(token, hostname, endpoint string, restClient *DatabricksRESTClient) {
	// Create DSN and open connection using Go driver
	dsn := fmt.Sprintf("token:%s@%s:443/sql/1.0/endpoints/%s", token, hostname, endpoint)
	db, err := sql.Open("databricks", dsn)
	if err != nil {
		log.Printf("Failed to open connection: %v", err)
		return
	}
	defer db.Close()

	// Create context with query ID callback to capture the statement ID
	var capturedQueryID string
	queryIDCallback := func(id string) {
		capturedQueryID = id
		fmt.Printf("📋 Captured Query ID: %s\n", id)
	}

	ctx := driverctx.NewContextWithCorrelationId(context.Background(), "hybrid-test")
	ctx = driverctx.NewContextWithQueryIdCallback(ctx, queryIDCallback)

	// Execute query using Go driver
	query := "SELECT current_timestamp() as query_time, 'hybrid_test' as message"
	fmt.Printf("🚀 Executing via Go Driver: %s\n", query)

	driverStartTime := time.Now()
	rows, err := db.QueryContext(ctx, query)
	driverEndTime := time.Now()

	if err != nil {
		log.Printf("Go driver query failed: %v", err)
		return
	}
	defer rows.Close()

	fmt.Printf("⏱️  Go Driver Execution Time: %s\n", driverEndTime.Sub(driverStartTime))

	// Process results from Go driver
	columns, err := rows.Columns()
	if err != nil {
		log.Printf("Failed to get columns: %v", err)
		return
	}

	var resultCount int
	for rows.Next() {
		resultCount++
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		if err := rows.Scan(valuePtrs...); err == nil && resultCount <= 2 {
			fmt.Printf("📄 Result %d: %v\n", resultCount, values)
		}
	}

	fmt.Printf("📊 Go Driver Results: %d rows, %d columns\n", resultCount, len(columns))

	// Now use the captured query ID to get timing information via REST API
	if capturedQueryID != "" {
		fmt.Printf("\n🔍 Fetching timing metadata via REST API for Query ID: %s\n", capturedQueryID)
		
		// Wait a moment for the query to be fully processed
		time.Sleep(500 * time.Millisecond)
		
		timingInfo, err := restClient.GetStatementTiming(capturedQueryID)
		if err != nil {
			fmt.Printf("❌ Failed to get timing info via REST API: %v\n", err)
		} else {
			fmt.Printf("✅ REST API Timing Information:\n")
			fmt.Printf("   State: %s\n", timingInfo.State)
			fmt.Printf("   Row Count: %d\n", timingInfo.RowCount)
			fmt.Printf("   Column Count: %d\n", timingInfo.ColumnCount)
			fmt.Printf("   Chunk Count: %d\n", timingInfo.ChunkCount)
			
			// Compare with Go driver results
			fmt.Printf("\n📈 Comparison:\n")
			fmt.Printf("   Go Driver Rows: %d | REST API Rows: %d\n", resultCount, timingInfo.RowCount)
			fmt.Printf("   Go Driver Columns: %d | REST API Columns: %d\n", len(columns), timingInfo.ColumnCount)
		}
	} else {
		fmt.Printf("❌ No query ID captured from Go driver\n")
	}
}

func executePureRESTApproach(restClient *DatabricksRESTClient) {
	query := "SELECT current_timestamp() as query_time, 'rest_api_test' as message"
	fmt.Printf("🚀 Executing via Pure REST API: %s\n", query)

	timingInfo, err := restClient.ExecuteStatementWithREST(query)
	if err != nil {
		fmt.Printf("❌ REST API execution failed: %v\n", err)
		return
	}

	fmt.Printf("✅ Pure REST API Results:\n")
	fmt.Printf("   Query ID: %s\n", timingInfo.QueryID)
	fmt.Printf("   State: %s\n", timingInfo.State)
	fmt.Printf("   Start Time: %s\n", timingInfo.StartTime.Format(time.RFC3339Nano))
	fmt.Printf("   End Time: %s\n", timingInfo.EndTime.Format(time.RFC3339Nano))
	fmt.Printf("   Duration: %s\n", timingInfo.Duration)
	fmt.Printf("   Row Count: %d\n", timingInfo.RowCount)
	fmt.Printf("   Column Count: %d\n", timingInfo.ColumnCount)
	fmt.Printf("   Chunk Count: %d\n", timingInfo.ChunkCount)
}