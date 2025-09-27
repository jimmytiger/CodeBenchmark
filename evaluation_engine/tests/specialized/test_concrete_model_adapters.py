#!/usr/bin/env python3
"""
Test script for concrete model adapters implementation.

This script validates that all model adapters are properly implemented
and can be instantiated with correct configurations.
"""

import os
import sys
import logging
from typing import Dict, Any, List
import asyncio

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_engine.core.concrete_model_adapters import (
    OpenAIModelAdapter,
    AnthropicModelAdapter,
    DashScopeModelAdapter,
    GoogleModelAdapter,
    CohereModelAdapter,
    HuggingFaceModelAdapter,
    create_model_adapter,
    get_available_adapters,
    validate_model_configuration,
    test_model_adapter
)
from evaluation_engine.core.model_adapters import ModelType, RateLimitConfig, ModelCapabilities


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_adapter_instantiation():
    """Test that all adapters can be instantiated."""
    print("Testing adapter instantiation...")
    
    test_cases = [
        {
            'name': 'OpenAI GPT-4',
            'class': OpenAIModelAdapter,
            'model_id': 'gpt-4',
            'api_key': 'test-key'
        },
        {
            'name': 'Anthropic Claude',
            'class': AnthropicModelAdapter,
            'model_id': 'claude-3-sonnet-20240229',
            'api_key': 'test-key'
        },
        {
            'name': 'DashScope Qwen',
            'class': DashScopeModelAdapter,
            'model_id': 'qwen-max',
            'api_key': 'test-key'
        },
        {
            'name': 'Google Gemini',
            'class': GoogleModelAdapter,
            'model_id': 'gemini-pro',
            'api_key': 'test-key'
        },
        {
            'name': 'Cohere Command',
            'class': CohereModelAdapter,
            'model_id': 'command',
            'api_key': 'test-key'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            adapter = test_case['class'](
                model_id=test_case['model_id'],
                api_key=test_case['api_key']
            )
            
            # Test basic properties
            assert adapter.model_id == test_case['model_id']
            assert adapter.api_key == test_case['api_key']
            assert isinstance(adapter.capabilities, ModelCapabilities)
            assert isinstance(adapter.rate_limit_config, RateLimitConfig)
            
            # Test model info
            info = adapter.get_model_info()
            assert 'model_id' in info
            assert 'model_type' in info
            assert 'capabilities' in info
            
            results.append({
                'name': test_case['name'],
                'success': True,
                'error': None
            })
            print(f"✓ {test_case['name']}: Successfully instantiated")
            
        except Exception as e:
            results.append({
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })
            print(f"✗ {test_case['name']}: Failed - {e}")
    
    return results


def test_huggingface_adapter():
    """Test HuggingFace adapter separately due to different requirements."""
    print("\nTesting HuggingFace adapter...")
    
    try:
        # Try to import transformers
        import transformers
        
        # Use a small model for testing
        adapter = HuggingFaceModelAdapter(
            model_id='microsoft/DialoGPT-small',
            device='cpu'  # Force CPU for testing
        )
        
        # Test basic properties
        assert adapter.model_id == 'microsoft/DialoGPT-small'
        assert isinstance(adapter.capabilities, ModelCapabilities)
        
        # Test model info
        info = adapter.get_model_info()
        assert 'model_id' in info
        assert 'model_type' in info
        
        print("✓ HuggingFace adapter: Successfully instantiated")
        return True
        
    except ImportError:
        print("⚠ HuggingFace adapter: Skipped (transformers not installed)")
        return True
    except Exception as e:
        print(f"✗ HuggingFace adapter: Failed - {e}")
        return False


def test_factory_function():
    """Test the create_model_adapter factory function."""
    print("\nTesting factory function...")
    
    test_cases = [
        ('openai', 'gpt-4', 'test-key'),
        ('anthropic', 'claude-3-sonnet-20240229', 'test-key'),
        ('dashscope', 'qwen-max', 'test-key'),
        ('google', 'gemini-pro', 'test-key'),
        ('cohere', 'command', 'test-key')
    ]
    
    results = []
    
    for provider, model_id, api_key in test_cases:
        try:
            adapter = create_model_adapter(
                provider=provider,
                model_id=model_id,
                api_key=api_key
            )
            
            assert adapter.model_id == model_id
            assert adapter.api_key == api_key
            
            results.append({
                'provider': provider,
                'success': True,
                'error': None
            })
            print(f"✓ Factory function for {provider}: Success")
            
        except Exception as e:
            results.append({
                'provider': provider,
                'success': False,
                'error': str(e)
            })
            print(f"✗ Factory function for {provider}: Failed - {e}")
    
    return results


def test_configuration_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    test_cases = [
        {
            'provider': 'openai',
            'model_id': 'gpt-4',
            'config': {'api_key': 'test-key', 'temperature': 0.7},
            'should_pass': True
        },
        {
            'provider': 'openai',
            'model_id': '',
            'config': {'api_key': 'test-key'},
            'should_pass': False
        },
        {
            'provider': 'openai',
            'model_id': 'gpt-4',
            'config': {'temperature': 3.0},  # Invalid temperature
            'should_pass': False
        },
        {
            'provider': 'anthropic',
            'model_id': 'claude-3-sonnet-20240229',
            'config': {},  # Missing API key
            'should_pass': False
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            is_valid, errors = validate_model_configuration(
                provider=test_case['provider'],
                model_id=test_case['model_id'],
                config=test_case['config']
            )
            
            if test_case['should_pass']:
                assert is_valid, f"Expected validation to pass but got errors: {errors}"
                print(f"✓ Validation test (should pass): Success")
            else:
                assert not is_valid, f"Expected validation to fail but it passed"
                print(f"✓ Validation test (should fail): Success - {errors}")
            
            results.append({
                'test_case': test_case,
                'success': True,
                'error': None
            })
            
        except Exception as e:
            results.append({
                'test_case': test_case,
                'success': False,
                'error': str(e)
            })
            print(f"✗ Validation test: Failed - {e}")
    
    return results


def test_available_adapters():
    """Test getting available adapters."""
    print("\nTesting available adapters...")
    
    try:
        adapters = get_available_adapters()
        
        # Check that we have the expected adapters
        expected_adapters = ['openai', 'anthropic', 'dashscope', 'google', 'cohere', 'huggingface']
        
        for expected in expected_adapters:
            if expected in adapters:
                print(f"✓ Found adapter: {expected}")
            else:
                print(f"⚠ Missing adapter: {expected}")
        
        print(f"Total adapters found: {len(adapters)}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to get available adapters: {e}")
        return False


def test_model_capabilities():
    """Test model capabilities for each adapter."""
    print("\nTesting model capabilities...")
    
    adapters = [
        ('OpenAI', OpenAIModelAdapter('gpt-4', api_key='test')),
        ('Anthropic', AnthropicModelAdapter('claude-3-sonnet-20240229', api_key='test')),
        ('DashScope', DashScopeModelAdapter('qwen-max', api_key='test')),
        ('Google', GoogleModelAdapter('gemini-pro', api_key='test')),
        ('Cohere', CohereModelAdapter('command', api_key='test'))
    ]
    
    results = []
    
    for name, adapter in adapters:
        try:
            capabilities = adapter.capabilities
            
            # Check required fields
            assert hasattr(capabilities, 'max_context_length')
            assert hasattr(capabilities, 'max_output_length')
            assert hasattr(capabilities, 'supports_chat_templates')
            assert hasattr(capabilities, 'supported_languages')
            
            # Check that values are reasonable
            assert capabilities.max_context_length > 0
            assert capabilities.max_output_length > 0
            assert isinstance(capabilities.supported_languages, list)
            
            results.append({
                'name': name,
                'success': True,
                'capabilities': capabilities.to_dict()
            })
            print(f"✓ {name} capabilities: Valid")
            
        except Exception as e:
            results.append({
                'name': name,
                'success': False,
                'error': str(e)
            })
            print(f"✗ {name} capabilities: Failed - {e}")
    
    return results


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\nTesting rate limiting...")
    
    try:
        # Create adapter with custom rate limits
        rate_config = RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            max_concurrent_requests=2
        )
        
        adapter = OpenAIModelAdapter(
            model_id='gpt-4',
            api_key='test-key',
            rate_limit_config=rate_config
        )
        
        # Test rate limit checking
        assert adapter._check_rate_limits() == True  # Should allow first request
        
        # Record some requests
        adapter._record_request(100)
        adapter._record_request(200)
        
        # Check that metrics are updated
        assert adapter.metrics.total_requests == 0  # Not updated until update_request is called
        
        print("✓ Rate limiting: Basic functionality works")
        return True
        
    except Exception as e:
        print(f"✗ Rate limiting: Failed - {e}")
        return False


def run_all_tests():
    """Run all tests and provide summary."""
    print("=" * 60)
    print("CONCRETE MODEL ADAPTERS TEST SUITE")
    print("=" * 60)
    
    test_results = {}
    
    # Run tests
    test_results['instantiation'] = test_adapter_instantiation()
    test_results['huggingface'] = test_huggingface_adapter()
    test_results['factory'] = test_factory_function()
    test_results['validation'] = test_configuration_validation()
    test_results['available'] = test_available_adapters()
    test_results['capabilities'] = test_model_capabilities()
    test_results['rate_limiting'] = test_rate_limiting()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, results in test_results.items():
        if isinstance(results, list):
            # Count individual test cases
            for result in results:
                total_tests += 1
                if result.get('success', False):
                    passed_tests += 1
        elif isinstance(results, bool):
            total_tests += 1
            if results:
                passed_tests += 1
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Model adapters are working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)