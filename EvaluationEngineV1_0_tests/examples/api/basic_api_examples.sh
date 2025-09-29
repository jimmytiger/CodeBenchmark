#!/bin/bash
# Basic API Examples for EvaluationEngineV1_0 Testing Framework
# This script demonstrates basic API testing with curl commands

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Basic API Examples ==="
echo "This script demonstrates basic API testing capabilities"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FRAMEWORK_DIR="$(dirname "$EXAMPLES_DIR")"
RESULTS_DIR="$EXAMPLES_DIR/results/api_basic"
BASE_URL="http://localhost:8001"
API_SERVER_PID=""

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo "API Base URL: $BASE_URL"
echo

# Function to start API server
start_api_server() {
    echo "Starting API test server..."
    cd "$TEST_FRAMEWORK_DIR"
    
    # Start server in background
    python -c "
from api.api_test_server import APITestServer
import time
import sys

server = APITestServer(host='localhost', port=8001)
try:
    server.start_server()
    if server.is_running():
        print('API server started successfully')
        print(f'Server PID: {server.get_pid()}')
        # Keep server running
        while True:
            time.sleep(1)
    else:
        print('Failed to start API server')
        sys.exit(1)
except KeyboardInterrupt:
    print('Stopping API server...')
    server.stop_server()
    sys.exit(0)
except Exception as e:
    print(f'Server error: {e}')
    sys.exit(1)
" > "$RESULTS_DIR/server.log" 2>&1 &
    
    API_SERVER_PID=$!
    echo "API server started with PID: $API_SERVER_PID"
    
    # Wait for server to be ready
    echo "Waiting for server to be ready..."
    for i in {1..30}; do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            echo "✓ API server is ready"
            return 0
        fi
        sleep 1
    done
    
    echo "✗ API server failed to start or is not responding"
    return 1
}

# Function to stop API server
stop_api_server() {
    if [ -n "$API_SERVER_PID" ]; then
        echo "Stopping API server (PID: $API_SERVER_PID)..."
        kill $API_SERVER_PID 2>/dev/null || true
        wait $API_SERVER_PID 2>/dev/null || true
        echo "API server stopped"
    fi
}

# Function to run curl command and save results
run_curl_test() {
    local test_name="$1"
    local curl_command="$2"
    local description="$3"
    local expected_status="${4:-200}"
    
    echo "=== $test_name ==="
    echo "Description: $description"
    echo "Command: $curl_command"
    echo
    
    # Run curl command and capture response
    local response_file="$RESULTS_DIR/${test_name,,}_response.json"
    local headers_file="$RESULTS_DIR/${test_name,,}_headers.txt"
    
    if curl -s -w "HTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\nTIME_CONNECT:%{time_connect}\n" \
           -D "$headers_file" \
           $curl_command > "$response_file" 2>&1; then
        
        # Extract status code
        local status_code=$(grep "HTTP_STATUS:" "$response_file" | cut -d: -f2)
        local time_total=$(grep "TIME_TOTAL:" "$response_file" | cut -d: -f2)
        
        # Remove timing info from response
        grep -v "HTTP_STATUS:\|TIME_TOTAL:\|TIME_CONNECT:" "$response_file" > "${response_file}.tmp"
        mv "${response_file}.tmp" "$response_file"
        
        if [ "$status_code" = "$expected_status" ]; then
            echo "✓ $test_name completed successfully"
            echo "  Status: $status_code (expected: $expected_status)"
            echo "  Response time: ${time_total}s"
            echo "  Response saved to: $response_file"
            
            # Show response preview
            if [ -s "$response_file" ]; then
                echo "  Response preview:"
                head -3 "$response_file" | sed 's/^/    /'
                if [ $(wc -l < "$response_file") -gt 3 ]; then
                    echo "    ... (see full response in file)"
                fi
            fi
        else
            echo "✗ $test_name failed - unexpected status code"
            echo "  Expected: $expected_status, Got: $status_code"
            echo "  Response time: ${time_total}s"
            echo "  Response saved to: $response_file"
        fi
    else
        echo "✗ $test_name failed - curl command failed"
        echo "  Error details saved to: $response_file"
    fi
    echo
}

# Trap to ensure server cleanup
trap stop_api_server EXIT

# Start API server
if ! start_api_server; then
    echo "Failed to start API server. Exiting."
    exit 1
fi

echo "Starting API tests..."
echo

# Example 1: Health Check
echo "1. Health Check"
echo "==============="
run_curl_test "Health_Check" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/health'" \
    "Check if the API server is healthy and responding" \
    "200"

# Example 2: List Available Tasks
echo "2. List Available Tasks"
echo "======================="
run_curl_test "List_Tasks" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "Get list of all available evaluation tasks" \
    "200"

# Example 3: List Available Adapters
echo "3. List Available Adapters"
echo "=========================="
run_curl_test "List_Adapters" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/adapters'" \
    "Get list of all available evaluation adapters" \
    "200"

# Example 4: Create Evaluation
echo "4. Create Evaluation"
echo "==================="

# Create evaluation request data
cat > "$RESULTS_DIR/evaluation_request.json" << EOF
{
  "model_id": "test_model_basic",
  "tasks": ["hellaswag"],
  "config": {
    "limit": 3,
    "test_mode": true,
    "description": "Basic API example evaluation"
  }
}
EOF

run_curl_test "Create_Evaluation" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "Create a new evaluation with hellaswag task" \
    "201"

# Extract evaluation ID for subsequent tests
EVALUATION_ID=""
if [ -f "$RESULTS_DIR/create_evaluation_response.json" ]; then
    EVALUATION_ID=$(grep -o '"evaluation_id":"[^"]*"' "$RESULTS_DIR/create_evaluation_response.json" | cut -d'"' -f4)
    if [ -n "$EVALUATION_ID" ]; then
        echo "Extracted evaluation ID: $EVALUATION_ID"
        echo "$EVALUATION_ID" > "$RESULTS_DIR/evaluation_id.txt"
    fi
fi

# Example 5: Check Evaluation Status
if [ -n "$EVALUATION_ID" ]; then
    echo "5. Check Evaluation Status"
    echo "=========================="
    run_curl_test "Check_Status" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/status'" \
        "Check the status of the created evaluation" \
        "200"
    
    # Wait a bit for evaluation to potentially progress
    echo "Waiting 5 seconds for evaluation to progress..."
    sleep 5
    
    # Check status again
    run_curl_test "Check_Status_Again" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/status'" \
        "Check evaluation status after waiting" \
        "200"
else
    echo "5. Check Evaluation Status"
    echo "=========================="
    echo "✗ Skipping status check - no evaluation ID available"
    echo
fi

# Example 6: List All Evaluations
echo "6. List All Evaluations"
echo "======================="
run_curl_test "List_Evaluations" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations'" \
    "Get list of all evaluations" \
    "200"

# Example 7: Get Evaluation Results (if available)
if [ -n "$EVALUATION_ID" ]; then
    echo "7. Get Evaluation Results"
    echo "========================"
    
    # First check if evaluation is completed
    echo "Checking if evaluation is completed..."
    status_response="$RESULTS_DIR/final_status_check.json"
    curl -s -X GET -H 'Accept: application/json' "$BASE_URL/api/v1/evaluations/$EVALUATION_ID/status" > "$status_response"
    
    if grep -q '"status":"completed"' "$status_response"; then
        echo "Evaluation completed, getting results..."
        run_curl_test "Get_Results" \
            "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results'" \
            "Get results from the completed evaluation" \
            "200"
    else
        echo "Evaluation not yet completed, attempting to get partial results..."
        run_curl_test "Get_Partial_Results" \
            "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results'" \
            "Attempt to get results from in-progress evaluation" \
            "200"
    fi
else
    echo "7. Get Evaluation Results"
    echo "========================"
    echo "✗ Skipping results retrieval - no evaluation ID available"
    echo
fi

# Example 8: Error Handling Test
echo "8. Error Handling Test"
echo "====================="
run_curl_test "Invalid_Endpoint" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/nonexistent'" \
    "Test error handling with invalid endpoint" \
    "404"

run_curl_test "Invalid_Method" \
    "-X PATCH -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "Test error handling with invalid HTTP method" \
    "405"

# Create invalid evaluation request
cat > "$RESULTS_DIR/invalid_evaluation_request.json" << EOF
{
  "model_id": "",
  "tasks": [],
  "config": {}
}
EOF

run_curl_test "Invalid_Evaluation" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/invalid_evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "Test error handling with invalid evaluation request" \
    "400"

# Generate comprehensive curl examples file
echo "9. Generate Curl Examples File"
echo "=============================="
cat > "$RESULTS_DIR/curl_examples.txt" << EOF
# EvaluationEngineV1_0 API - Curl Command Examples
# ================================================
# Base URL: $BASE_URL

# 1. Health Check
curl -X GET -H 'Accept: application/json' '$BASE_URL/health'

# 2. List Available Tasks
curl -X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'

# 3. List Available Adapters
curl -X GET -H 'Accept: application/json' '$BASE_URL/api/v1/adapters'

# 4. Create Evaluation
curl -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' \\
  -d '{
    "model_id": "your_model_id",
    "tasks": ["hellaswag", "arc_easy"],
    "config": {
      "limit": 10,
      "description": "Your evaluation description"
    }
  }' \\
  '$BASE_URL/api/v1/evaluations'

# 5. Check Evaluation Status (replace EVALUATION_ID)
curl -X GET -H 'Accept: application/json' \\
  '$BASE_URL/api/v1/evaluations/EVALUATION_ID/status'

# 6. Get Evaluation Results (replace EVALUATION_ID)
curl -X GET -H 'Accept: application/json' \\
  '$BASE_URL/api/v1/evaluations/EVALUATION_ID/results'

# 7. List All Evaluations
curl -X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations'

# 8. Cancel Evaluation (replace EVALUATION_ID)
curl -X DELETE -H 'Accept: application/json' \\
  '$BASE_URL/api/v1/evaluations/EVALUATION_ID'

# Example with verbose output and timing:
curl -v -w "\\nTime: %{time_total}s\\nStatus: %{http_code}\\n" \\
  -X GET -H 'Accept: application/json' '$BASE_URL/health'

# Example with custom headers:
curl -X POST -H 'Content-Type: application/json' \\
  -H 'Accept: application/json' \\
  -H 'User-Agent: MyApp/1.0' \\
  -H 'X-Request-ID: 12345' \\
  -d '{"model_id": "test", "tasks": ["hellaswag"], "config": {"limit": 5}}' \\
  '$BASE_URL/api/v1/evaluations'

# Note: Replace EVALUATION_ID with actual evaluation ID from create response
# Note: Adjust model_id, tasks, and config parameters as needed
EOF

echo "✓ Curl examples file created: $RESULTS_DIR/curl_examples.txt"
echo

# Summary
echo "=== Basic API Examples Summary ==="
echo "All basic API examples have been executed."
echo
echo "Results saved in: $RESULTS_DIR"
echo "Files created:"
ls -la "$RESULTS_DIR" | grep -v "^total" | awk '{print "  " $9 " (" $5 " bytes)"}'
echo
echo "API endpoints tested:"
echo "  ✓ Health check"
echo "  ✓ List tasks"
echo "  ✓ List adapters"
echo "  ✓ Create evaluation"
echo "  ✓ Check evaluation status"
echo "  ✓ List evaluations"
echo "  ✓ Get evaluation results"
echo "  ✓ Error handling"
echo
echo "Generated files:"
echo "  - curl_examples.txt: Ready-to-use curl commands"
echo "  - evaluation_request.json: Sample evaluation request"
echo "  - *_response.json: API response examples"
echo "  - *_headers.txt: HTTP headers from responses"
echo
echo "Next steps:"
echo "1. Review the response files to understand API data structures"
echo "2. Try the advanced API examples: ./advanced_api_examples.sh"
echo "3. Use the curl_examples.txt file for manual testing"
echo "4. Explore concurrent testing: ./concurrent_testing.sh"
echo
echo "For troubleshooting, check the server.log and individual response files"