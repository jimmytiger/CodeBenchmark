#!/bin/bash
# Comprehensive Curl Examples for EvaluationEngineV1_0 API Testing
# This script provides a complete set of curl commands for API testing

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Comprehensive Curl Examples ==="
echo "This script demonstrates comprehensive API testing with curl commands"
echo

# Configuration
BASE_URL="http://localhost:8001"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$EXAMPLES_DIR/results/api_comprehensive"

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "Base URL: $BASE_URL"
echo "Results directory: $RESULTS_DIR"
echo

# Function to execute curl command with logging
execute_curl() {
    local name="$1"
    local description="$2"
    local curl_command="$3"
    local expected_status="${4:-200}"
    
    echo "=== $name ==="
    echo "Description: $description"
    echo "Command: $curl_command"
    echo
    
    # Execute curl and capture response
    local response_file="$RESULTS_DIR/${name,,}_response.json"
    local headers_file="$RESULTS_DIR/${name,,}_headers.txt"
    local timing_file="$RESULTS_DIR/${name,,}_timing.txt"
    
    # Execute with timing and headers
    if curl -s -w "HTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\nTIME_CONNECT:%{time_connect}\nTIME_NAMELOOKUP:%{time_namelookup}\nTIME_PRETRANSFER:%{time_pretransfer}\nTIME_STARTTRANSFER:%{time_starttransfer}\nSIZE_DOWNLOAD:%{size_download}\nSPEED_DOWNLOAD:%{speed_download}\n" \
           -D "$headers_file" \
           $curl_command > "$response_file" 2>&1; then
        
        # Extract timing information
        grep "HTTP_STATUS:\|TIME_\|SIZE_\|SPEED_" "$response_file" > "$timing_file"
        
        # Clean response file
        grep -v "HTTP_STATUS:\|TIME_\|SIZE_\|SPEED_" "$response_file" > "${response_file}.tmp"
        mv "${response_file}.tmp" "$response_file"
        
        # Get status code
        local status_code=$(grep "HTTP_STATUS:" "$timing_file" | cut -d: -f2)
        local time_total=$(grep "TIME_TOTAL:" "$timing_file" | cut -d: -f2)
        
        if [ "$status_code" = "$expected_status" ]; then
            echo "✓ $name: SUCCESS (Status: $status_code, Time: ${time_total}s)"
        else
            echo "✗ $name: FAILED (Expected: $expected_status, Got: $status_code, Time: ${time_total}s)"
        fi
        
        # Show response preview
        if [ -s "$response_file" ]; then
            echo "Response preview:"
            head -3 "$response_file" | sed 's/^/  /'
            if [ $(wc -l < "$response_file") -gt 3 ]; then
                echo "  ... (see full response in $response_file)"
            fi
        fi
    else
        echo "✗ $name: CURL COMMAND FAILED"
    fi
    echo
}

# Check if server is running
echo "Checking if API server is running..."
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "⚠️  API server is not running at $BASE_URL"
    echo "Please start the API server first:"
    echo "  cd EvaluationEngineV1_0_tests"
    echo "  python -c 'from api.api_test_server import APITestServer; server = APITestServer(host=\"localhost\", port=8001); server.start_server(); input(\"Press Enter to stop...\"); server.stop_server()'"
    echo
    echo "Or run the basic API examples which will start the server automatically:"
    echo "  ./basic_api_examples.sh"
    echo
    exit 1
fi

echo "✓ API server is running"
echo

# 1. Basic Health and Status Checks
echo "1. BASIC HEALTH AND STATUS CHECKS"
echo "=================================="

execute_curl "Health_Check" \
    "Basic health check to verify API server is responding" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/health'" \
    "200"

execute_curl "Server_Info" \
    "Get server information and version details" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/info'" \
    "200"

execute_curl "API_Version" \
    "Check API version and supported endpoints" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/version'" \
    "200"

# 2. Resource Discovery
echo "2. RESOURCE DISCOVERY"
echo "===================="

execute_curl "List_Tasks" \
    "Get comprehensive list of all available evaluation tasks" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "200"

execute_curl "List_Adapters" \
    "Get list of all available evaluation adapters" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/adapters'" \
    "200"

execute_curl "List_Models" \
    "Get list of supported models (if available)" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/models'" \
    "200"

execute_curl "Task_Details" \
    "Get detailed information about a specific task" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks/hellaswag'" \
    "200"

# 3. Evaluation Management
echo "3. EVALUATION MANAGEMENT"
echo "======================="

# Create evaluation request data
cat > "$RESULTS_DIR/basic_evaluation_request.json" << EOF
{
  "model_id": "comprehensive_test_model",
  "tasks": ["hellaswag"],
  "config": {
    "limit": 5,
    "description": "Comprehensive curl example evaluation",
    "test_mode": true,
    "metadata": {
      "created_by": "curl_examples",
      "purpose": "demonstration"
    }
  }
}
EOF

execute_curl "Create_Basic_Evaluation" \
    "Create a basic evaluation with single task" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/basic_evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "201"

# Extract evaluation ID for subsequent tests
EVALUATION_ID=""
if [ -f "$RESULTS_DIR/create_basic_evaluation_response.json" ]; then
    EVALUATION_ID=$(grep -o '"evaluation_id":"[^"]*"' "$RESULTS_DIR/create_basic_evaluation_response.json" | cut -d'"' -f4)
    echo "Extracted evaluation ID: $EVALUATION_ID"
fi

# Create multi-task evaluation
cat > "$RESULTS_DIR/multi_task_evaluation_request.json" << EOF
{
  "model_id": "multi_task_test_model",
  "tasks": ["hellaswag", "arc_easy"],
  "config": {
    "limit": 3,
    "description": "Multi-task evaluation example",
    "parallel": false,
    "save_predictions": true,
    "metadata": {
      "task_count": 2,
      "evaluation_type": "multi_task"
    }
  }
}
EOF

execute_curl "Create_Multi_Task_Evaluation" \
    "Create evaluation with multiple tasks" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/multi_task_evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "201"

# List all evaluations
execute_curl "List_All_Evaluations" \
    "Get list of all evaluations with status information" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations'" \
    "200"

# List evaluations with filters
execute_curl "List_Evaluations_Filtered" \
    "Get filtered list of evaluations by status" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations?status=running&limit=10'" \
    "200"

# 4. Evaluation Monitoring
if [ -n "$EVALUATION_ID" ]; then
    echo "4. EVALUATION MONITORING"
    echo "======================="
    
    execute_curl "Check_Evaluation_Status" \
        "Check current status of specific evaluation" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/status'" \
        "200"
    
    execute_curl "Get_Evaluation_Progress" \
        "Get detailed progress information for evaluation" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/progress'" \
        "200"
    
    execute_curl "Get_Evaluation_Logs" \
        "Get execution logs for evaluation" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/logs'" \
        "200"
    
    execute_curl "Get_Evaluation_Metrics" \
        "Get real-time metrics for running evaluation" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/metrics'" \
        "200"
else
    echo "4. EVALUATION MONITORING"
    echo "======================="
    echo "⚠️  Skipping monitoring tests - no evaluation ID available"
    echo
fi

# 5. Results Retrieval
if [ -n "$EVALUATION_ID" ]; then
    echo "5. RESULTS RETRIEVAL"
    echo "==================="
    
    execute_curl "Get_Evaluation_Results" \
        "Get complete results from evaluation" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results'" \
        "200"
    
    execute_curl "Get_Results_Summary" \
        "Get summarized results with key metrics" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results/summary'" \
        "200"
    
    execute_curl "Get_Results_Detailed" \
        "Get detailed results with individual predictions" \
        "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results/detailed'" \
        "200"
    
    execute_curl "Export_Results_CSV" \
        "Export results in CSV format" \
        "-X GET -H 'Accept: text/csv' '$BASE_URL/api/v1/evaluations/$EVALUATION_ID/results/export?format=csv'" \
        "200"
else
    echo "5. RESULTS RETRIEVAL"
    echo "==================="
    echo "⚠️  Skipping results tests - no evaluation ID available"
    echo
fi

# 6. Advanced Configuration Examples
echo "6. ADVANCED CONFIGURATION EXAMPLES"
echo "=================================="

# Custom configuration evaluation
cat > "$RESULTS_DIR/advanced_evaluation_request.json" << EOF
{
  "model_id": "advanced_test_model",
  "tasks": ["hellaswag"],
  "config": {
    "limit": 10,
    "batch_size": 5,
    "temperature": 0.7,
    "max_tokens": 100,
    "description": "Advanced configuration example",
    "custom_prompt_template": "Answer the following question: {question}",
    "evaluation_settings": {
      "few_shot": 3,
      "chain_of_thought": true,
      "self_consistency": false
    },
    "output_settings": {
      "save_predictions": true,
      "save_logits": false,
      "include_metadata": true
    },
    "metadata": {
      "experiment_name": "advanced_config_test",
      "researcher": "curl_examples",
      "notes": "Testing advanced configuration options"
    }
  }
}
EOF

execute_curl "Create_Advanced_Evaluation" \
    "Create evaluation with advanced configuration options" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/advanced_evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "201"

# Batch evaluation request
cat > "$RESULTS_DIR/batch_evaluation_request.json" << EOF
{
  "batch_name": "curl_examples_batch",
  "evaluations": [
    {
      "model_id": "batch_model_1",
      "tasks": ["hellaswag"],
      "config": {"limit": 2, "description": "Batch evaluation 1"}
    },
    {
      "model_id": "batch_model_2",
      "tasks": ["arc_easy"],
      "config": {"limit": 2, "description": "Batch evaluation 2"}
    }
  ],
  "batch_config": {
    "parallel": true,
    "max_concurrent": 2,
    "timeout": 300
  }
}
EOF

execute_curl "Create_Batch_Evaluation" \
    "Create batch evaluation with multiple models/tasks" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/batch_evaluation_request.json' '$BASE_URL/api/v1/evaluations/batch'" \
    "201"

# 7. Error Handling and Edge Cases
echo "7. ERROR HANDLING AND EDGE CASES"
echo "================================"

execute_curl "Invalid_Endpoint" \
    "Test handling of invalid endpoint" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/nonexistent'" \
    "404"

execute_curl "Invalid_Method" \
    "Test handling of invalid HTTP method" \
    "-X PATCH -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "405"

execute_curl "Missing_Content_Type" \
    "Test handling of missing Content-Type header" \
    "-X POST -H 'Accept: application/json' -d '{\"test\": \"data\"}' '$BASE_URL/api/v1/evaluations'" \
    "400"

# Invalid JSON request
echo '{"invalid": json}' > "$RESULTS_DIR/invalid_json.txt"
execute_curl "Invalid_JSON" \
    "Test handling of malformed JSON" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/invalid_json.txt' '$BASE_URL/api/v1/evaluations'" \
    "400"

# Empty request
execute_curl "Empty_Request" \
    "Test handling of empty request body" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d '{}' '$BASE_URL/api/v1/evaluations'" \
    "400"

# Invalid evaluation ID
execute_curl "Invalid_Evaluation_ID" \
    "Test handling of invalid evaluation ID" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations/invalid-id-12345/status'" \
    "404"

# 8. Performance and Load Testing
echo "8. PERFORMANCE AND LOAD TESTING"
echo "==============================="

execute_curl "Concurrent_Request_1" \
    "First concurrent request for load testing" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "200" &

execute_curl "Concurrent_Request_2" \
    "Second concurrent request for load testing" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/adapters'" \
    "200" &

execute_curl "Concurrent_Request_3" \
    "Third concurrent request for load testing" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations'" \
    "200" &

# Wait for concurrent requests to complete
wait

# Large request test
cat > "$RESULTS_DIR/large_evaluation_request.json" << EOF
{
  "model_id": "large_test_model",
  "tasks": ["hellaswag", "arc_easy", "arc_challenge", "winogrande"],
  "config": {
    "limit": 1,
    "description": "Large request test with multiple tasks and extensive metadata",
    "metadata": {
      "large_field_1": "$(printf 'A%.0s' {1..1000})",
      "large_field_2": "$(printf 'B%.0s' {1..1000})",
      "large_field_3": "$(printf 'C%.0s' {1..1000})",
      "notes": "Testing API handling of large request payloads"
    }
  }
}
EOF

execute_curl "Large_Request_Test" \
    "Test handling of large request payload" \
    "-X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -d @'$RESULTS_DIR/large_evaluation_request.json' '$BASE_URL/api/v1/evaluations'" \
    "201"

# 9. Authentication and Security (if enabled)
echo "9. AUTHENTICATION AND SECURITY TESTS"
echo "===================================="

execute_curl "No_Auth_Header" \
    "Test access without authentication header (if auth required)" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/evaluations'" \
    "200"

execute_curl "Invalid_Auth_Header" \
    "Test access with invalid authentication header" \
    "-X GET -H 'Accept: application/json' -H 'Authorization: Bearer invalid-token' '$BASE_URL/api/v1/evaluations'" \
    "200"

# 10. Content Negotiation
echo "10. CONTENT NEGOTIATION"
echo "======================"

execute_curl "Accept_JSON" \
    "Request JSON response format" \
    "-X GET -H 'Accept: application/json' '$BASE_URL/api/v1/tasks'" \
    "200"

execute_curl "Accept_XML" \
    "Request XML response format (may not be supported)" \
    "-X GET -H 'Accept: application/xml' '$BASE_URL/api/v1/tasks'" \
    "200"

execute_curl "Accept_Any" \
    "Accept any response format" \
    "-X GET -H 'Accept: */*' '$BASE_URL/api/v1/tasks'" \
    "200"

# Generate comprehensive test script
echo "11. GENERATING COMPREHENSIVE TEST SCRIPT"
echo "========================================"

cat > "$RESULTS_DIR/comprehensive_api_test.sh" << 'EOF'
#!/bin/bash
# Comprehensive API Test Script
# Generated by comprehensive_curl_examples.sh

BASE_URL="http://localhost:8001"
RESULTS_DIR="./api_test_results"
mkdir -p "$RESULTS_DIR"

echo "=== Comprehensive API Test ==="
echo "Base URL: $BASE_URL"
echo "Results: $RESULTS_DIR"
echo

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="${5:-200}"
    
    echo "Testing $name..."
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X "$method" \
                       -H "Content-Type: application/json" \
                       -H "Accept: application/json" \
                       -d "$data" \
                       "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X "$method" \
                       -H "Accept: application/json" \
                       "$BASE_URL$endpoint")
    fi
    
    status_code=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
    response_body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "✓ $name: SUCCESS (Status: $status_code)"
    else
        echo "✗ $name: FAILED (Expected: $expected_status, Got: $status_code)"
    fi
    
    echo "$response_body" > "$RESULTS_DIR/${name,,}_response.json"
}

# Run comprehensive tests
test_endpoint "Health Check" "GET" "/health"
test_endpoint "List Tasks" "GET" "/api/v1/tasks"
test_endpoint "List Adapters" "GET" "/api/v1/adapters"
test_endpoint "List Evaluations" "GET" "/api/v1/evaluations"

# Create evaluation
eval_data='{"model_id": "test_model", "tasks": ["hellaswag"], "config": {"limit": 2}}'
test_endpoint "Create Evaluation" "POST" "/api/v1/evaluations" "$eval_data" "201"

echo
echo "=== Test Complete ==="
echo "Check $RESULTS_DIR for detailed responses"
EOF

chmod +x "$RESULTS_DIR/comprehensive_api_test.sh"
echo "✓ Comprehensive test script created: $RESULTS_DIR/comprehensive_api_test.sh"

# Summary
echo
echo "=== COMPREHENSIVE CURL EXAMPLES SUMMARY ==="
echo "All curl examples have been executed and documented."
echo
echo "Results saved in: $RESULTS_DIR"
echo "Files created:"
ls -la "$RESULTS_DIR" | grep -v "^total" | awk '{print "  " $9 " (" $5 " bytes)"}'
echo
echo "Generated files:"
echo "  ✓ Individual response files for each API call"
echo "  ✓ Timing information for performance analysis"
echo "  ✓ HTTP headers for debugging"
echo "  ✓ Sample request payloads"
echo "  ✓ Comprehensive test script for automation"
echo
echo "Usage examples:"
echo "  1. Review individual responses: cat $RESULTS_DIR/*_response.json"
echo "  2. Check timing data: cat $RESULTS_DIR/*_timing.txt"
echo "  3. Run automated test: $RESULTS_DIR/comprehensive_api_test.sh"
echo "  4. Analyze headers: cat $RESULTS_DIR/*_headers.txt"
echo
echo "Next steps:"
echo "  • Analyze response data for API behavior understanding"
echo "  • Use timing data for performance optimization"
echo "  • Customize request payloads for specific testing needs"
echo "  • Integrate curl commands into CI/CD pipelines"
echo
echo "For troubleshooting, check individual response and timing files."