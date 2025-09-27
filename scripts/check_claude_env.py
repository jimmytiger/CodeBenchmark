"""Simple check for Claude SDK availability and API key.
Run: python scripts\check_claude_env.py
"""
import importlib
import os

results = {}

# Check anthropic SDK
results['anthropic_installed'] = importlib.util.find_spec('anthropic') is not None
# Check claude-code-sdk
results['claude_code_sdk_installed'] = importlib.util.find_spec('claude_code_sdk') is not None
# Check env var
results['ANTHROPIC_API_KEY'] = bool(os.environ.get('ANTHROPIC_API_KEY'))

print('Claude environment check:')
print(f"  anthropic installed: {results['anthropic_installed']}")
print(f"  claude-code-sdk installed: {results['claude_code_sdk_installed']}")
print(f"  ANTHROPIC_API_KEY set: {results['ANTHROPIC_API_KEY']}")

if not results['anthropic_installed'] and not results['claude_code_sdk_installed']:
    print('\nNo Claude client SDK found. Install one of:')
    print('  pip install anthropic')
    print('  pip install claude-code-sdk')

if not results['ANTHROPIC_API_KEY']:
    print('\nEnvironment variable ANTHROPIC_API_KEY is not set. Set it before running evaluations.')

print('\nDone.')
