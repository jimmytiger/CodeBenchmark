# Single-Turn Evaluation Scenarios User Guide

## Overview

Single-turn evaluation scenarios assess language models on individual, self-contained tasks that require a single response. These scenarios are ideal for measuring specific capabilities like code generation, problem-solving, and technical knowledge.

## Available Single-Turn Scenarios

### 1. Code Completion (`single_turn_scenarios_code_completion`)

**Purpose**: Evaluate the model's ability to complete partial code implementations.

**Use Cases**:
- IDE autocomplete functionality
- Code assistance tools
- Programming education

**Example Problem**:
```python
# Input
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    # TODO: Implement this function

# Expected Output
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

**Metrics**:
- `pass_at_k`: Percentage of problems solved in k attempts
- `syntax_validity`: Syntactic correctness of generated code
- `code_quality_score`: Overall code quality assessment
- `execution_success`: Whether code runs without errors

**Configuration Example**:
```json
{
  "task_id": "single_turn_scenarios_code_completion",
  "context_mode": "full_context",
  "languages": ["python", "javascript", "java"],
  "difficulty_levels": ["easy", "medium", "hard"],
  "num_samples": 100
}
```

### 2. Bug Fix (`single_turn_scenarios_bug_fix`)

**Purpose**: Assess the model's ability to identify and fix bugs in existing code.

**Use Cases**:
- Automated debugging tools
- Code review assistance
- Software maintenance

**Example Problem**:
```python
# Input (buggy code)
def binary_search(arr, target):
    left, right = 0, len(arr)  # Bug: should be len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# Expected Output (fixed code)
def binary_search(arr, target):
    left, right = 0, len(arr) - 1  # Fixed: correct right boundary
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Metrics**:
- `bug_detection_accuracy`: Percentage of bugs correctly identified
- `fix_correctness`: Whether the fix resolves the issue
- `code_quality_improvement`: Quality improvement after fix
- `test_pass_rate`: Percentage of test cases passing after fix

### 3. Function Generation (`single_turn_scenarios_function_generation`)

**Purpose**: Evaluate complete function implementation from specifications.

**Use Cases**:
- API development
- Algorithm implementation
- Utility function creation

**Example Problem**:
```
# Input Specification
Function: calculate_compound_interest
Parameters:
- principal (float): Initial investment amount
- rate (float): Annual interest rate (as decimal)
- time (int): Number of years
- compound_frequency (int): Times compounded per year

Returns: Final amount after compound interest

Formula: A = P(1 + r/n)^(nt)
```

**Expected Output**:
```python
def calculate_compound_interest(principal, rate, time, compound_frequency):
    """
    Calculate compound interest.
    
    Args:
        principal: Initial investment amount
        rate: Annual interest rate (as decimal)
        time: Number of years
        compound_frequency: Times compounded per year
    
    Returns:
        Final amount after compound interest
    """
    if principal <= 0 or rate < 0 or time < 0 or compound_frequency <= 0:
        raise ValueError("Invalid input parameters")
    
    amount = principal * (1 + rate / compound_frequency) ** (compound_frequency * time)
    return round(amount, 2)
```

**Metrics**:
- `specification_compliance`: Adherence to given specifications
- `edge_case_handling`: Proper handling of edge cases
- `documentation_quality`: Quality of code documentation
- `performance_efficiency`: Algorithmic efficiency

### 4. Code Translation (`single_turn_scenarios_code_translation`)

**Purpose**: Translate code from one programming language to another.

**Use Cases**:
- Legacy system migration
- Cross-platform development
- Language learning

**Example Problem**:
```python
# Input (Python)
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

# Expected Output (JavaScript)
function quicksort(arr) {
    if (arr.length <= 1) {
        return arr;
    }
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    return [...quicksort(left), ...middle, ...quicksort(right)];
}
```

**Metrics**:
- `functional_equivalence`: Whether translated code produces same results
- `idiomatic_usage`: Use of language-specific best practices
- `performance_preservation`: Maintaining algorithmic complexity

### 5. Algorithm Implementation (`single_turn_scenarios_algorithm_implementation`)

**Purpose**: Implement algorithms from high-level descriptions.

**Use Cases**:
- Competitive programming
- Technical interviews
- Algorithm education

**Example Problem**:
```
# Input Description
Implement Dijkstra's shortest path algorithm:
- Input: Graph represented as adjacency list, start vertex
- Output: Dictionary of shortest distances from start to all vertices
- Handle disconnected vertices (distance = infinity)
- Use priority queue for efficiency
```

**Metrics**:
- `algorithmic_correctness`: Correct implementation of algorithm
- `time_complexity`: Optimal time complexity achievement
- `space_complexity`: Efficient space usage
- `code_clarity`: Readability and maintainability

### 6. API Design (`single_turn_scenarios_api_design`)

**Purpose**: Design RESTful API endpoints and schemas.

**Use Cases**:
- Backend development
- System integration
- API documentation

**Example Problem**:
```
# Input Requirements
Design a REST API for a library management system:
- Manage books (CRUD operations)
- Handle user borrowing/returning
- Track book availability
- Support search and filtering
- Include proper HTTP status codes
```

**Expected Output**:
```yaml
# Library Management API Design

# Books Management
GET /api/v1/books
  - Query params: title, author, isbn, available, limit, offset
  - Response: 200 OK, list of books with pagination

POST /api/v1/books
  - Body: book details (title, author, isbn, etc.)
  - Response: 201 Created, book object with ID

GET /api/v1/books/{book_id}
  - Response: 200 OK (book found), 404 Not Found

PUT /api/v1/books/{book_id}
  - Body: updated book details
  - Response: 200 OK, 404 Not Found

DELETE /api/v1/books/{book_id}
  - Response: 204 No Content, 404 Not Found

# Borrowing Management
POST /api/v1/books/{book_id}/borrow
  - Body: user_id, due_date
  - Response: 200 OK, 400 Bad Request (not available)

POST /api/v1/books/{book_id}/return
  - Body: user_id
  - Response: 200 OK, 400 Bad Request (not borrowed by user)
```

**Metrics**:
- `restful_compliance`: Adherence to REST principles
- `endpoint_completeness`: Coverage of required functionality
- `status_code_accuracy`: Proper HTTP status code usage
- `documentation_quality`: API documentation completeness

### 7. System Design (`single_turn_scenarios_system_design`)

**Purpose**: Design scalable system architectures.

**Use Cases**:
- System architecture planning
- Technical interviews
- Infrastructure design

**Example Problem**:
```
# Input Requirements
Design a URL shortening service (like bit.ly):
- Handle 100M URLs per day
- Support custom aliases
- Provide analytics (click tracking)
- Ensure high availability
- Consider caching strategy
```

**Metrics**:
- `scalability_considerations`: Proper scaling strategies
- `reliability_measures`: Fault tolerance and redundancy
- `performance_optimization`: Caching and optimization strategies
- `component_interaction`: Clear component relationships

### 8. Database Design (`single_turn_scenarios_database_design`)

**Purpose**: Design database schemas and queries.

**Use Cases**:
- Database architecture
- Data modeling
- Query optimization

**Example Problem**:
```
# Input Requirements
Design a database for an e-commerce platform:
- Users, products, orders, payments
- Support product categories and variants
- Handle inventory tracking
- Enable order history and analytics
- Ensure data integrity
```

**Metrics**:
- `normalization_quality`: Proper database normalization
- `query_efficiency`: Optimized query design
- `constraint_completeness`: Appropriate constraints and indexes
- `relationship_modeling`: Accurate entity relationships

### 9. Security Implementation (`single_turn_scenarios_security`)

**Purpose**: Implement security measures and identify vulnerabilities.

**Use Cases**:
- Security auditing
- Secure coding practices
- Vulnerability assessment

**Example Problem**:
```python
# Input (vulnerable code)
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    return result.fetchone() is not None

# Expected Output (secure implementation)
def login(username, password):
    # Use parameterized queries to prevent SQL injection
    query = "SELECT * FROM users WHERE username=? AND password=?"
    # Hash password before comparison
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    result = db.execute(query, (username, password_hash))
    return result.fetchone() is not None
```

**Metrics**:
- `vulnerability_detection`: Identification of security issues
- `security_best_practices`: Implementation of secure coding practices
- `compliance_adherence`: Following security standards

### 10. Performance Optimization (`single_turn_scenarios_performance_optimization`)

**Purpose**: Optimize code for better performance.

**Use Cases**:
- Performance tuning
- Algorithm optimization
- Resource efficiency

**Metrics**:
- `performance_improvement`: Measurable performance gains
- `algorithmic_efficiency`: Better time/space complexity
- `resource_optimization`: Reduced resource usage

## Running Single-Turn Evaluations

### Basic Evaluation

```python
from evaluation_engine import EvaluationClient

client = EvaluationClient(api_key="your-api-key")

# Simple code completion evaluation
evaluation = client.create_evaluation(
    models=[{
        "model_id": "openai/gpt-4",
        "model_type": "openai",
        "config": {"temperature": 0.7}
    }],
    tasks=["single_turn_scenarios_code_completion"]
)

# Wait for completion
results = client.wait_for_completion(evaluation.id)
print(f"Pass@1 Score: {results.metrics['pass_at_1']}")
```

### Advanced Configuration

```python
# Multi-language, multi-difficulty evaluation
evaluation = client.create_evaluation(
    models=[
        {"model_id": "openai/gpt-4", "model_type": "openai"},
        {"model_id": "anthropic/claude-3-opus", "model_type": "anthropic"}
    ],
    tasks=[{
        "task_id": "single_turn_scenarios_code_completion",
        "context_mode": "full_context",
        "languages": ["python", "javascript", "java"],
        "difficulty_levels": ["medium", "hard"],
        "num_samples": 200,
        "enable_sandbox": True
    }]
)
```

### Batch Evaluation

```python
# Evaluate multiple scenarios at once
scenarios = [
    "single_turn_scenarios_code_completion",
    "single_turn_scenarios_bug_fix",
    "single_turn_scenarios_function_generation"
]

evaluation = client.create_evaluation(
    models=[{"model_id": "openai/gpt-4", "model_type": "openai"}],
    tasks=scenarios
)
```

## Context Modes

### No Context (`no_context`)
- Minimal problem statement
- No examples or hints
- Tests pure model capability

### Minimal Context (`minimal_context`)
- Basic problem description
- Simple examples
- Limited background information

### Full Context (`full_context`)
- Comprehensive problem description
- Multiple examples
- Detailed specifications
- Best practices guidance

### Domain Context (`domain_context`)
- Industry-specific context
- Professional standards
- Real-world constraints

## Best Practices

### Model Selection
1. **Task Alignment**: Choose models suited for the task type
2. **Performance vs Cost**: Balance accuracy needs with budget
3. **Language Support**: Ensure model supports target languages

### Configuration Optimization
1. **Temperature Settings**: Lower for code tasks, higher for creative tasks
2. **Token Limits**: Set appropriate limits for task complexity
3. **Sampling Strategy**: Use multiple samples for better reliability

### Result Interpretation
1. **Metric Understanding**: Know what each metric measures
2. **Statistical Significance**: Consider sample sizes and confidence intervals
3. **Comparative Analysis**: Compare across models and configurations

### Common Pitfalls
1. **Overfitting to Metrics**: Don't optimize solely for specific metrics
2. **Insufficient Samples**: Use adequate sample sizes for reliable results
3. **Context Leakage**: Ensure fair evaluation without data contamination

## Troubleshooting

### Low Performance Scores
- Check context mode appropriateness
- Verify model configuration
- Review sample problems for clarity
- Consider model-specific prompt optimization

### Execution Errors
- Validate sandbox configuration
- Check language runtime availability
- Review resource limits
- Examine error logs for specific issues

### Inconsistent Results
- Increase sample size
- Check for randomness in evaluation
- Verify dataset quality
- Consider multiple evaluation runs

## Advanced Features

### Custom Metrics
```python
# Define custom evaluation metrics
custom_metrics = {
    "code_style_score": {
        "type": "custom",
        "evaluator": "style_checker",
        "config": {"style_guide": "pep8"}
    }
}

evaluation = client.create_evaluation(
    models=[{"model_id": "openai/gpt-4", "model_type": "openai"}],
    tasks=[{
        "task_id": "single_turn_scenarios_code_completion",
        "custom_metrics": custom_metrics
    }]
)
```

### A/B Testing
```python
# Compare different model configurations
evaluation = client.create_ab_test(
    model_configs=[
        {"model_id": "openai/gpt-4", "temperature": 0.3},
        {"model_id": "openai/gpt-4", "temperature": 0.7}
    ],
    tasks=["single_turn_scenarios_code_completion"],
    statistical_power=0.8
)
```

### Export and Reporting
```python
# Export detailed results
client.export_results(
    evaluation.id,
    format="pdf",
    include_samples=True,
    output_path="evaluation_report.pdf"
)

# Generate comparison report
comparison = client.compare_evaluations([eval1.id, eval2.id])
client.export_comparison(comparison, format="html")
```

This guide provides comprehensive coverage of single-turn evaluation scenarios, helping users effectively evaluate language models across diverse programming and problem-solving tasks.