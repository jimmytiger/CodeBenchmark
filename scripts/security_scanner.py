#!/usr/bin/env python3
"""
Comprehensive security scanner for AI Evaluation Engine.
"""

import os
import json
import subprocess
import sys
import re
import ast
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import logging
from datetime import datetime


@dataclass
class SecurityVulnerability:
    """Security vulnerability data structure."""
    id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    category: str
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    recommendation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None


@dataclass
class SecurityScanResult:
    """Security scan result data structure."""
    timestamp: str
    scan_type: str
    total_files_scanned: int
    vulnerabilities: List[SecurityVulnerability]
    summary: Dict[str, int]
    scan_duration: float


class SecurityScanner:
    """Comprehensive security scanner."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Security patterns to detect
        self.security_patterns = {
            'sql_injection': [
                r'\.execute\s*\(\s*["\'].*%.*["\']',
                r'\.execute\s*\(\s*f["\'].*\{.*\}.*["\']',
                r'cursor\.execute\s*\(\s*["\'].*\+.*["\']',
                r'query\s*=\s*["\'].*\+.*["\']',
                r'SELECT.*\+.*FROM',
                r'INSERT.*\+.*VALUES',
                r'UPDATE.*\+.*SET',
                r'DELETE.*\+.*WHERE'
            ],
            'command_injection': [
                r'os\.system\s*\(',
                r'subprocess\.call\s*\(',
                r'subprocess\.run\s*\(',
                r'subprocess\.Popen\s*\(',
                r'os\.popen\s*\(',
                r'commands\.getoutput\s*\(',
                r'eval\s*\(',
                r'exec\s*\(',
                r'__import__\s*\(',
                r'compile\s*\('
            ],
            'path_traversal': [
                r'open\s*\(\s*["\']\.\./',
                r'open\s*\(\s*.*\+.*["\']\.\./',
                r'os\.path\.join\s*\(.*\.\.',
                r'Path\s*\(.*\.\.',
                r'/etc/passwd',
                r'/etc/shadow',
                r'\.\.\\',
                r'\.\./\.\.'
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']{8,}["\']',
                r'api_key\s*=\s*["\'][^"\']{16,}["\']',
                r'secret\s*=\s*["\'][^"\']{16,}["\']',
                r'token\s*=\s*["\'][^"\']{16,}["\']',
                r'key\s*=\s*["\'][^"\']{16,}["\']',
                r'["\'][A-Za-z0-9]{32,}["\']',  # Long hex strings
                r'["\']sk-[A-Za-z0-9]{32,}["\']',  # OpenAI API keys
                r'["\']xoxb-[A-Za-z0-9-]{50,}["\']'  # Slack tokens
            ],
            'xss_vulnerabilities': [
                r'\.innerHTML\s*=',
                r'\.outerHTML\s*=',
                r'document\.write\s*\(',
                r'\.html\s*\(\s*.*\+',
                r'render_template_string\s*\(',
                r'Markup\s*\(',
                r'<script.*>.*</script>',
                r'javascript:',
                r'on\w+\s*='
            ],
            'insecure_random': [
                r'random\.random\s*\(',
                r'random\.randint\s*\(',
                r'random\.choice\s*\(',
                r'Math\.random\s*\(',
                r'rand\s*\(',
                r'srand\s*\('
            ],
            'weak_crypto': [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'DES\s*\(',
                r'RC4\s*\(',
                r'ECB\s*\(',
                r'hashlib\.md5',
                r'hashlib\.sha1',
                r'Crypto\.Cipher\.DES',
                r'Crypto\.Cipher\.ARC4'
            ],
            'unsafe_deserialization': [
                r'pickle\.loads\s*\(',
                r'pickle\.load\s*\(',
                r'cPickle\.loads\s*\(',
                r'yaml\.load\s*\(',
                r'json\.loads\s*\(.*user',
                r'marshal\.loads\s*\(',
                r'eval\s*\(.*input',
                r'exec\s*\(.*input'
            ]
        }
        
        # File extensions to scan
        self.scannable_extensions = {'.py', '.js', '.ts', '.java', '.php', '.rb', '.go', '.rs', '.cpp', '.c', '.h'}
        
        # Directories to skip
        self.skip_directories = {
            '__pycache__', '.git', '.svn', '.hg', 'node_modules', 
            '.pytest_cache', '.mypy_cache', 'venv', 'env', '.env',
            'build', 'dist', '.tox', 'htmlcov'
        }
    
    def scan_file(self, file_path: Path) -> List[SecurityVulnerability]:
        """Scan a single file for security vulnerabilities."""
        vulnerabilities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Scan for each vulnerability category
            for category, patterns in self.security_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        # Find line number
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_number = content[:match.start()].count('\n') + 1
                        line_end = content.find('\n', match.end())
                        if line_end == -1:
                            line_end = len(content)
                        
                        code_snippet = content[line_start:line_end].strip()
                        
                        vulnerability = SecurityVulnerability(
                            id=self._generate_vulnerability_id(file_path, line_number, category),
                            severity=self._get_severity(category),
                            category=category,
                            title=self._get_vulnerability_title(category),
                            description=self._get_vulnerability_description(category),
                            file_path=str(file_path),
                            line_number=line_number,
                            code_snippet=code_snippet,
                            recommendation=self._get_recommendation(category),
                            cwe_id=self._get_cwe_id(category)
                        )
                        
                        vulnerabilities.append(vulnerability)
        
        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")
        
        return vulnerabilities
    
    def scan_directory(self, directory: Path) -> SecurityScanResult:
        """Scan a directory recursively for security vulnerabilities."""
        start_time = datetime.now()
        vulnerabilities = []
        files_scanned = 0
        
        for file_path in directory.rglob('*'):
            # Skip directories and non-scannable files
            if file_path.is_dir():
                continue
            
            # Skip files in excluded directories
            if any(skip_dir in file_path.parts for skip_dir in self.skip_directories):
                continue
            
            # Only scan files with relevant extensions
            if file_path.suffix not in self.scannable_extensions:
                continue
            
            files_scanned += 1
            file_vulnerabilities = self.scan_file(file_path)
            vulnerabilities.extend(file_vulnerabilities)
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        # Generate summary
        summary = {}
        for vuln in vulnerabilities:
            summary[vuln.severity] = summary.get(vuln.severity, 0) + 1
            summary[vuln.category] = summary.get(vuln.category, 0) + 1
        
        return SecurityScanResult(
            timestamp=start_time.isoformat(),
            scan_type='static_analysis',
            total_files_scanned=files_scanned,
            vulnerabilities=vulnerabilities,
            summary=summary,
            scan_duration=scan_duration
        )
    
    def run_bandit_scan(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Run Bandit security scanner."""
        try:
            result = subprocess.run([
                'bandit', '-r', str(directory), '-f', 'json',
                '--skip', 'B101,B601',  # Skip assert and shell usage in tests
                '--exclude', ','.join([
                    '*/tests/*', '*/test_*', '*/__pycache__/*', 
                    '*/venv/*', '*/env/*', '*/.git/*'
                ])
            ], capture_output=True, text=True, check=False)
            
            if result.stdout:
                return json.loads(result.stdout)
            
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Error running Bandit: {e}")
        
        return None
    
    def run_safety_scan(self) -> Optional[List[Dict[str, Any]]]:
        """Run Safety dependency scanner."""
        try:
            result = subprocess.run([
                'safety', 'check', '--json'
            ], capture_output=True, text=True, check=False)
            
            if result.stdout:
                return json.loads(result.stdout)
            
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Error running Safety: {e}")
        
        return None
    
    def run_semgrep_scan(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Run Semgrep security scanner."""
        try:
            result = subprocess.run([
                'semgrep', '--config=auto', str(directory), '--json',
                '--exclude', 'tests/', '--exclude', '__pycache__/',
                '--exclude', 'venv/', '--exclude', '.git/'
            ], capture_output=True, text=True, check=False)
            
            if result.stdout:
                return json.loads(result.stdout)
            
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Error running Semgrep: {e}")
        
        return None
    
    def scan_dependencies(self, requirements_file: Path = None) -> Dict[str, Any]:
        """Scan dependencies for known vulnerabilities."""
        vulnerabilities = []
        
        # Find requirements files if not specified
        if requirements_file is None:
            req_files = ['requirements.txt', 'requirements-dev.txt', 'pyproject.toml', 'Pipfile']
            for req_file in req_files:
                if Path(req_file).exists():
                    requirements_file = Path(req_file)
                    break
        
        if requirements_file and requirements_file.exists():
            # Run safety check
            safety_results = self.run_safety_scan()
            if safety_results:
                for vuln in safety_results:
                    vulnerabilities.append({
                        'type': 'dependency_vulnerability',
                        'package': vuln.get('package', 'unknown'),
                        'version': vuln.get('installed_version', 'unknown'),
                        'vulnerability_id': vuln.get('vulnerability_id', ''),
                        'advisory': vuln.get('advisory', ''),
                        'severity': self._map_safety_severity(vuln.get('severity', 'unknown'))
                    })
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'vulnerabilities': vulnerabilities,
            'scan_timestamp': datetime.now().isoformat()
        }
    
    def generate_security_report(self, scan_results: List[SecurityScanResult], 
                                output_file: str = 'security_report.html'):
        """Generate comprehensive security report."""
        total_vulnerabilities = sum(len(result.vulnerabilities) for result in scan_results)
        
        # Aggregate vulnerabilities by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        category_counts = {}
        
        all_vulnerabilities = []
        for result in scan_results:
            all_vulnerabilities.extend(result.vulnerabilities)
        
        for vuln in all_vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
            category_counts[vuln.category] = category_counts.get(vuln.category, 0) + 1
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Scan Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card.critical {{ border-left: 4px solid #dc3545; }}
        .summary-card.high {{ border-left: 4px solid #fd7e14; }}
        .summary-card.medium {{ border-left: 4px solid #ffc107; }}
        .summary-card.low {{ border-left: 4px solid #28a745; }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .critical .value {{ color: #dc3545; }}
        .high .value {{ color: #fd7e14; }}
        .medium .value {{ color: #ffc107; }}
        .low .value {{ color: #28a745; }}
        .vulnerability {{
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .vulnerability-header {{
            padding: 15px;
            cursor: pointer;
        }}
        .vulnerability-header:hover {{
            background: #f8f9fa;
        }}
        .vulnerability-header.critical {{ background: #f8d7da; }}
        .vulnerability-header.high {{ background: #ffeaa7; }}
        .vulnerability-header.medium {{ background: #fff3cd; }}
        .vulnerability-header.low {{ background: #d4edda; }}
        .vulnerability-content {{
            display: none;
            padding: 15px;
            background: #f8f9fa;
        }}
        .vulnerability-content.show {{
            display: block;
        }}
        .code-snippet {{
            background: #f1f3f4;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            margin: 10px 0;
            overflow-x: auto;
        }}
        .severity-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }}
        .severity-critical {{ background: #dc3545; }}
        .severity-high {{ background: #fd7e14; }}
        .severity-medium {{ background: #ffc107; color: #333; }}
        .severity-low {{ background: #28a745; }}
    </style>
    <script>
        function toggleVulnerability(element) {{
            const content = element.nextElementSibling;
            content.classList.toggle('show');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Security Scan Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card critical">
                <h3>Critical</h3>
                <div class="value">{severity_counts['critical']}</div>
            </div>
            <div class="summary-card high">
                <h3>High</h3>
                <div class="value">{severity_counts['high']}</div>
            </div>
            <div class="summary-card medium">
                <h3>Medium</h3>
                <div class="value">{severity_counts['medium']}</div>
            </div>
            <div class="summary-card low">
                <h3>Low</h3>
                <div class="value">{severity_counts['low']}</div>
            </div>
        </div>
        
        <h2>Vulnerabilities ({total_vulnerabilities} total)</h2>
"""
        
        # Sort vulnerabilities by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_vulnerabilities = sorted(
            all_vulnerabilities,
            key=lambda v: (severity_order.get(v.severity, 4), v.file_path, v.line_number)
        )
        
        for vuln in sorted_vulnerabilities:
            html_content += f"""
        <div class="vulnerability">
            <div class="vulnerability-header {vuln.severity}" onclick="toggleVulnerability(this)">
                <h3>{vuln.title} <span class="severity-badge severity-{vuln.severity}">{vuln.severity}</span></h3>
                <p><strong>File:</strong> {vuln.file_path}:{vuln.line_number}</p>
                <p><strong>Category:</strong> {vuln.category}</p>
            </div>
            <div class="vulnerability-content">
                <p><strong>Description:</strong> {vuln.description}</p>
                <div class="code-snippet">{vuln.code_snippet}</div>
                <p><strong>Recommendation:</strong> {vuln.recommendation}</p>
                {f'<p><strong>CWE ID:</strong> {vuln.cwe_id}</p>' if vuln.cwe_id else ''}
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Security report generated: {output_file}")
    
    def _generate_vulnerability_id(self, file_path: Path, line_number: int, category: str) -> str:
        """Generate unique vulnerability ID."""
        content = f"{file_path}:{line_number}:{category}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _get_severity(self, category: str) -> str:
        """Get severity level for vulnerability category."""
        severity_map = {
            'sql_injection': 'critical',
            'command_injection': 'critical',
            'path_traversal': 'high',
            'hardcoded_secrets': 'high',
            'xss_vulnerabilities': 'high',
            'unsafe_deserialization': 'high',
            'insecure_random': 'medium',
            'weak_crypto': 'medium'
        }
        return severity_map.get(category, 'low')
    
    def _get_vulnerability_title(self, category: str) -> str:
        """Get vulnerability title."""
        titles = {
            'sql_injection': 'SQL Injection Vulnerability',
            'command_injection': 'Command Injection Vulnerability',
            'path_traversal': 'Path Traversal Vulnerability',
            'hardcoded_secrets': 'Hardcoded Secret/Credential',
            'xss_vulnerabilities': 'Cross-Site Scripting (XSS) Vulnerability',
            'insecure_random': 'Insecure Random Number Generation',
            'weak_crypto': 'Weak Cryptographic Algorithm',
            'unsafe_deserialization': 'Unsafe Deserialization'
        }
        return titles.get(category, 'Security Vulnerability')
    
    def _get_vulnerability_description(self, category: str) -> str:
        """Get vulnerability description."""
        descriptions = {
            'sql_injection': 'Code appears to be vulnerable to SQL injection attacks through unsanitized user input.',
            'command_injection': 'Code executes system commands with potentially unsafe input, allowing command injection.',
            'path_traversal': 'File path operations may allow directory traversal attacks.',
            'hardcoded_secrets': 'Sensitive credentials or secrets are hardcoded in the source code.',
            'xss_vulnerabilities': 'Code may be vulnerable to cross-site scripting attacks.',
            'insecure_random': 'Code uses insecure random number generation for security-sensitive operations.',
            'weak_crypto': 'Code uses weak or deprecated cryptographic algorithms.',
            'unsafe_deserialization': 'Code deserializes untrusted data which could lead to code execution.'
        }
        return descriptions.get(category, 'Security vulnerability detected.')
    
    def _get_recommendation(self, category: str) -> str:
        """Get security recommendation."""
        recommendations = {
            'sql_injection': 'Use parameterized queries or prepared statements instead of string concatenation.',
            'command_injection': 'Avoid executing system commands with user input. Use safe alternatives or proper input validation.',
            'path_traversal': 'Validate and sanitize file paths. Use os.path.abspath() and check against allowed directories.',
            'hardcoded_secrets': 'Move secrets to environment variables or secure configuration files.',
            'xss_vulnerabilities': 'Properly escape or sanitize user input before rendering in HTML.',
            'insecure_random': 'Use cryptographically secure random number generators (secrets module in Python).',
            'weak_crypto': 'Use strong, modern cryptographic algorithms (AES, SHA-256, etc.).',
            'unsafe_deserialization': 'Avoid deserializing untrusted data or use safe serialization formats like JSON.'
        }
        return recommendations.get(category, 'Review and fix the security issue.')
    
    def _get_cwe_id(self, category: str) -> Optional[str]:
        """Get CWE (Common Weakness Enumeration) ID."""
        cwe_map = {
            'sql_injection': 'CWE-89',
            'command_injection': 'CWE-78',
            'path_traversal': 'CWE-22',
            'hardcoded_secrets': 'CWE-798',
            'xss_vulnerabilities': 'CWE-79',
            'insecure_random': 'CWE-338',
            'weak_crypto': 'CWE-327',
            'unsafe_deserialization': 'CWE-502'
        }
        return cwe_map.get(category)
    
    def _map_safety_severity(self, safety_severity: str) -> str:
        """Map Safety severity to our severity levels."""
        mapping = {
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(safety_severity.lower(), 'medium')


def main():
    """Main function for security scanning."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive security scanner')
    parser.add_argument('--directory', '-d', default='.', help='Directory to scan')
    parser.add_argument('--output', '-o', default='security_report.html', help='Output report file')
    parser.add_argument('--json-output', help='JSON output file')
    parser.add_argument('--include-bandit', action='store_true', help='Include Bandit scan results')
    parser.add_argument('--include-safety', action='store_true', help='Include Safety scan results')
    parser.add_argument('--include-semgrep', action='store_true', help='Include Semgrep scan results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scanner = SecurityScanner()
    scan_results = []
    
    # Run static analysis scan
    print(f"Scanning directory: {args.directory}")
    static_result = scanner.scan_directory(Path(args.directory))
    scan_results.append(static_result)
    
    print(f"Static analysis completed:")
    print(f"  Files scanned: {static_result.total_files_scanned}")
    print(f"  Vulnerabilities found: {len(static_result.vulnerabilities)}")
    print(f"  Scan duration: {static_result.scan_duration:.2f}s")
    
    # Run additional scans if requested
    if args.include_bandit:
        print("Running Bandit scan...")
        bandit_result = scanner.run_bandit_scan(Path(args.directory))
        if bandit_result:
            print(f"  Bandit found {len(bandit_result.get('results', []))} issues")
    
    if args.include_safety:
        print("Running Safety scan...")
        safety_result = scanner.run_safety_scan()
        if safety_result:
            print(f"  Safety found {len(safety_result)} vulnerabilities")
    
    if args.include_semgrep:
        print("Running Semgrep scan...")
        semgrep_result = scanner.run_semgrep_scan(Path(args.directory))
        if semgrep_result:
            print(f"  Semgrep found {len(semgrep_result.get('results', []))} issues")
    
    # Generate reports
    scanner.generate_security_report(scan_results, args.output)
    print(f"Security report generated: {args.output}")
    
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump([asdict(result) for result in scan_results], f, indent=2)
        print(f"JSON report generated: {args.json_output}")
    
    # Exit with appropriate code
    total_critical = sum(
        sum(1 for v in result.vulnerabilities if v.severity == 'critical')
        for result in scan_results
    )
    total_high = sum(
        sum(1 for v in result.vulnerabilities if v.severity == 'high')
        for result in scan_results
    )
    
    if total_critical > 0:
        print(f"CRITICAL: {total_critical} critical vulnerabilities found!")
        sys.exit(2)
    elif total_high > 0:
        print(f"WARNING: {total_high} high severity vulnerabilities found!")
        sys.exit(1)
    else:
        print("No critical or high severity vulnerabilities found.")
        sys.exit(0)


if __name__ == '__main__':
    main()