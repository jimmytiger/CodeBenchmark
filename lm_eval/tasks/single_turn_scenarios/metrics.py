"""Comprehensive evaluation metrics for single_turn_scenarios tasks."""

import ast
import re
import logging
from typing import List, Dict, Any, Union, Optional, TYPE_CHECKING
from collections import Counter
import subprocess
import tempfile
import os

if TYPE_CHECKING:
    from .sandbox import ExecutionResult

eval_logger = logging.getLogger(__name__)

# Basic Metrics
def exact_match(predictions: List[str], references: List[str]) -> float:
    """Calculate exact match score between predictions and references.
    
    Args:
        predictions: List of predicted strings
        references: List of reference strings
        
    Returns:
        float: Exact match score (0.0 to 1.0)
    """
    if len(predictions) != len(references):
        eval_logger.warning(f"Length mismatch: predictions={len(predictions)}, references={len(references)}")
        return 0.0
    
    matches = sum(1 for pred, ref in zip(predictions, references) if pred.strip() == ref.strip())
    return matches / len(predictions) if predictions else 0.0

def bleu_score(predictions: List[str], references: List[str]) -> float:
    """Calculate BLEU score for text similarity.
    
    Args:
        predictions: List of predicted strings
        references: List of reference strings
        
    Returns:
        float: BLEU score (0.0 to 1.0)
    """
    try:
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        import nltk
        
        # Download required NLTK data if not present
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        if len(predictions) != len(references):
            return 0.0
        
        smoothing = SmoothingFunction().method1
        scores = []
        
        for pred, ref in zip(predictions, references):
            # Tokenize
            pred_tokens = pred.split()
            ref_tokens = [ref.split()]  # BLEU expects list of reference token lists
            
            if not pred_tokens or not ref_tokens[0]:
                scores.append(0.0)
                continue
                
            score = sentence_bleu(ref_tokens, pred_tokens, smoothing_function=smoothing)
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
        
    except ImportError:
        eval_logger.warning("NLTK not available, using simple token overlap")
        return _simple_token_overlap(predictions, references)

def _simple_token_overlap(predictions: List[str], references: List[str]) -> float:
    """Simple token overlap as fallback for BLEU score."""
    if len(predictions) != len(references):
        return 0.0
    
    scores = []
    for pred, ref in zip(predictions, references):
        pred_tokens = set(pred.split())
        ref_tokens = set(ref.split())
        
        if not ref_tokens:
            scores.append(1.0 if not pred_tokens else 0.0)
            continue
            
        overlap = len(pred_tokens & ref_tokens)
        score = overlap / len(ref_tokens)
        scores.append(score)
    
    return sum(scores) / len(scores) if scores else 0.0

def codebleu_score(predictions: List[str], references: List[str]) -> float:
    """Calculate CodeBLEU score for code similarity.
    
    Args:
        predictions: List of predicted code strings
        references: List of reference code strings
        
    Returns:
        float: CodeBLEU score (0.0 to 1.0)
    """
    try:
        # Try to use codebleu package if available
        from codebleu import calc_codebleu
        
        if len(predictions) != len(references):
            return 0.0
        
        # CodeBLEU expects specific format
        result = calc_codebleu(references, predictions, lang="python")
        return result.get('codebleu', 0.0)
        
    except ImportError:
        eval_logger.warning("CodeBLEU package not available, using AST-based similarity")
        return _ast_similarity(predictions, references)

def _ast_similarity(predictions: List[str], references: List[str]) -> float:
    """AST-based code similarity as fallback for CodeBLEU."""
    if len(predictions) != len(references):
        return 0.0
    
    scores = []
    for pred, ref in zip(predictions, references):
        try:
            pred_ast = ast.parse(pred)
            ref_ast = ast.parse(ref)
            
            # Simple AST node comparison
            pred_nodes = [type(node).__name__ for node in ast.walk(pred_ast)]
            ref_nodes = [type(node).__name__ for node in ast.walk(ref_ast)]
            
            pred_counter = Counter(pred_nodes)
            ref_counter = Counter(ref_nodes)
            
            # Calculate Jaccard similarity
            intersection = sum((pred_counter & ref_counter).values())
            union = sum((pred_counter | ref_counter).values())
            
            score = intersection / union if union > 0 else 0.0
            scores.append(score)
            
        except SyntaxError:
            # If AST parsing fails, fall back to token similarity
            scores.append(_simple_token_overlap([pred], [ref]))
    
    return sum(scores) / len(scores) if scores else 0.0

def rouge_l_score(predictions: List[str], references: List[str]) -> float:
    """Calculate ROUGE-L score for longest common subsequence.
    
    Args:
        predictions: List of predicted strings
        references: List of reference strings
        
    Returns:
        float: ROUGE-L score (0.0 to 1.0)
    """
    if len(predictions) != len(references):
        return 0.0
    
    def lcs_length(x, y):
        """Calculate longest common subsequence length."""
        m, n = len(x), len(y)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if x[i-1] == y[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    scores = []
    for pred, ref in zip(predictions, references):
        pred_tokens = pred.split()
        ref_tokens = ref.split()
        
        if not ref_tokens:
            scores.append(1.0 if not pred_tokens else 0.0)
            continue
        
        lcs_len = lcs_length(pred_tokens, ref_tokens)
        
        # ROUGE-L F1 score
        if len(pred_tokens) == 0:
            precision = 0.0
        else:
            precision = lcs_len / len(pred_tokens)
        
        recall = lcs_len / len(ref_tokens)
        
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)
        
        scores.append(f1)
    
    return sum(scores) / len(scores) if scores else 0.0

def edit_distance_score(predictions: List[str], references: List[str]) -> float:
    """Calculate normalized edit distance score.
    
    Args:
        predictions: List of predicted strings
        references: List of reference strings
        
    Returns:
        float: Normalized edit distance score (0.0 to 1.0, higher is better)
    """
    if len(predictions) != len(references):
        return 0.0
    
    def edit_distance(s1, s2):
        """Calculate edit distance between two strings."""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n]
    
    scores = []
    for pred, ref in zip(predictions, references):
        distance = edit_distance(pred, ref)
        max_len = max(len(pred), len(ref))
        
        if max_len == 0:
            scores.append(1.0)
        else:
            # Normalize to 0-1 range, where 1 is perfect match
            normalized_score = 1.0 - (distance / max_len)
            scores.append(max(0.0, normalized_score))
    
    return sum(scores) / len(scores) if scores else 0.0

# Code Quality Metrics
def syntax_validity(predictions: List[str], language: str = "python") -> float:
    """Check syntax validity of code predictions.
    
    Args:
        predictions: List of code strings
        language: Programming language
        
    Returns:
        float: Fraction of syntactically valid code (0.0 to 1.0)
    """
    if not predictions:
        return 0.0
    
    valid_count = 0
    
    for code in predictions:
        try:
            if _check_syntax_for_language(code, language):
                valid_count += 1
        except Exception as e:
            eval_logger.debug(f"Syntax check error for {language}: {e}")
            continue
    
    return valid_count / len(predictions)

def _check_syntax_for_language(code: str, language: str) -> bool:
    """Check syntax validity for specific programming language."""
    language = language.lower()
    
    if language == "python":
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    elif language in ["javascript", "js", "typescript", "ts"]:
        return _check_javascript_syntax(code)
    
    elif language == "java":
        return _check_java_syntax(code)
    
    elif language in ["c++", "cpp", "cxx"]:
        return _check_cpp_syntax(code)
    
    elif language == "go":
        return _check_go_syntax(code)
    
    elif language == "rust":
        return _check_rust_syntax(code)
    
    else:
        # For unsupported languages, do basic checks
        return _check_basic_syntax(code)

def _check_javascript_syntax(code: str) -> bool:
    """Check JavaScript/TypeScript syntax using basic validation."""
    # Basic syntax checks for JavaScript/TypeScript
    if not code.strip():
        return False
    
    # Check for balanced braces, brackets, and parentheses
    if not _check_balanced_delimiters(code):
        return False
    
    # Check for obvious syntax errors
    syntax_errors = [
        r'function\s*\(\s*\)\s*\{[^}]*$',  # Unclosed function
        r'if\s*\([^)]*\)\s*\{[^}]*$',     # Unclosed if statement
        r'for\s*\([^)]*\)\s*\{[^}]*$',    # Unclosed for loop
    ]
    
    for pattern in syntax_errors:
        if re.search(pattern, code, re.MULTILINE | re.DOTALL):
            return False
    
    return True

def _check_java_syntax(code: str) -> bool:
    """Check Java syntax using basic validation."""
    if not code.strip():
        return False
    
    # Check for balanced braces
    if not _check_balanced_delimiters(code):
        return False
    
    # Basic Java syntax patterns
    java_patterns = [
        r'class\s+\w+\s*\{',  # Class declaration
        r'public\s+static\s+void\s+main',  # Main method
        r'public\s+\w+\s+\w+\s*\(',  # Method declaration
    ]
    
    # If it looks like Java code, do more specific checks
    if any(re.search(pattern, code) for pattern in java_patterns):
        # Check for semicolons at end of statements (simplified)
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        statement_lines = [line for line in lines 
                          if not line.startswith('//') and not line.startswith('/*') 
                          and not line.endswith('{') and not line.endswith('}')]
        
        if statement_lines:
            # At least some statements should end with semicolons
            semicolon_lines = [line for line in statement_lines if line.endswith(';')]
            if len(semicolon_lines) < len(statement_lines) * 0.3:  # Allow some flexibility
                return False
    
    return True

def _check_cpp_syntax(code: str) -> bool:
    """Check C++ syntax using basic validation."""
    if not code.strip():
        return False
    
    # Check for balanced braces
    if not _check_balanced_delimiters(code):
        return False
    
    # Basic C++ syntax checks
    cpp_patterns = [
        r'#include\s*<[^>]+>',  # Include statements
        r'int\s+main\s*\(',     # Main function
        r'std::\w+',            # Standard library usage
    ]
    
    # If it looks like C++ code, check for semicolons
    if any(re.search(pattern, code) for pattern in cpp_patterns):
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        statement_lines = [line for line in lines 
                          if not line.startswith('//') and not line.startswith('/*') 
                          and not line.startswith('#') and not line.endswith('{') 
                          and not line.endswith('}')]
        
        if statement_lines:
            semicolon_lines = [line for line in statement_lines if line.endswith(';')]
            if len(semicolon_lines) < len(statement_lines) * 0.5:
                return False
    
    return True

def _check_go_syntax(code: str) -> bool:
    """Check Go syntax using basic validation."""
    if not code.strip():
        return False
    
    # Check for balanced braces
    if not _check_balanced_delimiters(code):
        return False
    
    # Basic Go syntax patterns
    go_patterns = [
        r'package\s+\w+',      # Package declaration
        r'func\s+\w+\s*\(',    # Function declaration
        r'import\s*\(',        # Import statement
    ]
    
    # Go-specific checks
    if any(re.search(pattern, code) for pattern in go_patterns):
        # Go doesn't use semicolons typically, check for proper structure
        if 'package' in code and 'func' in code:
            return True
    
    return _check_basic_syntax(code)

def _check_rust_syntax(code: str) -> bool:
    """Check Rust syntax using basic validation."""
    if not code.strip():
        return False
    
    # Check for balanced braces
    if not _check_balanced_delimiters(code):
        return False
    
    # Basic Rust syntax patterns
    rust_patterns = [
        r'fn\s+\w+\s*\(',      # Function declaration
        r'let\s+\w+\s*=',      # Variable declaration
        r'use\s+\w+',          # Use statement
    ]
    
    # Rust-specific checks
    if any(re.search(pattern, code) for pattern in rust_patterns):
        # Check for proper Rust syntax elements
        return True
    
    return _check_basic_syntax(code)

def _check_basic_syntax(code: str) -> bool:
    """Basic syntax checks that apply to most languages."""
    if not code.strip():
        return False
    
    # Check for balanced delimiters
    return _check_balanced_delimiters(code)

def _check_balanced_delimiters(code: str) -> bool:
    """Check if braces, brackets, and parentheses are balanced."""
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    
    # Remove string literals and comments to avoid false positives
    cleaned_code = _remove_strings_and_comments(code)
    
    for char in cleaned_code:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack:
                return False
            if pairs[stack.pop()] != char:
                return False
    
    return len(stack) == 0

def _remove_strings_and_comments(code: str) -> str:
    """Remove string literals and comments from code for syntax checking."""
    # This is a simplified implementation
    # Remove single-line comments
    code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
    
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    
    # Remove string literals (simplified)
    code = re.sub(r'"[^"]*"', '""', code)
    code = re.sub(r"'[^']*'", "''", code)
    
    return code

def cyclomatic_complexity(predictions: List[str], language: str = "python") -> float:
    """Calculate average cyclomatic complexity of code predictions.
    
    Args:
        predictions: List of code strings
        language: Programming language
        
    Returns:
        float: Average cyclomatic complexity
    """
    if not predictions:
        return 0.0
    
    complexities = []
    
    for code in predictions:
        try:
            complexity = _calculate_complexity_for_language(code, language)
            complexities.append(complexity)
        except Exception as e:
            eval_logger.debug(f"Complexity calculation error for {language}: {e}")
            complexities.append(1.0)  # Default complexity
    
    return sum(complexities) / len(complexities) if complexities else 1.0

def _calculate_complexity_for_language(code: str, language: str) -> float:
    """Calculate cyclomatic complexity for specific programming language."""
    language = language.lower()
    
    if language == "python":
        return _calculate_python_complexity(code)
    elif language in ["javascript", "js", "typescript", "ts"]:
        return _calculate_javascript_complexity(code)
    elif language == "java":
        return _calculate_java_complexity(code)
    elif language in ["c++", "cpp", "cxx"]:
        return _calculate_cpp_complexity(code)
    elif language == "go":
        return _calculate_go_complexity(code)
    elif language == "rust":
        return _calculate_rust_complexity(code)
    else:
        return _calculate_generic_complexity(code)

def _calculate_python_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for Python code."""
    try:
        tree = ast.parse(code)
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        
        return float(complexity)
    except:
        return 1.0

def _calculate_javascript_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for JavaScript/TypeScript code."""
    complexity = 1  # Base complexity
    
    # Count decision points using regex patterns
    patterns = [
        r'\bif\s*\(',           # if statements
        r'\belse\s+if\s*\(',    # else if statements
        r'\bwhile\s*\(',        # while loops
        r'\bfor\s*\(',          # for loops
        r'\bswitch\s*\(',       # switch statements
        r'\bcase\s+',           # case statements
        r'\bcatch\s*\(',        # catch blocks
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
        r'\?.*:',               # ternary operator
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def _calculate_java_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for Java code."""
    complexity = 1  # Base complexity
    
    patterns = [
        r'\bif\s*\(',           # if statements
        r'\belse\s+if\s*\(',    # else if statements
        r'\bwhile\s*\(',        # while loops
        r'\bfor\s*\(',          # for loops
        r'\bdo\s*\{',           # do-while loops
        r'\bswitch\s*\(',       # switch statements
        r'\bcase\s+',           # case statements
        r'\bcatch\s*\(',        # catch blocks
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
        r'\?.*:',               # ternary operator
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def _calculate_cpp_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for C++ code."""
    complexity = 1  # Base complexity
    
    patterns = [
        r'\bif\s*\(',           # if statements
        r'\belse\s+if\s*\(',    # else if statements
        r'\bwhile\s*\(',        # while loops
        r'\bfor\s*\(',          # for loops
        r'\bdo\s*\{',           # do-while loops
        r'\bswitch\s*\(',       # switch statements
        r'\bcase\s+',           # case statements
        r'\bcatch\s*\(',        # catch blocks
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
        r'\?.*:',               # ternary operator
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def _calculate_go_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for Go code."""
    complexity = 1  # Base complexity
    
    patterns = [
        r'\bif\s+',             # if statements (Go doesn't require parentheses)
        r'\belse\s+if\s+',      # else if statements
        r'\bfor\s+',            # for loops (Go's only loop construct)
        r'\bswitch\s+',         # switch statements
        r'\bcase\s+',           # case statements
        r'\bselect\s*\{',       # select statements
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def _calculate_rust_complexity(code: str) -> float:
    """Calculate cyclomatic complexity for Rust code."""
    complexity = 1  # Base complexity
    
    patterns = [
        r'\bif\s+',             # if statements
        r'\belse\s+if\s+',      # else if statements
        r'\bwhile\s+',          # while loops
        r'\bfor\s+',            # for loops
        r'\bloop\s*\{',         # infinite loops
        r'\bmatch\s+',          # match statements
        r'=>',                  # match arms
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def _calculate_generic_complexity(code: str) -> float:
    """Calculate generic cyclomatic complexity for unknown languages."""
    complexity = 1  # Base complexity
    
    # Generic patterns that might indicate decision points
    patterns = [
        r'\bif\b',              # if statements
        r'\bwhile\b',           # while loops
        r'\bfor\b',             # for loops
        r'\bswitch\b',          # switch statements
        r'\bcase\b',            # case statements
        r'&&',                  # logical AND
        r'\|\|',                # logical OR
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        complexity += len(matches)
    
    return float(complexity)

def security_score(predictions: List[str], language: str = "python") -> float:
    """Assess security of code predictions using static analysis.
    
    Args:
        predictions: List of code strings
        language: Programming language
        
    Returns:
        float: Security score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    scores = []
    
    for code in predictions:
        score = _calculate_security_score_for_language(code, language)
        scores.append(score)
    
    return sum(scores) / len(scores) if scores else 1.0

def _calculate_security_score_for_language(code: str, language: str) -> float:
    """Calculate security score for specific programming language."""
    language = language.lower()
    
    # Define dangerous patterns for different languages
    dangerous_patterns = {
        "python": [
            (r"eval\s*\(", 0.3, "Code execution via eval()"),
            (r"exec\s*\(", 0.3, "Code execution via exec()"),
            (r"__import__\s*\(", 0.2, "Dynamic imports"),
            (r"subprocess\.", 0.25, "System command execution"),
            (r"os\.system", 0.3, "Direct system calls"),
            (r"os\.popen", 0.25, "Process execution"),
            (r"open\s*\([^)]*['\"]w", 0.15, "File writing operations"),
            (r"pickle\.loads?", 0.2, "Unsafe deserialization"),
            (r"input\s*\(", 0.1, "User input without validation"),
            (r"raw_input\s*\(", 0.1, "Raw user input"),
        ],
        "javascript": [
            (r"eval\s*\(", 0.3, "Code execution via eval()"),
            (r"Function\s*\(", 0.25, "Dynamic function creation"),
            (r"setTimeout\s*\([^,]*['\"][^'\"]*['\"]", 0.2, "String-based setTimeout"),
            (r"setInterval\s*\([^,]*['\"][^'\"]*['\"]", 0.2, "String-based setInterval"),
            (r"innerHTML\s*=", 0.2, "Potential XSS via innerHTML"),
            (r"document\.write", 0.25, "Direct DOM manipulation"),
            (r"\.exec\s*\(", 0.15, "Regular expression execution"),
            (r"require\s*\([^)]*\+", 0.2, "Dynamic require statements"),
        ],
        "typescript": [
            (r"eval\s*\(", 0.3, "Code execution via eval()"),
            (r"Function\s*\(", 0.25, "Dynamic function creation"),
            (r"setTimeout\s*\([^,]*['\"][^'\"]*['\"]", 0.2, "String-based setTimeout"),
            (r"setInterval\s*\([^,]*['\"][^'\"]*['\"]", 0.2, "String-based setInterval"),
            (r"innerHTML\s*=", 0.2, "Potential XSS via innerHTML"),
            (r"document\.write", 0.25, "Direct DOM manipulation"),
            (r"any\s+", 0.05, "Use of 'any' type reduces type safety"),
        ],
        "java": [
            (r"Runtime\.getRuntime\(\)\.exec", 0.3, "System command execution"),
            (r"ProcessBuilder", 0.25, "Process execution"),
            (r"Class\.forName", 0.2, "Dynamic class loading"),
            (r"Method\.invoke", 0.2, "Reflection method invocation"),
            (r"System\.exit", 0.15, "System termination"),
            (r"File.*delete", 0.15, "File deletion operations"),
            (r"ObjectInputStream", 0.2, "Unsafe deserialization"),
            (r"ScriptEngine", 0.25, "Script execution"),
        ],
        "cpp": [
            (r"system\s*\(", 0.3, "System command execution"),
            (r"popen\s*\(", 0.25, "Process execution"),
            (r"gets\s*\(", 0.3, "Buffer overflow vulnerability"),
            (r"strcpy\s*\(", 0.2, "Unsafe string copy"),
            (r"strcat\s*\(", 0.2, "Unsafe string concatenation"),
            (r"sprintf\s*\(", 0.2, "Unsafe string formatting"),
            (r"malloc\s*\(", 0.1, "Manual memory management"),
            (r"free\s*\(", 0.1, "Manual memory deallocation"),
            (r"delete\s+", 0.1, "Manual memory deallocation"),
        ],
        "go": [
            (r"os/exec", 0.25, "System command execution"),
            (r"os\.Exec", 0.25, "Process execution"),
            (r"unsafe\.", 0.2, "Unsafe operations"),
            (r"reflect\.", 0.15, "Reflection usage"),
            (r"syscall\.", 0.2, "Direct system calls"),
            (r"os\.Remove", 0.1, "File deletion"),
        ],
        "rust": [
            (r"unsafe\s*\{", 0.2, "Unsafe code blocks"),
            (r"std::process::Command", 0.2, "System command execution"),
            (r"std::ptr::", 0.15, "Raw pointer operations"),
            (r"transmute", 0.25, "Memory transmutation"),
            (r"from_raw", 0.2, "Raw pointer conversion"),
            (r"as_mut_ptr", 0.1, "Mutable raw pointer access"),
        ]
    }
    
    # Get patterns for the specified language, fallback to generic patterns
    patterns = dangerous_patterns.get(language, dangerous_patterns.get("python", []))
    
    total_penalty = 0.0
    violations = []
    
    for pattern, penalty, description in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        if matches:
            violation_count = len(matches)
            total_penalty += penalty * violation_count
            violations.append(f"{description}: {violation_count} occurrences")
    
    # Additional language-agnostic security checks
    generic_violations = _check_generic_security_patterns(code)
    total_penalty += generic_violations
    
    # Calculate final score (higher penalty = lower score)
    score = max(0.0, 1.0 - total_penalty)
    
    if violations:
        eval_logger.debug(f"Security violations found: {violations}")
    
    return score

def _check_generic_security_patterns(code: str) -> float:
    """Check for generic security patterns that apply to most languages."""
    penalty = 0.0
    
    # Check for hardcoded credentials patterns
    credential_patterns = [
        (r"password\s*=\s*['\"][^'\"]{3,}['\"]", 0.2, "Hardcoded password"),
        (r"api_?key\s*=\s*['\"][^'\"]{10,}['\"]", 0.2, "Hardcoded API key"),
        (r"secret\s*=\s*['\"][^'\"]{5,}['\"]", 0.15, "Hardcoded secret"),
        (r"token\s*=\s*['\"][^'\"]{10,}['\"]", 0.15, "Hardcoded token"),
    ]
    
    for pattern, pen, desc in credential_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            penalty += pen
    
    # Check for SQL injection patterns
    sql_patterns = [
        (r"['\"].*\+.*['\"].*WHERE", 0.25, "Potential SQL injection"),
        (r"['\"].*%s.*['\"].*SELECT", 0.25, "String formatting in SQL"),
        (r"['\"].*\{.*\}.*['\"].*INSERT", 0.2, "String interpolation in SQL"),
    ]
    
    for pattern, pen, desc in sql_patterns:
        if re.search(pattern, code, re.IGNORECASE | re.DOTALL):
            penalty += pen
    
    # Check for path traversal patterns
    path_patterns = [
        (r"\.\.\/", 0.15, "Path traversal attempt"),
        (r"\.\.[\\\\]", 0.15, "Path traversal attempt (Windows)"),
    ]
    
    for pattern, pen, desc in path_patterns:
        if re.search(pattern, code):
            penalty += pen
    
    return penalty

def performance_score(predictions: List[str], execution_results: Optional[List[Dict]] = None, language: str = "python") -> float:
    """Assess performance of code predictions.
    
    Args:
        predictions: List of code strings
        execution_results: Optional execution results with timing info
        language: Programming language for static analysis
        
    Returns:
        float: Performance score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    if execution_results and len(execution_results) == len(predictions):
        # Use actual execution times and memory usage if available
        scores = []
        times = [result.get('wall_time', 1.0) for result in execution_results]
        memories = [result.get('peak_memory_mb', 100) for result in execution_results]
        
        # Normalize times and memory usage
        max_time = max(times) if times else 1.0
        max_memory = max(memories) if memories else 100
        
        for i, (time, memory) in enumerate(zip(times, memories)):
            # Combine time and memory efficiency
            time_score = 1.0 - (time / max_time) if max_time > 0 else 1.0
            memory_score = 1.0 - (memory / max_memory) if max_memory > 0 else 1.0
            
            # Weight time more heavily than memory
            combined_score = 0.7 * time_score + 0.3 * memory_score
            
            # Also consider static analysis
            static_score = _analyze_performance_patterns(predictions[i], language)
            
            # Combine dynamic and static scores
            final_score = 0.8 * combined_score + 0.2 * static_score
            scores.append(final_score)
        
        return sum(scores) / len(scores)
    else:
        # Static analysis for performance patterns
        scores = []
        for code in predictions:
            score = _analyze_performance_patterns(code, language)
            scores.append(score)
        return sum(scores) / len(scores)

def _analyze_performance_patterns(code: str, language: str = "python") -> float:
    """Analyze code for performance patterns based on language."""
    language = language.lower()
    
    if language == "python":
        return _analyze_python_performance(code)
    elif language in ["javascript", "js", "typescript", "ts"]:
        return _analyze_javascript_performance(code)
    elif language == "java":
        return _analyze_java_performance(code)
    elif language in ["c++", "cpp", "cxx"]:
        return _analyze_cpp_performance(code)
    elif language == "go":
        return _analyze_go_performance(code)
    elif language == "rust":
        return _analyze_rust_performance(code)
    else:
        return _analyze_generic_performance(code)

def _analyze_python_performance(code: str) -> float:
    """Analyze Python code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"for.*in.*range\(len\(", 0.15, "Inefficient iteration pattern"),
        (r"\.append\(.*\)\s*$", 0.05, "Multiple appends in loop"),
        (r"\+\s*=.*\[.*\]", 0.1, "List concatenation with +="),
        (r"\.keys\(\)\s*\)", 0.05, "Unnecessary .keys() call"),
        (r"len\(.*\)\s*==\s*0", 0.05, "Use 'not list' instead of len() == 0"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code))
        if matches > 0:
            score -= penalty * min(matches, 3)  # Cap penalty
    
    # Efficient patterns (bonus points)
    efficient_patterns = [
        (r"list\(.*\)", 0.05, "List comprehension usage"),
        (r"\[.*for.*in.*\]", 0.1, "List comprehension"),
        (r"enumerate\(", 0.05, "Using enumerate()"),
        (r"zip\(", 0.05, "Using zip()"),
        (r"collections\.", 0.05, "Using collections module"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_javascript_performance(code: str) -> float:
    """Analyze JavaScript/TypeScript code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"document\.getElementById", 0.1, "Repeated DOM queries"),
        (r"innerHTML\s*\+=", 0.15, "Inefficient DOM manipulation"),
        (r"for\s*\(.*\.length", 0.1, "Length property in loop condition"),
        (r"new\s+Array\(", 0.05, "Array constructor usage"),
        (r"==\s*true|==\s*false", 0.05, "Unnecessary boolean comparison"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code, re.IGNORECASE))
        if matches > 0:
            score -= penalty * min(matches, 3)
    
    # Efficient patterns
    efficient_patterns = [
        (r"\.map\(", 0.05, "Using map()"),
        (r"\.filter\(", 0.05, "Using filter()"),
        (r"\.reduce\(", 0.05, "Using reduce()"),
        (r"const\s+", 0.02, "Using const declarations"),
        (r"===", 0.02, "Strict equality comparison"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_java_performance(code: str) -> float:
    """Analyze Java code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"String\s*\+", 0.1, "String concatenation with +"),
        (r"new\s+String\(", 0.05, "Unnecessary String constructor"),
        (r"\.equals\(.*\)\s*==\s*true", 0.05, "Redundant boolean comparison"),
        (r"Vector\s*<", 0.1, "Using Vector instead of ArrayList"),
        (r"Hashtable\s*<", 0.1, "Using Hashtable instead of HashMap"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code, re.IGNORECASE))
        if matches > 0:
            score -= penalty * min(matches, 3)
    
    # Efficient patterns
    efficient_patterns = [
        (r"StringBuilder", 0.1, "Using StringBuilder"),
        (r"ArrayList\s*<", 0.05, "Using ArrayList"),
        (r"HashMap\s*<", 0.05, "Using HashMap"),
        (r"enhanced\s+for|for\s*\(.*:", 0.05, "Enhanced for loop"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_cpp_performance(code: str) -> float:
    """Analyze C++ code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"endl", 0.05, "Using endl instead of \\n"),
        (r"new\s+.*\[", 0.1, "Dynamic array allocation"),
        (r"vector.*push_back.*loop", 0.05, "Repeated push_back in loop"),
        (r"string\s*\+", 0.1, "String concatenation"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code, re.IGNORECASE))
        if matches > 0:
            score -= penalty * min(matches, 3)
    
    # Efficient patterns
    efficient_patterns = [
        (r"std::move", 0.1, "Using move semantics"),
        (r"const\s+.*&", 0.05, "Const references"),
        (r"reserve\(", 0.05, "Vector reserve"),
        (r"emplace", 0.05, "Using emplace"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_go_performance(code: str) -> float:
    """Analyze Go code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"fmt\.Sprintf.*\+", 0.1, "String concatenation with Sprintf"),
        (r"range.*len\(", 0.05, "Unnecessary len() in range"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code))
        if matches > 0:
            score -= penalty * min(matches, 3)
    
    # Efficient patterns
    efficient_patterns = [
        (r"strings\.Builder", 0.1, "Using strings.Builder"),
        (r"make\(.*,.*,", 0.05, "Pre-allocating slices"),
        (r"sync\.Pool", 0.1, "Using object pools"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_rust_performance(code: str) -> float:
    """Analyze Rust code for performance patterns."""
    score = 1.0
    
    # Inefficient patterns
    inefficient_patterns = [
        (r"\.clone\(\)", 0.1, "Unnecessary cloning"),
        (r"String::from.*\+", 0.1, "String concatenation"),
        (r"collect\(\).*iter", 0.05, "Unnecessary collect/iter"),
    ]
    
    for pattern, penalty, desc in inefficient_patterns:
        matches = len(re.findall(pattern, code))
        if matches > 0:
            score -= penalty * min(matches, 3)
    
    # Efficient patterns
    efficient_patterns = [
        (r"\.iter\(\)", 0.05, "Using iterators"),
        (r"\.map\(", 0.05, "Using map"),
        (r"\.filter\(", 0.05, "Using filter"),
        (r"with_capacity", 0.1, "Pre-allocating capacity"),
    ]
    
    for pattern, bonus, desc in efficient_patterns:
        if re.search(pattern, code):
            score += bonus
    
    return max(0.0, min(1.0, score))

def _analyze_generic_performance(code: str) -> float:
    """Analyze generic code for basic performance patterns."""
    score = 1.0
    
    # Basic inefficient patterns
    if len(re.findall(r"for.*for.*for", code)) > 0:  # Nested loops
        score -= 0.2
    
    if len(re.findall(r"while.*while", code)) > 0:  # Nested while loops
        score -= 0.1
    
    # Count total loops
    loop_count = len(re.findall(r"\b(for|while)\b", code, re.IGNORECASE))
    if loop_count > 5:
        score -= 0.1
    
    return max(0.0, score)

def code_style_score(predictions: List[str], language: str = "python") -> float:
    """Assess code style compliance for various programming languages.
    
    Args:
        predictions: List of code strings
        language: Programming language
        
    Returns:
        float: Style score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    scores = []
    
    for code in predictions:
        score = _check_style_for_language(code, language)
        scores.append(score)
    
    return sum(scores) / len(scores)

def _check_style_for_language(code: str, language: str) -> float:
    """Check code style for specific programming language."""
    language = language.lower()
    
    if language == "python":
        return _check_python_style(code)
    elif language in ["javascript", "js", "typescript", "ts"]:
        return _check_javascript_style(code)
    elif language == "java":
        return _check_java_style(code)
    elif language in ["c++", "cpp", "cxx"]:
        return _check_cpp_style(code)
    elif language == "go":
        return _check_go_style(code)
    elif language == "rust":
        return _check_rust_style(code)
    else:
        return _check_general_style(code)

def _check_python_style(code: str) -> float:
    """Check Python code style (PEP 8 compliance)."""
    score = 1.0
    lines = code.split('\n')
    
    for i, line in enumerate(lines):
        # Check line length (PEP 8: 79 characters, but we'll be lenient at 100)
        if len(line) > 100:
            score -= 0.02
        
        # Check for proper spacing around operators
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01  # Missing spaces around operators
        
        # Check for proper spacing after commas
        if re.search(r',[a-zA-Z0-9]', line):
            score -= 0.01  # Missing space after comma
        
        # Check for trailing whitespace
        if line.endswith(' ') or line.endswith('\t'):
            score -= 0.01
        
        # Check for proper function/method naming (snake_case)
        func_matches = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for func_name in func_matches:
            if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                score -= 0.05  # Not snake_case
        
        # Check for proper class naming (PascalCase)
        class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for class_name in class_matches:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                score -= 0.05  # Not PascalCase
    
    # Check for consistent indentation (4 spaces)
    indented_lines = [line for line in lines if line.startswith(' ') or line.startswith('\t')]
    if indented_lines:
        # Check if using tabs vs spaces consistently
        tab_lines = [line for line in indented_lines if line.startswith('\t')]
        space_lines = [line for line in indented_lines if line.startswith(' ')]
        
        if tab_lines and space_lines:
            score -= 0.1  # Mixed tabs and spaces
        
        # Check for 4-space indentation
        if space_lines:
            indents = [len(line) - len(line.lstrip()) for line in space_lines]
            non_four_space = [indent for indent in indents if indent % 4 != 0]
            if non_four_space:
                score -= 0.05  # Not 4-space indentation
    
    return max(0.0, score)

def _check_javascript_style(code: str) -> float:
    """Check JavaScript/TypeScript code style."""
    score = 1.0
    lines = code.split('\n')
    
    for line in lines:
        # Check line length
        if len(line) > 120:
            score -= 0.02
        
        # Check for semicolons at end of statements
        if re.search(r'[a-zA-Z0-9\)\]]\s*$', line.strip()) and not line.strip().endswith((';', '{', '}', ',')):
            if not re.search(r'(if|else|for|while|function|class)\s*\(', line):
                score -= 0.01  # Missing semicolon
        
        # Check for proper spacing
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01  # Missing spaces around operators
        
        # Check for camelCase function names
        func_matches = re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for func_name in func_matches:
            if not re.match(r'^[a-z][a-zA-Z0-9]*$', func_name):
                score -= 0.03  # Not camelCase
    
    # Check for consistent indentation (2 spaces is common in JS)
    indented_lines = [line for line in lines if line.startswith(' ')]
    if indented_lines:
        indents = [len(line) - len(line.lstrip()) for line in indented_lines]
        non_two_space = [indent for indent in indents if indent % 2 != 0]
        if non_two_space:
            score -= 0.03
    
    return max(0.0, score)

def _check_java_style(code: str) -> float:
    """Check Java code style."""
    score = 1.0
    lines = code.split('\n')
    
    for line in lines:
        # Check line length
        if len(line) > 120:
            score -= 0.02
        
        # Check for proper class naming (PascalCase)
        class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for class_name in class_matches:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                score -= 0.05  # Not PascalCase
        
        # Check for proper method naming (camelCase)
        method_matches = re.findall(r'(public|private|protected)?\s*\w+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
        for _, method_name in method_matches:
            if not re.match(r'^[a-z][a-zA-Z0-9]*$', method_name) and method_name not in ['main']:
                score -= 0.03  # Not camelCase
        
        # Check for proper spacing
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01  # Missing spaces around operators
        
        # Check for opening brace style (same line)
        if re.search(r'\)\s*\n\s*\{', code):
            score -= 0.02  # Brace on new line (not Java convention)
    
    # Check for consistent indentation (4 spaces)
    indented_lines = [line for line in lines if line.startswith(' ')]
    if indented_lines:
        indents = [len(line) - len(line.lstrip()) for line in indented_lines]
        non_four_space = [indent for indent in indents if indent % 4 != 0]
        if non_four_space:
            score -= 0.03
    
    return max(0.0, score)

def _check_cpp_style(code: str) -> float:
    """Check C++ code style."""
    score = 1.0
    lines = code.split('\n')
    
    for line in lines:
        # Check line length
        if len(line) > 120:
            score -= 0.02
        
        # Check for proper spacing around operators
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01
        
        # Check for proper pointer/reference spacing
        if re.search(r'\w\*\w|\w&\w', line):
            score -= 0.01  # Should have space around * and &
        
        # Check for include guard or pragma once
        if '#ifndef' in code or '#pragma once' in code:
            score += 0.02  # Bonus for header guards
    
    # Check for consistent indentation
    indented_lines = [line for line in lines if line.startswith(' ')]
    if indented_lines:
        indents = [len(line) - len(line.lstrip()) for line in indented_lines]
        # C++ commonly uses 2 or 4 spaces
        consistent_indent = all(indent % 2 == 0 for indent in indents)
        if not consistent_indent:
            score -= 0.03
    
    return max(0.0, score)

def _check_go_style(code: str) -> float:
    """Check Go code style (gofmt compliance)."""
    score = 1.0
    lines = code.split('\n')
    
    for line in lines:
        # Check line length
        if len(line) > 120:
            score -= 0.02
        
        # Check for proper spacing (gofmt enforces this)
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01
        
        # Check for proper function naming (camelCase for exported, lowercase for unexported)
        func_matches = re.findall(r'func\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for func_name in func_matches:
            # Go naming conventions are strict
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', func_name):
                score -= 0.03
    
    # Go uses tabs for indentation
    indented_lines = [line for line in lines if line.startswith('\t') or line.startswith(' ')]
    if indented_lines:
        tab_lines = [line for line in indented_lines if line.startswith('\t')]
        space_lines = [line for line in indented_lines if line.startswith(' ')]
        
        # Go strongly prefers tabs
        if space_lines and len(space_lines) > len(tab_lines):
            score -= 0.1
    
    return max(0.0, score)

def _check_rust_style(code: str) -> float:
    """Check Rust code style (rustfmt compliance)."""
    score = 1.0
    lines = code.split('\n')
    
    for line in lines:
        # Check line length
        if len(line) > 100:
            score -= 0.02
        
        # Check for proper spacing
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', line):
            score -= 0.01
        
        # Check for proper function naming (snake_case)
        func_matches = re.findall(r'fn\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for func_name in func_matches:
            if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                score -= 0.03  # Not snake_case
        
        # Check for proper struct naming (PascalCase)
        struct_matches = re.findall(r'struct\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        for struct_name in struct_matches:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', struct_name):
                score -= 0.03  # Not PascalCase
    
    # Check for consistent indentation (4 spaces)
    indented_lines = [line for line in lines if line.startswith(' ')]
    if indented_lines:
        indents = [len(line) - len(line.lstrip()) for line in indented_lines]
        non_four_space = [indent for indent in indents if indent % 4 != 0]
        if non_four_space:
            score -= 0.03
    
    return max(0.0, score)

def _check_general_style(code: str) -> float:
    """Check general code style for unknown languages."""
    score = 1.0
    
    # Basic checks that apply to most languages
    if not code.strip():
        return 0.0
    
    lines = code.split('\n')
    
    # Check for consistent indentation
    indented_lines = [line for line in lines if line.strip() and (line.startswith(' ') or line.startswith('\t'))]
    if indented_lines:
        # Check for mixed tabs and spaces
        tab_lines = [line for line in indented_lines if line.startswith('\t')]
        space_lines = [line for line in indented_lines if line.startswith(' ')]
        
        if tab_lines and space_lines:
            score -= 0.1  # Mixed indentation
        
        # Check for consistent indentation levels
        if space_lines:
            indents = [len(line) - len(line.lstrip()) for line in space_lines]
            unique_indents = set(indents)
            if len(unique_indents) > len(indents) * 0.7:  # Too many different indent levels
                score -= 0.05
    
    # Check line lengths
    long_lines = [line for line in lines if len(line) > 120]
    if long_lines:
        score -= 0.02 * min(len(long_lines), 5)  # Penalty for long lines
    
    # Check for trailing whitespace
    trailing_ws_lines = [line for line in lines if line.endswith(' ') or line.endswith('\t')]
    if trailing_ws_lines:
        score -= 0.01 * min(len(trailing_ws_lines), 10)
    
    return max(0.0, score)

# Functional Metrics
# Removed duplicate pass_at_k function - using the more complete version below

def runtime_correctness(execution_results: List[Dict]) -> float:
    """Calculate runtime correctness based on execution results.
    
    Args:
        execution_results: List of execution results
        
    Returns:
        float: Runtime correctness score (0.0 to 1.0)
    """
    if not execution_results:
        return 0.0
    
    correct = sum(1 for result in execution_results 
                 if result.get('exit_code', 1) == 0 and not result.get('stderr', '').strip())
    return correct / len(execution_results)

def memory_efficiency(execution_results: List[Dict]) -> float:
    """Calculate memory efficiency score.
    
    Args:
        execution_results: List of execution results with memory info
        
    Returns:
        float: Memory efficiency score (0.0 to 1.0, higher is better)
    """
    if not execution_results:
        return 0.0
    
    memory_usages = [result.get('peak_memory_mb', 100) for result in execution_results]
    
    if not memory_usages:
        return 0.0
    
    # Normalize memory usage (lower usage = higher score)
    max_memory = max(memory_usages)
    if max_memory == 0:
        return 1.0
    
    scores = [1.0 - (memory / max_memory) for memory in memory_usages]
    return sum(scores) / len(scores)

# Metric Aggregation and Statistical Analysis Functions
def aggregate_metrics(metric_results: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """Aggregate metric results with statistical analysis.
    
    Args:
        metric_results: Dictionary mapping metric names to lists of scores
        
    Returns:
        Dict with aggregated statistics for each metric
    """
    import statistics
    
    aggregated = {}
    
    for metric_name, scores in metric_results.items():
        if not scores:
            aggregated[metric_name] = {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }
            continue
        
        # Filter out None values
        valid_scores = [s for s in scores if s is not None]
        
        if not valid_scores:
            aggregated[metric_name] = {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }
            continue
        
        aggregated[metric_name] = {
            'mean': statistics.mean(valid_scores),
            'median': statistics.median(valid_scores),
            'std': statistics.stdev(valid_scores) if len(valid_scores) > 1 else 0.0,
            'min': min(valid_scores),
            'max': max(valid_scores),
            'count': len(valid_scores)
        }
    
    return aggregated

def calculate_confidence_interval(scores: List[float], confidence: float = 0.95) -> tuple:
    """Calculate confidence interval for a list of scores.
    
    Args:
        scores: List of metric scores
        confidence: Confidence level (default 0.95)
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    import statistics
    import math
    
    if not scores or len(scores) < 2:
        return (0.0, 0.0)
    
    valid_scores = [s for s in scores if s is not None]
    if len(valid_scores) < 2:
        return (0.0, 0.0)
    
    mean = statistics.mean(valid_scores)
    std = statistics.stdev(valid_scores)
    n = len(valid_scores)
    
    # Use t-distribution for small samples, normal for large
    if n < 30:
        # Simplified t-distribution approximation
        t_value = 2.0 if confidence >= 0.95 else 1.65
    else:
        # Normal distribution
        t_value = 1.96 if confidence >= 0.95 else 1.65
    
    margin_error = t_value * (std / math.sqrt(n))
    
    return (
        max(0.0, mean - margin_error),
        min(1.0, mean + margin_error)
    )

def compute_metric_correlations(metric_results: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """Compute correlations between different metrics.
    
    Args:
        metric_results: Dictionary mapping metric names to lists of scores
        
    Returns:
        Dictionary of pairwise correlations between metrics
    """
    import statistics
    
    correlations = {}
    metric_names = list(metric_results.keys())
    
    for i, metric1 in enumerate(metric_names):
        correlations[metric1] = {}
        scores1 = [s for s in metric_results[metric1] if s is not None]
        
        for j, metric2 in enumerate(metric_names):
            if i == j:
                correlations[metric1][metric2] = 1.0
                continue
            
            scores2 = [s for s in metric_results[metric2] if s is not None]
            
            # Ensure same length
            min_len = min(len(scores1), len(scores2))
            if min_len < 2:
                correlations[metric1][metric2] = 0.0
                continue
            
            s1 = scores1[:min_len]
            s2 = scores2[:min_len]
            
            # Calculate Pearson correlation
            correlation = _pearson_correlation(s1, s2)
            correlations[metric1][metric2] = correlation
    
    return correlations

def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    import statistics
    
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    
    sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
    sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
    
    denominator = (sum_sq_x * sum_sq_y) ** 0.5
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator

def normalize_scores(scores: List[float], method: str = "min_max") -> List[float]:
    """Normalize scores using specified method.
    
    Args:
        scores: List of scores to normalize
        method: Normalization method ("min_max", "z_score", "robust")
        
    Returns:
        List of normalized scores
    """
    import statistics
    
    if not scores:
        return []
    
    valid_scores = [s for s in scores if s is not None]
    if not valid_scores:
        return [0.0] * len(scores)
    
    if method == "min_max":
        min_score = min(valid_scores)
        max_score = max(valid_scores)
        if max_score == min_score:
            return [0.5] * len(scores)
        
        normalized = []
        for score in scores:
            if score is None:
                normalized.append(0.0)
            else:
                norm_score = (score - min_score) / (max_score - min_score)
                normalized.append(norm_score)
        return normalized
    
    elif method == "z_score":
        mean_score = statistics.mean(valid_scores)
        std_score = statistics.stdev(valid_scores) if len(valid_scores) > 1 else 1.0
        
        normalized = []
        for score in scores:
            if score is None:
                normalized.append(0.0)
            else:
                norm_score = (score - mean_score) / std_score
                normalized.append(norm_score)
        return normalized
    
    elif method == "robust":
        # Use median and MAD (Median Absolute Deviation)
        median_score = statistics.median(valid_scores)
        mad = statistics.median([abs(s - median_score) for s in valid_scores])
        if mad == 0:
            mad = 1.0
        
        normalized = []
        for score in scores:
            if score is None:
                normalized.append(0.0)
            else:
                norm_score = (score - median_score) / mad
                normalized.append(norm_score)
        return normalized
    
    else:
        raise ValueError(f"Unknown normalization method: {method}")

def compute_composite_score(metric_results: Dict[str, List[float]], 
                          weights: Optional[Dict[str, float]] = None) -> List[float]:
    """Compute weighted composite score from multiple metrics.
    
    Args:
        metric_results: Dictionary mapping metric names to lists of scores
        weights: Optional weights for each metric (default: equal weights)
        
    Returns:
        List of composite scores
    """
    if not metric_results:
        return []
    
    # Get the length of score lists
    score_lengths = [len(scores) for scores in metric_results.values()]
    if not score_lengths:
        return []
    
    max_length = max(score_lengths)
    
    # Set default weights if not provided
    if weights is None:
        weights = {metric: 1.0 for metric in metric_results.keys()}
    
    # Normalize weights
    total_weight = sum(weights.values())
    if total_weight == 0:
        return [0.0] * max_length
    
    normalized_weights = {k: v / total_weight for k, v in weights.items()}
    
    composite_scores = []
    
    for i in range(max_length):
        weighted_sum = 0.0
        valid_weight_sum = 0.0
        
        for metric, scores in metric_results.items():
            if i < len(scores) and scores[i] is not None:
                weight = normalized_weights.get(metric, 0.0)
                weighted_sum += scores[i] * weight
                valid_weight_sum += weight
        
        if valid_weight_sum > 0:
            composite_scores.append(weighted_sum / valid_weight_sum)
        else:
            composite_scores.append(0.0)
    
    return composite_scores


# Functional Correctness Metrics
def pass_at_k(predictions: List[str], tests: List[Dict], k: int = 1, 
              language: str = "python", num_samples: int = 1) -> float:
    """Calculate Pass@K metric with proper sampling strategies.
    
    Pass@K measures the probability that at least one of the top-k generated
    solutions passes all test cases. This is a key metric for code generation.
    
    Args:
        predictions: List of code predictions (can be multiple per problem)
        tests: List of test definitions with test cases
        k: Number of samples to consider (default: 1 for Pass@1)
        language: Programming language for execution
        num_samples: Number of samples per problem (for sampling strategy)
        
    Returns:
        float: Pass@K score (0.0 to 1.0)
    """
    if not predictions or not tests:
        return 0.0
    
    if k <= 0:
        return 0.0
    
    # Import sandbox executor for code execution
    try:
        from .sandbox import SandboxExecutor
    except ImportError:
        eval_logger.warning("SandboxExecutor not available, using syntax-only validation")
        return _pass_at_k_syntax_only(predictions, k)
    
    # Group predictions by problem (assuming predictions are ordered by problem)
    problems_count = len(tests)
    samples_per_problem = len(predictions) // problems_count if problems_count > 0 else 0
    
    if samples_per_problem == 0:
        return 0.0
    
    total_problems = 0
    passed_problems = 0
    
    try:
        # Initialize sandbox executor
        executor = SandboxExecutor(language)
        
        for problem_idx in range(problems_count):
            total_problems += 1
            
            # Get predictions for this problem
            start_idx = problem_idx * samples_per_problem
            end_idx = start_idx + min(samples_per_problem, k)
            problem_predictions = predictions[start_idx:end_idx]
            
            # Get test cases for this problem
            problem_tests = tests[problem_idx] if isinstance(tests[problem_idx], list) else [tests[problem_idx]]
            
            # Check if any of the k predictions pass all tests
            problem_passed = False
            
            for pred in problem_predictions:
                if _execute_and_validate(executor, pred, problem_tests):
                    problem_passed = True
                    break
            
            if problem_passed:
                passed_problems += 1
                
    except Exception as e:
        eval_logger.error(f"Pass@K execution failed: {e}")
        return 0.0
    
    return passed_problems / total_problems if total_problems > 0 else 0.0


def _pass_at_k_syntax_only(predictions: List[str], k: int) -> float:
    """Fallback Pass@K using syntax validation only."""
    if not predictions:
        return 0.0
    
    valid_count = 0
    total_count = min(len(predictions), k)
    
    for pred in predictions[:total_count]:
        try:
            ast.parse(pred)  # Basic syntax check for Python
            valid_count += 1
        except SyntaxError:
            continue
    
    return valid_count / total_count if total_count > 0 else 0.0


def _execute_and_validate(executor, code: str, tests: List[Dict]) -> bool:
    """Execute code and validate against test cases."""
    try:
        # Execute code with tests
        result = executor.execute_code(code, tests)
        
        # Check if execution was successful and no security violations
        if not result.success or result.security_violations:
            return False
        
        # Check exit code
        if result.exit_code != 0:
            return False
        
        # Additional validation can be added here based on test specifications
        return True
        
    except Exception as e:
        eval_logger.debug(f"Code execution failed: {e}")
        return False


def test_coverage(predictions: List[str], tests: List[Dict], 
                 language: str = "python") -> float:
    """Analyze test coverage using language-specific tools.
    
    Measures how much of the test suite is covered by the generated code.
    This helps assess the completeness of the solution.
    
    Args:
        predictions: List of code predictions
        tests: List of test definitions
        language: Programming language
        
    Returns:
        float: Average test coverage score (0.0 to 1.0)
    """
    if not predictions or not tests:
        return 0.0
    
    coverage_scores = []
    
    for pred in predictions:
        try:
            coverage = _calculate_coverage_for_language(pred, tests, language)
            coverage_scores.append(coverage)
        except Exception as e:
            eval_logger.debug(f"Coverage calculation failed: {e}")
            coverage_scores.append(0.0)
    
    return sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0


def _calculate_coverage_for_language(code: str, tests: List[Dict], language: str) -> float:
    """Calculate test coverage for specific programming language."""
    language = language.lower()
    
    if language == "python":
        return _calculate_python_coverage(code, tests)
    elif language in ["javascript", "js", "typescript", "ts"]:
        return _calculate_javascript_coverage(code, tests)
    elif language == "java":
        return _calculate_java_coverage(code, tests)
    elif language in ["c++", "cpp", "cxx", "c"]:
        return _calculate_cpp_coverage(code, tests)
    elif language == "go":
        return _calculate_go_coverage(code, tests)
    elif language == "rust":
        return _calculate_rust_coverage(code, tests)
    else:
        return _calculate_generic_coverage(code, tests)


def _calculate_python_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for Python code."""
    try:
        # Parse the code to get function/class definitions
        tree = ast.parse(code)
        
        # Extract function and class names
        defined_items = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defined_items.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined_items.add(node.name)
        
        if not defined_items:
            return 0.0
        
        # Check how many defined items are tested
        tested_items = set()
        for test in tests:
            test_content = test.get('content', '') if isinstance(test, dict) else str(test)
            
            for item in defined_items:
                if item in test_content:
                    tested_items.add(item)
        
        return len(tested_items) / len(defined_items) if defined_items else 0.0
        
    except Exception as e:
        eval_logger.debug(f"Python coverage calculation failed: {e}")
        return 0.0


def _calculate_javascript_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for JavaScript/TypeScript code."""
    # Simple heuristic: look for function declarations and exports
    import re
    
    # Find function declarations
    function_patterns = [
        r'function\s+(\w+)\s*\(',
        r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
        r'let\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
        r'var\s+(\w+)\s*=\s*function',
        r'export\s+function\s+(\w+)',
        r'exports\.(\w+)\s*=',
    ]
    
    defined_functions = set()
    for pattern in function_patterns:
        matches = re.findall(pattern, code, re.MULTILINE)
        defined_functions.update(matches)
    
    if not defined_functions:
        return 0.0
    
    # Check test coverage
    tested_functions = set()
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        
        for func in defined_functions:
            if func in test_content:
                tested_functions.add(func)
    
    return len(tested_functions) / len(defined_functions) if defined_functions else 0.0


def _calculate_java_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for Java code."""
    import re
    
    # Find method declarations
    method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{'
    methods = set(re.findall(method_pattern, code))
    
    if not methods:
        return 0.0
    
    # Check test coverage
    tested_methods = set()
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        
        for method in methods:
            if method in test_content:
                tested_methods.add(method)
    
    return len(tested_methods) / len(methods) if methods else 0.0


def _calculate_cpp_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for C++ code."""
    import re
    
    # Find function declarations
    function_pattern = r'(?:int|void|float|double|char|bool|\w+)\s+(\w+)\s*\([^)]*\)\s*\{'
    functions = set(re.findall(function_pattern, code))
    
    # Remove common keywords that might be matched
    functions.discard('if')
    functions.discard('for')
    functions.discard('while')
    
    if not functions:
        return 0.0
    
    # Check test coverage
    tested_functions = set()
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        
        for func in functions:
            if func in test_content:
                tested_functions.add(func)
    
    return len(tested_functions) / len(functions) if functions else 0.0


def _calculate_go_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for Go code."""
    import re
    
    # Find function declarations
    function_pattern = r'func\s+(\w+)\s*\([^)]*\)'
    functions = set(re.findall(function_pattern, code))
    
    if not functions:
        return 0.0
    
    # Check test coverage
    tested_functions = set()
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        
        for func in functions:
            if func in test_content:
                tested_functions.add(func)
    
    return len(tested_functions) / len(functions) if functions else 0.0


def _calculate_rust_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate test coverage for Rust code."""
    import re
    
    # Find function declarations
    function_pattern = r'fn\s+(\w+)\s*\([^)]*\)'
    functions = set(re.findall(function_pattern, code))
    
    if not functions:
        return 0.0
    
    # Check test coverage
    tested_functions = set()
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        
        for func in functions:
            if func in test_content:
                tested_functions.add(func)
    
    return len(tested_functions) / len(functions) if functions else 0.0


def _calculate_generic_coverage(code: str, tests: List[Dict]) -> float:
    """Calculate generic test coverage for unknown languages."""
    # Very basic heuristic: count lines of code vs lines of tests
    code_lines = len([line for line in code.split('\n') if line.strip() and not line.strip().startswith('#')])
    
    total_test_lines = 0
    for test in tests:
        test_content = test.get('content', '') if isinstance(test, dict) else str(test)
        test_lines = len([line for line in test_content.split('\n') if line.strip()])
        total_test_lines += test_lines
    
    if code_lines == 0:
        return 0.0
    
    # Simple ratio with cap at 1.0
    return min(1.0, total_test_lines / code_lines)


def runtime_correctness(execution_results: List['ExecutionResult']) -> float:
    """Measure runtime correctness based on execution results.
    
    Evaluates whether code executes successfully without errors,
    crashes, or security violations.
    
    Args:
        execution_results: List of ExecutionResult objects from sandbox execution
        
    Returns:
        float: Runtime correctness score (0.0 to 1.0)
    """
    if not execution_results:
        return 0.0
    
    correct_executions = 0
    
    for result in execution_results:
        # Check multiple criteria for correctness
        is_correct = (
            result.success and                    # Overall success flag
            result.exit_code == 0 and            # Clean exit
            not result.security_violations and   # No security issues
            not result.error_message and         # No error messages
            result.wall_time > 0                 # Actually executed
        )
        
        # Additional checks for runtime issues
        if is_correct and result.stderr:
            # Check for runtime warnings/errors in stderr
            error_indicators = [
                'error', 'exception', 'traceback', 'segmentation fault',
                'bus error', 'abort', 'killed', 'timeout'
            ]
            
            stderr_lower = result.stderr.lower()
            if any(indicator in stderr_lower for indicator in error_indicators):
                is_correct = False
        
        if is_correct:
            correct_executions += 1
    
    return correct_executions / len(execution_results)


def memory_efficiency(execution_results: List['ExecutionResult'], 
                     memory_limit_mb: int = 512) -> float:
    """Measure memory efficiency of code execution.
    
    Evaluates how efficiently the code uses memory relative to limits
    and expected usage patterns.
    
    Args:
        execution_results: List of ExecutionResult objects from sandbox execution
        memory_limit_mb: Memory limit in MB for normalization
        
    Returns:
        float: Memory efficiency score (0.0 to 1.0, higher is better)
    """
    if not execution_results:
        return 0.0
    
    efficiency_scores = []
    
    for result in execution_results:
        if not result.success or result.peak_memory <= 0:
            efficiency_scores.append(0.0)
            continue
        
        # Calculate efficiency based on memory usage
        memory_usage_ratio = result.peak_memory / memory_limit_mb
        
        # Efficiency score: lower memory usage = higher efficiency
        # Use exponential decay to reward low memory usage
        if memory_usage_ratio <= 0.1:  # Very efficient (< 10% of limit)
            efficiency = 1.0
        elif memory_usage_ratio <= 0.25:  # Good efficiency (< 25% of limit)
            efficiency = 0.9
        elif memory_usage_ratio <= 0.5:   # Moderate efficiency (< 50% of limit)
            efficiency = 0.7
        elif memory_usage_ratio <= 0.75:  # Poor efficiency (< 75% of limit)
            efficiency = 0.4
        elif memory_usage_ratio <= 1.0:   # Very poor efficiency (< 100% of limit)
            efficiency = 0.2
        else:  # Exceeded limit
            efficiency = 0.0
        
        # Bonus for very low memory usage
        if memory_usage_ratio <= 0.05:
            efficiency = min(1.0, efficiency + 0.1)
        
        efficiency_scores.append(efficiency)
    
    return sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.0


def calculate_functional_metrics(predictions: List[str], tests: List[Dict],
                               execution_results: Optional[List['ExecutionResult']] = None,
                               language: str = "python", k: int = 1) -> Dict[str, float]:
    """Calculate all functional correctness metrics in one call.
    
    Convenience function to compute all functional correctness metrics
    for a set of predictions and tests.
    
    Args:
        predictions: List of code predictions
        tests: List of test definitions
        execution_results: Optional execution results from sandbox
        language: Programming language
        k: K value for Pass@K calculation
        
    Returns:
        Dictionary with all functional correctness metric scores
    """
    metrics = {}
    
    try:
        # Pass@K metric
        metrics['pass_at_k'] = pass_at_k(predictions, tests, k, language)
        
        # Test coverage metric
        metrics['test_coverage'] = test_coverage(predictions, tests, language)
        
        # Runtime correctness and memory efficiency (if execution results available)
        if execution_results:
            metrics['runtime_correctness'] = runtime_correctness(execution_results)
            metrics['memory_efficiency'] = memory_efficiency(execution_results)
        else:
            metrics['runtime_correctness'] = 0.0
            metrics['memory_efficiency'] = 0.0
            
    except Exception as e:
        eval_logger.error(f"Functional metrics calculation failed: {e}")
        # Return default values on error
        metrics = {
            'pass_at_k': 0.0,
            'test_coverage': 0.0,
            'runtime_correctness': 0.0,
            'memory_efficiency': 0.0
        }
    
    return metrics


# Consistency Metrics for Complex Scenarios
def phase_coherence(predictions: List[str]) -> float:
    """Measure phase coherence for multi-phase outputs.
    
    This metric evaluates how well different phases of a complex output
    (e.g., analysis → design → implementation) maintain consistency
    and logical flow between phases.
    
    Args:
        predictions: List of prediction strings containing multi-phase outputs
        
    Returns:
        float: Phase coherence score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    coherence_scores = []
    
    for prediction in predictions:
        try:
            score = _calculate_phase_coherence(prediction)
            coherence_scores.append(score)
        except Exception as e:
            eval_logger.debug(f"Phase coherence calculation error: {e}")
            coherence_scores.append(0.0)
    
    return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0


def _calculate_phase_coherence(prediction: str) -> float:
    """Calculate phase coherence for a single prediction."""
    # Identify common phase markers in technical outputs
    phase_markers = [
        # Analysis phase markers
        (r'\b(analysis|analyze|problem|requirement|issue|challenge)\b', 'analysis'),
        (r'\b(understand|identify|examine|investigate|assess)\b', 'analysis'),
        
        # Design phase markers  
        (r'\b(design|architecture|structure|approach|solution|strategy)\b', 'design'),
        (r'\b(plan|blueprint|framework|model|pattern)\b', 'design'),
        
        # Implementation phase markers
        (r'\b(implement|code|develop|build|create|construct)\b', 'implementation'),
        (r'\b(function|class|method|algorithm|procedure)\b', 'implementation'),
        
        # Testing/Validation phase markers
        (r'\b(test|validate|verify|check|ensure|confirm)\b', 'testing'),
        (r'\b(unit test|integration|validation|assertion)\b', 'testing'),
    ]
    
    # Split prediction into sentences/sections
    sections = _split_into_sections(prediction)
    if len(sections) < 2:
        return 0.5  # Single section gets neutral score
    
    # Identify phases in each section
    section_phases = []
    for section in sections:
        section_phase_counts = {'analysis': 0, 'design': 0, 'implementation': 0, 'testing': 0}
        
        for pattern, phase in phase_markers:
            matches = len(re.findall(pattern, section, re.IGNORECASE))
            section_phase_counts[phase] += matches
        
        # Determine dominant phase for this section
        if sum(section_phase_counts.values()) > 0:
            dominant_phase = max(section_phase_counts, key=section_phase_counts.get)
            section_phases.append(dominant_phase)
        else:
            section_phases.append('unknown')
    
    # Calculate coherence based on logical phase progression
    coherence_score = _evaluate_phase_progression(section_phases)
    
    # Check for cross-references and consistency between phases
    consistency_bonus = _check_phase_consistency(prediction, sections)
    
    # Combine scores
    final_score = min(1.0, coherence_score + consistency_bonus)
    
    return final_score


def _split_into_sections(text: str) -> List[str]:
    """Split text into logical sections for phase analysis."""
    # Split by common section delimiters
    delimiters = [
        r'\n\s*#{1,6}\s+',  # Markdown headers
        r'\n\s*\d+\.\s+',   # Numbered lists
        r'\n\s*[A-Z][^.]*:\s*\n',  # Section headers ending with colon
        r'\n\s*\*\*[^*]+\*\*\s*\n',  # Bold headers
        r'\n\s*---+\s*\n',  # Horizontal rules
        r'\n\s*```[^`]*```\s*\n',  # Code blocks as separate sections
    ]
    
    sections = [text]
    
    for delimiter in delimiters:
        new_sections = []
        for section in sections:
            parts = re.split(delimiter, section)
            new_sections.extend([part.strip() for part in parts if part.strip()])
        sections = new_sections
    
    # If no clear sections found, split by paragraphs
    if len(sections) <= 1:
        sections = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    return sections


def _evaluate_phase_progression(phases: List[str]) -> float:
    """Evaluate the logical progression of phases."""
    if not phases:
        return 0.0
    
    # Define ideal phase progression patterns
    ideal_progressions = [
        ['analysis', 'design', 'implementation', 'testing'],
        ['analysis', 'design', 'implementation'],
        ['design', 'implementation', 'testing'],
        ['analysis', 'implementation'],
        ['design', 'implementation'],
    ]
    
    # Calculate best match with ideal progressions
    best_score = 0.0
    
    for ideal in ideal_progressions:
        score = _calculate_progression_similarity(phases, ideal)
        best_score = max(best_score, score)
    
    return best_score


def _calculate_progression_similarity(actual: List[str], ideal: List[str]) -> float:
    """Calculate similarity between actual and ideal phase progression."""
    if not actual or not ideal:
        return 0.0
    
    # Use longest common subsequence to measure similarity
    def lcs_length(seq1, seq2):
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    lcs_len = lcs_length(actual, ideal)
    
    # Normalize by the length of the ideal sequence
    similarity = lcs_len / len(ideal) if ideal else 0.0
    
    # Bonus for maintaining order
    order_bonus = 0.0
    if lcs_len > 1:
        # Check if the matched phases appear in the correct order
        matched_indices = []
        ideal_idx = 0
        for phase in actual:
            if ideal_idx < len(ideal) and phase == ideal[ideal_idx]:
                matched_indices.append(ideal_idx)
                ideal_idx += 1
        
        if len(matched_indices) > 1:
            # Check if indices are in ascending order
            is_ordered = all(matched_indices[i] < matched_indices[i+1] 
                           for i in range(len(matched_indices)-1))
            if is_ordered:
                order_bonus = 0.2
    
    return min(1.0, similarity + order_bonus)


def _check_phase_consistency(text: str, sections: List[str]) -> float:
    """Check for consistency and cross-references between phases."""
    consistency_score = 0.0
    
    # Look for cross-references between sections
    reference_patterns = [
        r'\b(as mentioned|as discussed|as outlined|as described|as shown)\b',
        r'\b(above|below|previous|following|earlier|later)\b',
        r'\b(this approach|this design|this implementation|this solution)\b',
        r'\b(based on|according to|following|using)\b',
    ]
    
    cross_references = 0
    for pattern in reference_patterns:
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        cross_references += matches
    
    # Normalize cross-reference score
    if cross_references > 0:
        consistency_score += min(0.2, cross_references * 0.05)
    
    # Check for consistent terminology usage
    terminology_consistency = _check_terminology_consistency(sections)
    consistency_score += terminology_consistency
    
    return min(0.3, consistency_score)  # Cap bonus at 0.3


def _check_terminology_consistency(sections: List[str]) -> float:
    """Check for consistent use of technical terminology across sections."""
    if len(sections) < 2:
        return 0.0
    
    # Extract technical terms from each section
    technical_patterns = [
        r'\b[A-Z][a-z]*[A-Z][a-zA-Z]*\b',  # CamelCase terms
        r'\b[a-z]+_[a-z_]+\b',             # snake_case terms
        r'\b[A-Z]{2,}\b',                  # ACRONYMS
        r'\b\w+\(\)\b',                    # function() calls
    ]
    
    section_terms = []
    for section in sections:
        terms = set()
        for pattern in technical_patterns:
            matches = re.findall(pattern, section)
            terms.update(matches)
        section_terms.append(terms)
    
    if not any(section_terms):
        return 0.0
    
    # Calculate term overlap between sections
    total_overlap = 0
    comparisons = 0
    
    for i in range(len(section_terms)):
        for j in range(i + 1, len(section_terms)):
            if section_terms[i] and section_terms[j]:
                overlap = len(section_terms[i] & section_terms[j])
                union = len(section_terms[i] | section_terms[j])
                if union > 0:
                    total_overlap += overlap / union
                    comparisons += 1
    
    if comparisons == 0:
        return 0.0
    
    avg_overlap = total_overlap / comparisons
    return min(0.1, avg_overlap * 0.2)  # Small bonus for terminology consistency


def design_implementation_alignment(predictions: List[str]) -> float:
    """Score alignment between design and implementation phases.
    
    This metric evaluates how well the implementation follows
    the design specifications and architectural decisions.
    
    Args:
        predictions: List of prediction strings containing design and implementation
        
    Returns:
        float: Design-implementation alignment score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    alignment_scores = []
    
    for prediction in predictions:
        try:
            score = _calculate_design_implementation_alignment(prediction)
            alignment_scores.append(score)
        except Exception as e:
            eval_logger.debug(f"Design-implementation alignment calculation error: {e}")
            alignment_scores.append(0.0)
    
    return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.0


def _calculate_design_implementation_alignment(prediction: str) -> float:
    """Calculate design-implementation alignment for a single prediction."""
    # Split prediction into design and implementation sections
    design_section, impl_section = _extract_design_and_implementation(prediction)
    
    if not design_section or not impl_section:
        return 0.5  # Neutral score if can't identify both sections
    
    # Extract design elements
    design_elements = _extract_design_elements(design_section)
    
    # Extract implementation elements  
    impl_elements = _extract_implementation_elements(impl_section)
    
    # Calculate alignment scores
    structural_alignment = _calculate_structural_alignment(design_elements, impl_elements)
    naming_alignment = _calculate_naming_alignment(design_elements, impl_elements)
    pattern_alignment = _calculate_pattern_alignment(design_elements, impl_elements)
    
    # Weighted combination of alignment scores
    total_score = (
        structural_alignment * 0.4 +
        naming_alignment * 0.3 +
        pattern_alignment * 0.3
    )
    
    return min(1.0, total_score)


def _extract_design_and_implementation(text: str) -> tuple:
    """Extract design and implementation sections from text."""
    # Look for explicit section headers first
    design_section_pattern = r'##?\s*(design|architecture|approach|solution|plan)\s*\n(.*?)(?=##|\Z)'
    impl_section_pattern = r'##?\s*(implementation|code|develop|build)\s*\n(.*?)(?=##|\Z)'
    
    design_match = re.search(design_section_pattern, text, re.IGNORECASE | re.DOTALL)
    impl_match = re.search(impl_section_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if design_match and impl_match:
        return design_match.group(2).strip(), impl_match.group(2).strip()
    
    # Fallback to marker-based detection
    design_markers = [
        r'design|architecture|structure|approach|solution|strategy',
        r'plan|blueprint|framework|model|pattern|schema',
        r'class diagram|component|interface|api'
    ]
    
    impl_markers = [
        r'implementation|code|develop|build|create',
        r'function|class|method|algorithm|procedure',
        r'```|def |class |import |from '
    ]
    
    sections = _split_into_sections(text)
    
    design_sections = []
    impl_sections = []
    
    for section in sections:
        # Check if section contains code blocks - likely implementation
        if re.search(r'```[\s\S]*?```', section):
            impl_sections.append(section)
            continue
            
        design_score = sum(len(re.findall(pattern, section, re.IGNORECASE)) 
                          for pattern in design_markers)
        impl_score = sum(len(re.findall(pattern, section, re.IGNORECASE)) 
                        for pattern in impl_markers)
        
        if design_score > impl_score and design_score > 0:
            design_sections.append(section)
        elif impl_score > 0:
            impl_sections.append(section)
    
    design_text = '\n'.join(design_sections)
    impl_text = '\n'.join(impl_sections)
    
    return design_text, impl_text


def _extract_design_elements(design_text: str) -> Dict[str, List[str]]:
    """Extract design elements from design section."""
    elements = {
        'classes': [],
        'functions': [],
        'interfaces': [],
        'patterns': [],
        'components': []
    }
    
    # Extract class names
    class_patterns = [
        r'\bclass\s+(\w+)',
        r'\b(\w+)\s+class',
        r'\b(\w+Class)\b',
        r'\b([A-Z]\w*)\s+(?:component|service|manager|handler)'
    ]
    
    for pattern in class_patterns:
        matches = re.findall(pattern, design_text, re.IGNORECASE)
        elements['classes'].extend(matches)
    
    # Extract function/method names
    function_patterns = [
        r'\bfunction\s+(\w+)',
        r'\bmethod\s+(\w+)',
        r'\b(\w+)\s*\(\)',
        r'\b(\w+)\s+function'
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, design_text, re.IGNORECASE)
        elements['functions'].extend(matches)
    
    # Extract interface names
    interface_patterns = [
        r'\binterface\s+(\w+)',
        r'\b(\w+)\s+interface',
        r'\bAPI\s+(\w+)',
        r'\b(\w+)API\b'
    ]
    
    for pattern in interface_patterns:
        matches = re.findall(pattern, design_text, re.IGNORECASE)
        elements['interfaces'].extend(matches)
    
    # Extract design patterns
    pattern_names = [
        'singleton', 'factory', 'observer', 'strategy', 'decorator',
        'adapter', 'facade', 'proxy', 'builder', 'prototype',
        'mvc', 'mvp', 'mvvm', 'repository', 'service'
    ]
    
    for pattern_name in pattern_names:
        if re.search(rf'\b{pattern_name}\b', design_text, re.IGNORECASE):
            elements['patterns'].append(pattern_name)
    
    # Extract component names
    component_patterns = [
        r'\bcomponent\s+(\w+)',
        r'\b(\w+)\s+component',
        r'\bmodule\s+(\w+)',
        r'\b(\w+)\s+module'
    ]
    
    for pattern in component_patterns:
        matches = re.findall(pattern, design_text, re.IGNORECASE)
        elements['components'].extend(matches)
    
    return elements


def _extract_implementation_elements(impl_text: str) -> Dict[str, List[str]]:
    """Extract implementation elements from implementation section."""
    elements = {
        'classes': [],
        'functions': [],
        'interfaces': [],
        'patterns': [],
        'components': []
    }
    
    # Extract actual class definitions
    class_matches = re.findall(r'\bclass\s+(\w+)', impl_text, re.IGNORECASE)
    elements['classes'].extend(class_matches)
    
    # Extract function definitions - be more comprehensive
    function_matches = re.findall(r'\bdef\s+(\w+)', impl_text)
    function_matches.extend(re.findall(r'\bfunction\s+(\w+)', impl_text, re.IGNORECASE))
    # Also look for method calls that might indicate functions mentioned in design
    method_calls = re.findall(r'\.(\w+)\s*\(', impl_text)
    elements['functions'].extend(function_matches)
    elements['functions'].extend(method_calls)
    
    # Extract interface implementations (language-specific)
    interface_matches = re.findall(r'\binterface\s+(\w+)', impl_text, re.IGNORECASE)
    interface_matches.extend(re.findall(r'\bimplements\s+(\w+)', impl_text, re.IGNORECASE))
    elements['interfaces'].extend(interface_matches)
    
    # Look for pattern implementations in code structure
    if re.search(r'__new__.*__init__', impl_text, re.DOTALL):
        elements['patterns'].append('singleton')
    if re.search(r'create.*factory', impl_text, re.IGNORECASE):
        elements['patterns'].append('factory')
    if re.search(r'notify.*observer', impl_text, re.IGNORECASE):
        elements['patterns'].append('observer')
    
    return elements


def _calculate_structural_alignment(design_elements: Dict, impl_elements: Dict) -> float:
    """Calculate structural alignment between design and implementation."""
    alignment_score = 0.0
    total_categories = 0
    
    for category in ['classes', 'functions', 'interfaces', 'components']:
        if design_elements[category] or impl_elements[category]:
            total_categories += 1
            
            design_set = set(name.lower() for name in design_elements[category])
            impl_set = set(name.lower() for name in impl_elements[category])
            
            if design_set and impl_set:
                # Calculate fuzzy matching for better alignment detection
                matches = 0
                for design_name in design_set:
                    best_match = 0.0
                    for impl_name in impl_set:
                        similarity = _calculate_string_similarity(design_name, impl_name)
                        best_match = max(best_match, similarity)
                    if best_match > 0.6:  # Threshold for considering a match
                        matches += 1
                
                # Calculate alignment based on matches
                alignment = matches / len(design_set) if design_set else 0.0
                alignment_score += alignment
            elif not design_set and not impl_set:
                alignment_score += 1.0  # Both empty is perfect alignment
            elif design_set and not impl_set:
                alignment_score += 0.0  # Design specified but not implemented
            else:
                alignment_score += 0.3  # Implementation without design gets partial credit
    
    return alignment_score / total_categories if total_categories > 0 else 0.5


def _calculate_naming_alignment(design_elements: Dict, impl_elements: Dict) -> float:
    """Calculate naming consistency between design and implementation."""
    all_design_names = []
    all_impl_names = []
    
    for category in ['classes', 'functions', 'interfaces', 'components']:
        all_design_names.extend(design_elements[category])
        all_impl_names.extend(impl_elements[category])
    
    if not all_design_names or not all_impl_names:
        return 0.5  # Neutral score if no names to compare
    
    # Calculate fuzzy string matching for names
    matches = 0
    total_comparisons = 0
    
    for design_name in all_design_names:
        best_match_score = 0.0
        for impl_name in all_impl_names:
            similarity = _calculate_string_similarity(design_name.lower(), impl_name.lower())
            best_match_score = max(best_match_score, similarity)
        
        if best_match_score > 0.7:  # Threshold for considering a match
            matches += 1
        total_comparisons += 1
    
    return matches / total_comparisons if total_comparisons > 0 else 0.0


def _calculate_pattern_alignment(design_elements: Dict, impl_elements: Dict) -> float:
    """Calculate design pattern alignment between design and implementation."""
    design_patterns = set(design_elements['patterns'])
    impl_patterns = set(impl_elements['patterns'])
    
    if not design_patterns and not impl_patterns:
        return 1.0  # No patterns mentioned is perfect alignment
    
    if not design_patterns or not impl_patterns:
        return 0.0  # One has patterns, other doesn't
    
    # Calculate pattern overlap
    intersection = len(design_patterns & impl_patterns)
    union = len(design_patterns | impl_patterns)
    
    return intersection / union if union > 0 else 0.0


def _calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings using edit distance."""
    if str1 == str2:
        return 1.0
    
    if not str1 or not str2:
        return 0.0
    
    # Calculate edit distance
    m, n = len(str1), len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    edit_distance = dp[m][n]
    max_len = max(len(str1), len(str2))
    
    return 1.0 - (edit_distance / max_len) if max_len > 0 else 0.0


def information_flow(predictions: List[str]) -> float:
    """Evaluate information flow consistency in complex outputs.
    
    This metric assesses how well information flows logically
    through different sections and maintains consistency in
    data usage, variable references, and conceptual connections.
    
    Args:
        predictions: List of prediction strings to evaluate
        
    Returns:
        float: Information flow consistency score (0.0 to 1.0, higher is better)
    """
    if not predictions:
        return 0.0
    
    flow_scores = []
    
    for prediction in predictions:
        try:
            score = _calculate_information_flow(prediction)
            flow_scores.append(score)
        except Exception as e:
            eval_logger.debug(f"Information flow calculation error: {e}")
            flow_scores.append(0.0)
    
    return sum(flow_scores) / len(flow_scores) if flow_scores else 0.0


def _calculate_information_flow(prediction: str) -> float:
    """Calculate information flow consistency for a single prediction."""
    sections = _split_into_sections(prediction)
    
    if len(sections) < 2:
        return 0.5  # Single section gets neutral score
    
    # Extract information entities from each section
    section_entities = []
    for section in sections:
        entities = _extract_information_entities(section)
        section_entities.append(entities)
    
    # Calculate flow consistency metrics
    reference_consistency = _calculate_reference_consistency(section_entities)
    data_flow_consistency = _calculate_data_flow_consistency(section_entities)
    conceptual_consistency = _calculate_conceptual_consistency(sections)
    
    # Weighted combination
    total_score = (
        reference_consistency * 0.4 +
        data_flow_consistency * 0.3 +
        conceptual_consistency * 0.3
    )
    
    return min(1.0, total_score)


def _extract_information_entities(text: str) -> Dict[str, List[str]]:
    """Extract information entities from text section."""
    entities = {
        'variables': [],
        'functions': [],
        'classes': [],
        'concepts': [],
        'data_structures': []
    }
    
    # Extract variable names
    variable_patterns = [
        r'\b([a-z_][a-z0-9_]*)\s*=',  # Assignment patterns
        r'\b([a-z_][a-z0-9_]*)\s*\[',  # Array/dict access
        r'\blet\s+([a-z_][a-z0-9_]*)',  # Let declarations
        r'\bvar\s+([a-z_][a-z0-9_]*)',  # Var declarations
        r'([a-z_][a-z0-9_]*)\s*\["',   # Dictionary access with quotes
        r'([a-z_][a-z0-9_]*)\s*\[\'',  # Dictionary access with single quotes
    ]
    
    for pattern in variable_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities['variables'].extend(matches)
    
    # Extract function references
    function_patterns = [
        r'\b([a-z_][a-z0-9_]*)\s*\(',  # Function calls
        r'\bdef\s+([a-z_][a-z0-9_]*)',  # Function definitions
        r'\bfunction\s+([a-z_][a-z0-9_]*)',  # JS function definitions
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities['functions'].extend(matches)
    
    # Extract class references
    class_patterns = [
        r'\bclass\s+([A-Z][a-zA-Z0-9_]*)',  # Class definitions
        r'\bnew\s+([A-Z][a-zA-Z0-9_]*)',    # Object instantiation
        r'\b([A-Z][a-zA-Z0-9_]*)\s*\(',     # Constructor calls
    ]
    
    for pattern in class_patterns:
        matches = re.findall(pattern, text)
        entities['classes'].extend(matches)
    
    # Extract conceptual terms (capitalized words that aren't code)
    concept_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    concept_matches = re.findall(concept_pattern, text)
    # Filter out common non-conceptual words
    stop_words = {'The', 'This', 'That', 'These', 'Those', 'When', 'Where', 'What', 'How', 'Why'}
    concepts = [match for match in concept_matches if match not in stop_words]
    entities['concepts'].extend(concepts)
    
    # Extract data structure references
    data_structure_patterns = [
        r'\b(list|array|dict|map|set|queue|stack|tree|graph)\b',
        r'\b([a-z_][a-z0-9_]*(?:_(?:list|array|dict|map|set|queue|stack|tree|graph)))\b',
    ]
    
    for pattern in data_structure_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities['data_structures'].extend(matches)
    
    return entities


def _calculate_reference_consistency(section_entities: List[Dict]) -> float:
    """Calculate consistency of entity references across sections."""
    if len(section_entities) < 2:
        return 1.0
    
    # Track entity usage across sections
    entity_usage = {}
    
    for section_idx, entities in enumerate(section_entities):
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity_key = (entity_type, entity.lower())
                if entity_key not in entity_usage:
                    entity_usage[entity_key] = []
                entity_usage[entity_key].append(section_idx)
    
    if not entity_usage:
        return 0.5  # No entities found
    
    # Calculate consistency score
    consistent_entities = 0
    total_entities = 0
    
    for entity_key, usage_sections in entity_usage.items():
        total_entities += 1
        
        # Entity is consistent if it appears in multiple sections
        if len(usage_sections) > 1:
            # Multi-section usage gets high score
            usage_sections.sort()
            if len(usage_sections) >= 2:
                # Check if usage follows logical progression
                max_gap = max(usage_sections[i+1] - usage_sections[i] 
                             for i in range(len(usage_sections)-1)) if len(usage_sections) > 1 else 0
                
                if max_gap <= 1:  # Consecutive sections
                    consistent_entities += 1.0
                elif max_gap <= 2:  # Small gaps
                    consistent_entities += 0.8
                else:
                    consistent_entities += 0.6  # Scattered but still multi-section
        else:
            # Single usage gets lower score
            consistent_entities += 0.2
    
    return consistent_entities / total_entities if total_entities > 0 else 0.5


def _calculate_data_flow_consistency(section_entities: List[Dict]) -> float:
    """Calculate data flow consistency across sections."""
    if len(section_entities) < 2:
        return 1.0
    
    # Look for data flow patterns: definition → usage → transformation
    flow_score = 0.0
    flow_patterns = 0
    
    # Check variable flow patterns
    all_variables = set()
    for entities in section_entities:
        all_variables.update(var.lower() for var in entities['variables'])
    
    for variable in all_variables:
        # Track where this variable appears
        appearances = []
        for section_idx, entities in enumerate(section_entities):
            if variable in [v.lower() for v in entities['variables']]:
                appearances.append(section_idx)
        
        if len(appearances) > 1:
            flow_patterns += 1
            # Check if appearances follow logical order
            if appearances == sorted(appearances):
                flow_score += 1.0  # Perfect sequential flow
            else:
                flow_score += 0.5  # Some flow but not perfect
    
    # Check function call flow
    all_functions = set()
    for entities in section_entities:
        all_functions.update(func.lower() for func in entities['functions'])
    
    for function in all_functions:
        appearances = []
        for section_idx, entities in enumerate(section_entities):
            if function in [f.lower() for f in entities['functions']]:
                appearances.append(section_idx)
        
        if len(appearances) > 1:
            flow_patterns += 1
            if appearances == sorted(appearances):
                flow_score += 1.0
            else:
                flow_score += 0.5
    
    return flow_score / flow_patterns if flow_patterns > 0 else 1.0


def _calculate_conceptual_consistency(sections: List[str]) -> float:
    """Calculate conceptual consistency across sections."""
    if len(sections) < 2:
        return 1.0
    
    # Extract key concepts from each section
    section_concepts = []
    for section in sections:
        concepts = _extract_key_concepts(section)
        section_concepts.append(concepts)
    
    # Calculate concept overlap between adjacent sections
    overlap_scores = []
    
    for i in range(len(section_concepts) - 1):
        current_concepts = section_concepts[i]
        next_concepts = section_concepts[i + 1]
        
        if current_concepts and next_concepts:
            intersection = len(current_concepts & next_concepts)
            union = len(current_concepts | next_concepts)
            overlap = intersection / union if union > 0 else 0.0
            overlap_scores.append(overlap)
        else:
            overlap_scores.append(0.0)
    
    # Also check for concept evolution (new concepts building on old ones)
    evolution_score = _calculate_concept_evolution(section_concepts)
    
    avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0
    
    # Combine overlap and evolution scores
    return (avg_overlap * 0.7 + evolution_score * 0.3)


def _extract_key_concepts(text: str) -> set:
    """Extract key conceptual terms from text."""
    # Remove code blocks to focus on conceptual content
    text_without_code = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text_without_code = re.sub(r'`[^`]*`', '', text_without_code)
    
    # Extract meaningful terms (nouns, technical terms)
    concept_patterns = [
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Capitalized phrases
        r'\b([a-z]+(?:_[a-z]+)+)\b',              # snake_case terms
        r'\b([a-z]+(?:[A-Z][a-z]*)+)\b',          # camelCase terms
        r'\b(\w+(?:ing|tion|ness|ment|ity|ism))\b',  # Abstract nouns
    ]
    
    concepts = set()
    for pattern in concept_patterns:
        matches = re.findall(pattern, text_without_code)
        concepts.update(match.lower() for match in matches)
    
    # Filter out common stop words and very short terms
    stop_words = {
        'the', 'this', 'that', 'these', 'those', 'when', 'where', 'what', 'how', 'why',
        'and', 'but', 'for', 'not', 'are', 'was', 'will', 'can', 'may', 'should',
        'have', 'has', 'had', 'been', 'being', 'get', 'got', 'make', 'made', 'take',
        'code', 'function', 'method', 'class', 'object', 'string', 'number', 'value'
    }
    
    filtered_concepts = {concept for concept in concepts 
                        if len(concept) > 2 and concept not in stop_words}
    
    return filtered_concepts


def _calculate_concept_evolution(section_concepts: List[set]) -> float:
    """Calculate how concepts evolve and build upon each other."""
    if len(section_concepts) < 2:
        return 1.0
    
    evolution_score = 0.0
    evolution_count = 0
    
    for i in range(len(section_concepts) - 1):
        current = section_concepts[i]
        next_section = section_concepts[i + 1]
        
        if current and next_section:
            # Check for concept building (new concepts that extend existing ones)
            building_concepts = 0
            for next_concept in next_section:
                for current_concept in current:
                    # Check if next concept builds on current concept
                    if (current_concept in next_concept or 
                        next_concept in current_concept or
                        _are_related_concepts(current_concept, next_concept)):
                        building_concepts += 1
                        break
            
            if next_section:
                building_ratio = building_concepts / len(next_section)
                evolution_score += building_ratio
                evolution_count += 1
    
    return evolution_score / evolution_count if evolution_count > 0 else 1.0


def _are_related_concepts(concept1: str, concept2: str) -> bool:
    """Check if two concepts are semantically related."""
    # Simple heuristic: concepts are related if they share significant substrings
    if len(concept1) < 3 or len(concept2) < 3:
        return False
    
    # Check for common roots or stems
    min_len = min(len(concept1), len(concept2))
    common_prefix_len = 0
    
    for i in range(min_len):
        if concept1[i] == concept2[i]:
            common_prefix_len += 1
        else:
            break
    
    # Consider related if they share at least 50% of the shorter word
    return common_prefix_len >= min_len * 0.5


def calculate_consistency_metrics(predictions: List[str]) -> Dict[str, float]:
    """Calculate all consistency metrics in one call.
    
    Convenience function to compute all consistency metrics
    for complex scenarios.
    
    Args:
        predictions: List of prediction strings to evaluate
        
    Returns:
        Dictionary with all consistency metric scores
    """
    metrics = {}
    
    try:
        # Phase coherence metric
        metrics['phase_coherence'] = phase_coherence(predictions)
        
        # Design-implementation alignment metric
        metrics['design_implementation_alignment'] = design_implementation_alignment(predictions)
        
        # Information flow consistency metric
        metrics['information_flow'] = information_flow(predictions)
        
    except Exception as e:
        eval_logger.error(f"Consistency metrics calculation failed: {e}")
        # Return default values on error
        metrics = {
            'phase_coherence': 0.0,
            'design_implementation_alignment': 0.0,
            'information_flow': 0.0
        }
    
    return metrics