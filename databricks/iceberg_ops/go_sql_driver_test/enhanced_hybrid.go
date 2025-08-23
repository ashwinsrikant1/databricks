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
	"strings"
	"time"

	_ "github.com/databricks/databricks-sql-go"
	"github.com/databricks/databricks-sql-go/driverctx"
)

// QueryHistoryResponse represents the system.query.history response
type QueryHistoryResponse struct {
	StatementID           string    `json:"statement_id"`
	ExecutedBy           string    `json:"executed_by"`
	ExecutionStatus      string    `json:"execution_status"`
	StartTime            time.Time `json:"start_time"`
	EndTime              time.Time `json:"end_time"`
	TotalDurationMs      int64     `json:"total_duration_ms"`
	ExecutionDurationMs  int64     `json:"execution_duration_ms"`
	CompilationDurationMs int64    `json:"compilation_duration_ms"`
	StatementText        string    `json:"statement_text"`
	ReadRows             int64     `json:"read_rows"`
	ProducedRows         int64     `json:"produced_rows"`
}

// StatementExecutionRequest represents the request to execute a statement
type StatementExecutionRequest struct {
	Statement   string `json:"statement"`
	WarehouseID string `json:"warehouse_id"`
	WaitTimeout string `json:"wait_timeout"`
	Format      string `json:"format"`
	Disposition string `json:"disposition"`
}

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
		ChunkIndex int           `json:"chunk_index"`
		RowOffset  int           `json:"row_offset"`
		RowCount   int           `json:"row_count"`
		DataArray  [][]any       `json:"data_array"`
	} `json:"result"`
}

// TimingComparison represents comparison between different approaches
type TimingComparison struct {
	GoDriverTiming   TimingInfo `json:"go_driver_timing"`
	RESTAPITiming    TimingInfo `json:"rest_api_timing"`
	QueryHistoryInfo *QueryHistoryResponse `json:"query_history_info,omitempty"`
}

// TimingInfo represents extracted timing information
type TimingInfo struct {
	Method        string    `json:"method"`
	QueryID       string    `json:"query_id"`
	StatementText string    `json:"statement_text"`
	State         string    `json:"state"`
	StartTime     time.Time `json:"start_time"`
	EndTime       time.Time `json:"end_time"`
	Duration      string    `json:"duration"`
	DurationMs    int64     `json:"duration_ms"`
	RowCount      int       `json:"row_count"`
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
		httpClient:  &http.Client{Timeout: 60 * time.Second},
	}
}

// ExecuteStatementWithREST executes a statement via REST API to get full timing info
func (c *DatabricksRESTClient) ExecuteStatementWithREST(statement string) (*TimingInfo, error) {
	// Construct the API URL
	url := fmt.Sprintf("https://%s/api/2.0/sql/statements/", c.hostname)

	// Create the request payload
	payload := StatementExecutionRequest{
		Statement:   statement,
		WarehouseID: c.warehouseID,
		WaitTimeout: "50s", // Wait up to 50 seconds for completion
		Format:      "JSON_ARRAY",
		Disposition: "INLINE",
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
		Method:        "REST_API",
		QueryID:       execResp.StatementID,
		StatementText: statement,
		State:         execResp.Status.State,
		StartTime:     startTime,
		EndTime:       endTime,
		Duration:      endTime.Sub(startTime).String(),
		DurationMs:    endTime.Sub(startTime).Milliseconds(),
		RowCount:      execResp.Manifest.TotalRowCount,
		ColumnCount:   execResp.Manifest.Schema.ColumnCount,
	}

	return timingInfo, nil
}

// QueryHistoryForStatement looks up a statement in system.query.history
func (c *DatabricksRESTClient) QueryHistoryForStatement(statementText string, afterTime time.Time) (*QueryHistoryResponse, error) {
	// Clean the statement text for comparison
	cleanStatement := strings.TrimSpace(strings.ReplaceAll(statementText, "\n", " "))
	
	// Use system.query.history to find our statement
	historyQuery := fmt.Sprintf(`
		SELECT 
			statement_id,
			executed_by,
			execution_status,
			start_time,
			end_time,
			total_duration_ms,
			execution_duration_ms,
			compilation_duration_ms,
			statement_text,
			read_rows,
			produced_rows
		FROM system.query.history 
		WHERE statement_text LIKE '%%%s%%'
		AND start_time >= '%s'
		ORDER BY start_time DESC 
		LIMIT 5`,
		strings.ReplaceAll(cleanStatement, "'", "''"), // Escape single quotes
		afterTime.UTC().Format("2006-01-02 15:04:05"))

	timingInfo, err := c.ExecuteStatementWithREST(historyQuery)
	if err != nil {
		return nil, fmt.Errorf("failed to query history: %w", err)
	}

	fmt.Printf("📋 Query history lookup returned %d rows\n", timingInfo.RowCount)

	// For now, we'll return the timing info structure
	// In a real implementation, you'd parse the results to extract the specific query
	return &QueryHistoryResponse{
		StatementID:          timingInfo.QueryID,
		ExecutionStatus:      timingInfo.State,
		StartTime:            timingInfo.StartTime,
		EndTime:              timingInfo.EndTime,
		TotalDurationMs:      timingInfo.DurationMs,
		StatementText:        historyQuery,
	}, nil
}

func main() {
	// Get connection details from environment variables
	token := os.Getenv("DATABRICKS_TOKEN")
	hostname := os.Getenv("DATABRICKS_HOSTNAME")
	endpoint := os.Getenv("DATABRICKS_ENDPOINT")

	if token == "" || hostname == "" || endpoint == "" {
		log.Fatal("Please set DATABRICKS_TOKEN, DATABRICKS_HOSTNAME, and DATABRICKS_ENDPOINT environment variables")
	}

	fmt.Println("=== Enhanced Hybrid Approach: Go Driver + REST API Timing ===")
	fmt.Println()

	// Create REST client for timing information
	restClient := NewDatabricksRESTClient(hostname, token, endpoint)

	// Test query that's easy to identify
	testQuery := "SELECT current_timestamp() as query_time, 'enhanced_hybrid_test_12345' as message"

	// Test 1: Go Driver execution with timing
	fmt.Println("🔄 Test 1: Go Driver Execution")
	goDriverTiming := executeGoDriverApproach(token, hostname, endpoint, testQuery)

	fmt.Println()

	// Test 2: REST API execution
	fmt.Println("🔄 Test 2: REST API Execution")
	restAPITiming := executeRESTAPIApproach(restClient, testQuery)

	fmt.Println()

	// Test 3: Try to correlate using query history
	fmt.Println("🔄 Test 3: Query History Correlation")
	historyInfo := queryHistoryCorrelation(restClient, testQuery, goDriverTiming.StartTime)

	// Create comparison
	comparison := TimingComparison{
		GoDriverTiming:   *goDriverTiming,
		RESTAPITiming:    *restAPITiming,
		QueryHistoryInfo: historyInfo,
	}

	// Display comparison
	fmt.Println()
	fmt.Println("📊 TIMING COMPARISON SUMMARY")
	fmt.Println("============================================================")
	fmt.Printf("Go Driver:  %s (Query ID: %s)\n", goDriverTiming.Duration, goDriverTiming.QueryID)
	fmt.Printf("REST API:   %s (Statement ID: %s)\n", restAPITiming.Duration, restAPITiming.QueryID)
	fmt.Printf("Difference: %dms\n", abs(goDriverTiming.DurationMs - restAPITiming.DurationMs))
	
	fmt.Println()
	fmt.Printf("Results Comparison:\n")
	fmt.Printf("  Go Driver: %d rows, %d columns\n", goDriverTiming.RowCount, goDriverTiming.ColumnCount)
	fmt.Printf("  REST API:  %d rows, %d columns\n", restAPITiming.RowCount, restAPITiming.ColumnCount)

	// Export the comparison as JSON
	comparisonJSON, _ := json.MarshalIndent(comparison, "", "  ")
	fmt.Println("\n📄 Full Comparison (JSON):")
	fmt.Println(string(comparisonJSON))
}

func executeGoDriverApproach(token, hostname, endpoint, query string) *TimingInfo {
	// Create DSN and open connection using Go driver
	dsn := fmt.Sprintf("token:%s@%s:443/sql/1.0/endpoints/%s", token, hostname, endpoint)
	db, err := sql.Open("databricks", dsn)
	if err != nil {
		log.Printf("Failed to open connection: %v", err)
		return &TimingInfo{Method: "GO_DRIVER", ErrorMessage: err.Error()}
	}
	defer db.Close()

	// Create context with query ID callback
	var capturedQueryID string
	queryIDCallback := func(id string) {
		capturedQueryID = id
	}

	ctx := driverctx.NewContextWithCorrelationId(context.Background(), "enhanced-hybrid-test")
	ctx = driverctx.NewContextWithQueryIdCallback(ctx, queryIDCallback)

	// Execute query using Go driver
	fmt.Printf("🚀 Executing via Go Driver: %s\n", query)

	startTime := time.Now()
	rows, err := db.QueryContext(ctx, query)
	endTime := time.Now()

	if err != nil {
		log.Printf("Go driver query failed: %v", err)
		return &TimingInfo{
			Method:        "GO_DRIVER",
			StatementText: query,
			StartTime:     startTime,
			EndTime:       endTime,
			Duration:      endTime.Sub(startTime).String(),
			DurationMs:    endTime.Sub(startTime).Milliseconds(),
			ErrorMessage:  err.Error(),
		}
	}
	defer rows.Close()

	// Process results
	columns, err := rows.Columns()
	if err != nil {
		log.Printf("Failed to get columns: %v", err)
		return &TimingInfo{Method: "GO_DRIVER", ErrorMessage: err.Error()}
	}

	var resultCount int
	for rows.Next() {
		resultCount++
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		if err := rows.Scan(valuePtrs...); err == nil && resultCount == 1 {
			fmt.Printf("📄 Go Driver Result: %v\n", values)
		}
	}

	fmt.Printf("⏱️  Go Driver: %s (%d rows, %d columns)\n", 
		endTime.Sub(startTime), resultCount, len(columns))
	fmt.Printf("📋 Go Driver Query ID: %s\n", capturedQueryID)

	return &TimingInfo{
		Method:        "GO_DRIVER",
		QueryID:       capturedQueryID,
		StatementText: query,
		State:         "COMPLETED",
		StartTime:     startTime,
		EndTime:       endTime,
		Duration:      endTime.Sub(startTime).String(),
		DurationMs:    endTime.Sub(startTime).Milliseconds(),
		RowCount:      resultCount,
		ColumnCount:   len(columns),
	}
}

func executeRESTAPIApproach(restClient *DatabricksRESTClient, query string) *TimingInfo {
	fmt.Printf("🚀 Executing via REST API: %s\n", query)

	timingInfo, err := restClient.ExecuteStatementWithREST(query)
	if err != nil {
		fmt.Printf("❌ REST API execution failed: %v\n", err)
		return &TimingInfo{Method: "REST_API", ErrorMessage: err.Error()}
	}

	fmt.Printf("⏱️  REST API: %s (%d rows, %d columns)\n", 
		timingInfo.Duration, timingInfo.RowCount, timingInfo.ColumnCount)
	fmt.Printf("📋 REST API Statement ID: %s\n", timingInfo.QueryID)

	return timingInfo
}

func queryHistoryCorrelation(restClient *DatabricksRESTClient, query string, afterTime time.Time) *QueryHistoryResponse {
	fmt.Printf("🔍 Searching query history for statement containing: %s\n", 
		strings.Split(query, "'")[1]) // Extract the unique message

	historyInfo, err := restClient.QueryHistoryForStatement(query, afterTime.Add(-1*time.Minute))
	if err != nil {
		fmt.Printf("❌ Failed to query history: %v\n", err)
		return nil
	}

	fmt.Printf("📊 Query history search completed\n")
	return historyInfo
}

func abs(x int64) int64 {
	if x < 0 {
		return -x
	}
	return x
}