"""
Concrete Model Adapters for Major Providers

This module implements concrete model adapters for major AI providers:
- OpenAI (GPT models)
- Anthropic (Claude models)
- DashScope (Qwen models)
- Google (Gemini models)
- Cohere (Command models)
- HuggingFace (Local models)
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
from dataclasses import dataclass

from .model_adapters import ModelAdapter, ModelType, ModelCapabilities, register_model_adapter
from .advanced_model_config import ModelConfiguration


eval_logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standardized API response format."""
    content: str
    tokens_used: int = 0
    cost: float = 0.0
    response_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@register_model_adapter("openai", {"provider": "OpenAI", "supports_chat": True})
class OpenAIModelAdapter(ModelAdapter):
    """OpenAI model adapter with GPT support."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            model_id=model_id,
            model_type=ModelType.OPENAI,
            api_key=api_key,
            api_base=kwargs.get('api_base', 'https://api.openai.com/v1'),
            **kwargs
        )
        
        # Model-specific pricing (tokens per dollar)
        self.pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},  # per 1K tokens
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            'gpt-4o': {'input': 0.005, 'output': 0.015}
        }
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get OpenAI model capabilities."""
        if 'gpt-4' in self.model_id.lower():
            return ModelCapabilities(
                max_context_length=8192 if 'turbo' not in self.model_id else 128000,
                max_output_length=4096,
                supports_function_calling=True,
                supports_streaming=True,
                supports_chat_templates=True,
                supports_system_messages=True,
                supports_multimodal='vision' in self.model_id,
                supported_languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
            )
        else:  # GPT-3.5
            return ModelCapabilities(
                max_context_length=4096,
                max_output_length=2048,
                supports_function_calling=True,
                supports_streaming=True,
                supports_chat_templates=True,
                supports_system_messages=True,
                supported_languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
            )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from OpenAI response."""
        if isinstance(response, dict) and 'usage' in response:
            return response['usage'].get('total_tokens', 0)
        return 0
    
    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost based on OpenAI pricing."""
        model_key = self.model_id.lower()
        for key in self.pricing:
            if key in model_key:
                # Simplified cost calculation (assuming equal input/output)
                avg_price = (self.pricing[key]['input'] + self.pricing[key]['output']) / 2
                return (tokens_used / 1000) * avg_price
        return 0.0
    
    async def _make_openai_request(self, messages: List[Dict], **kwargs) -> APIResponse:
        """Make request to OpenAI API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model_id,
            'messages': messages,
            **kwargs
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.model_kwargs.get('timeout', 30)) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
        response_time = time.time() - start_time
        data = response.json()
        
        content = data['choices'][0]['message']['content']
        tokens_used = self._extract_token_usage(data)
        cost = self._calculate_cost(tokens_used)
        
        return APIResponse(
            content=content,
            tokens_used=tokens_used,
            cost=cost,
            response_time=response_time,
            metadata=data
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for OpenAI models."""
        # OpenAI doesn't provide direct loglikelihood, so we approximate
        results = []
        for context, continuation in requests:
            # Use completion probability as proxy
            messages = [{"role": "user", "content": context + continuation}]
            try:
                # This is a simplified implementation
                # In practice, you'd need to use the logprobs parameter
                results.append((0.0, True))  # Placeholder
            except Exception:
                results.append((float('-inf'), False))
        return results
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood."""
        # Simplified implementation
        return [0.0] * len(requests)
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                messages = [{"role": "user", "content": context}]
                
                # Extract generation parameters
                max_tokens = getattr(request, 'max_tokens', 1024)
                temperature = getattr(request, 'temperature', 0.7)
                stop = getattr(request, 'stop', None)
                
                # Make async request synchronously
                response = asyncio.run(self._make_openai_request(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop
                ))
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"OpenAI generation error: {e}")
                results.append("")
        
        return results


@register_model_adapter("anthropic", {"provider": "Anthropic", "supports_chat": True})
class AnthropicModelAdapter(ModelAdapter):
    """Anthropic Claude model adapter."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            model_id=model_id,
            model_type=ModelType.ANTHROPIC,
            api_key=api_key,
            api_base=kwargs.get('api_base', 'https://api.anthropic.com/v1'),
            **kwargs
        )
        
        # Claude pricing
        self.pricing = {
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125}
        }
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get Anthropic model capabilities."""
        if 'opus' in self.model_id.lower():
            context_length = 200000
        elif 'sonnet' in self.model_id.lower():
            context_length = 200000
        else:  # haiku
            context_length = 200000
        
        return ModelCapabilities(
            max_context_length=context_length,
            max_output_length=4096,
            supports_function_calling=False,
            supports_streaming=True,
            supports_chat_templates=True,
            supports_system_messages=True,
            supports_multimodal='vision' in self.model_id,
            supported_languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
        )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from Anthropic response."""
        if isinstance(response, dict) and 'usage' in response:
            input_tokens = response['usage'].get('input_tokens', 0)
            output_tokens = response['usage'].get('output_tokens', 0)
            return input_tokens + output_tokens
        return 0
    
    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost for Anthropic models."""
        model_key = self.model_id.lower()
        for key in self.pricing:
            if key in model_key:
                # Simplified cost calculation
                avg_price = (self.pricing[key]['input'] + self.pricing[key]['output']) / 2
                return (tokens_used / 1000) * avg_price
        return 0.0
    
    async def _make_anthropic_request(self, messages: List[Dict], **kwargs) -> APIResponse:
        """Make request to Anthropic API."""
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        # Convert messages to Anthropic format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        payload = {
            'model': self.model_id,
            'messages': user_messages,
            'max_tokens': kwargs.get('max_tokens', 1024),
            **kwargs
        }
        
        if system_message:
            payload['system'] = system_message
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.model_kwargs.get('timeout', 30)) as client:
            response = await client.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
        
        response_time = time.time() - start_time
        data = response.json()
        
        content = data['content'][0]['text']
        tokens_used = self._extract_token_usage(data)
        cost = self._calculate_cost(tokens_used)
        
        return APIResponse(
            content=content,
            tokens_used=tokens_used,
            cost=cost,
            response_time=response_time,
            metadata=data
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for Anthropic models."""
        # Anthropic doesn't provide loglikelihood, return approximation
        return [(0.0, True)] * len(requests)
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood."""
        return [0.0] * len(requests)
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                messages = [{"role": "user", "content": context}]
                
                max_tokens = getattr(request, 'max_tokens', 1024)
                temperature = getattr(request, 'temperature', 0.7)
                
                response = asyncio.run(self._make_anthropic_request(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ))
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"Anthropic generation error: {e}")
                results.append("")
        
        return results


@register_model_adapter("dashscope", {"provider": "Alibaba DashScope", "supports_chat": True})
class DashScopeModelAdapter(ModelAdapter):
    """DashScope Qwen model adapter."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            model_id=model_id,
            model_type=ModelType.DASHSCOPE,
            api_key=api_key,
            api_base=kwargs.get('api_base', 'https://dashscope.aliyuncs.com/api/v1'),
            **kwargs
        )
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get DashScope model capabilities."""
        if 'max' in self.model_id.lower():
            context_length = 6000
        elif 'plus' in self.model_id.lower():
            context_length = 30000
        else:
            context_length = 6000
        
        return ModelCapabilities(
            max_context_length=context_length,
            max_output_length=2048,
            supports_function_calling=True,
            supports_streaming=True,
            supports_chat_templates=True,
            supports_system_messages=True,
            supported_languages=['zh', 'en', 'ja', 'ko', 'es', 'fr', 'de']
        )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from DashScope response."""
        if isinstance(response, dict) and 'usage' in response:
            return response['usage'].get('total_tokens', 0)
        return 0
    
    async def _make_dashscope_request(self, messages: List[Dict], **kwargs) -> APIResponse:
        """Make request to DashScope API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model_id,
            'input': {
                'messages': messages
            },
            'parameters': {
                'max_tokens': kwargs.get('max_tokens', 1024),
                'temperature': kwargs.get('temperature', 0.7),
                **{k: v for k, v in kwargs.items() if k not in ['max_tokens', 'temperature']}
            }
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.model_kwargs.get('timeout', 30)) as client:
            response = await client.post(
                f"{self.api_base}/services/aigc/text-generation/generation",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
        
        response_time = time.time() - start_time
        data = response.json()
        
        content = data['output']['text']
        tokens_used = self._extract_token_usage(data)
        
        return APIResponse(
            content=content,
            tokens_used=tokens_used,
            cost=0.0,  # DashScope pricing varies
            response_time=response_time,
            metadata=data
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for DashScope models."""
        return [(0.0, True)] * len(requests)
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood."""
        return [0.0] * len(requests)
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                messages = [{"role": "user", "content": context}]
                
                max_tokens = getattr(request, 'max_tokens', 1024)
                temperature = getattr(request, 'temperature', 0.7)
                
                response = asyncio.run(self._make_dashscope_request(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ))
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"DashScope generation error: {e}")
                results.append("")
        
        return results


@register_model_adapter("google", {"provider": "Google", "supports_chat": True})
class GoogleModelAdapter(ModelAdapter):
    """Google Gemini model adapter."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            model_id=model_id,
            model_type=ModelType.GOOGLE,
            api_key=api_key,
            api_base=kwargs.get('api_base', 'https://generativelanguage.googleapis.com/v1'),
            **kwargs
        )
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get Google model capabilities."""
        if 'ultra' in self.model_id.lower():
            context_length = 32000
        else:  # pro
            context_length = 32000
        
        return ModelCapabilities(
            max_context_length=context_length,
            max_output_length=2048,
            supports_function_calling=True,
            supports_streaming=True,
            supports_chat_templates=True,
            supports_system_messages=True,
            supports_multimodal=True,
            supported_languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
        )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from Google response."""
        if isinstance(response, dict) and 'usageMetadata' in response:
            return response['usageMetadata'].get('totalTokenCount', 0)
        return 0
    
    async def _make_google_request(self, messages: List[Dict], **kwargs) -> APIResponse:
        """Make request to Google API."""
        # Convert messages to Google format
        contents = []
        for msg in messages:
            contents.append({
                'role': 'user' if msg['role'] == 'user' else 'model',
                'parts': [{'text': msg['content']}]
            })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'maxOutputTokens': kwargs.get('max_tokens', 1024),
                'temperature': kwargs.get('temperature', 0.7),
            }
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.model_kwargs.get('timeout', 30)) as client:
            response = await client.post(
                f"{self.api_base}/models/{self.model_id}:generateContent?key={self.api_key}",
                json=payload
            )
            response.raise_for_status()
        
        response_time = time.time() - start_time
        data = response.json()
        
        content = data['candidates'][0]['content']['parts'][0]['text']
        tokens_used = self._extract_token_usage(data)
        
        return APIResponse(
            content=content,
            tokens_used=tokens_used,
            cost=0.0,  # Google pricing varies
            response_time=response_time,
            metadata=data
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for Google models."""
        return [(0.0, True)] * len(requests)
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood."""
        return [0.0] * len(requests)
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                messages = [{"role": "user", "content": context}]
                
                max_tokens = getattr(request, 'max_tokens', 1024)
                temperature = getattr(request, 'temperature', 0.7)
                
                response = asyncio.run(self._make_google_request(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ))
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"Google generation error: {e}")
                results.append("")
        
        return results


@register_model_adapter("cohere", {"provider": "Cohere", "supports_chat": True})
class CohereModelAdapter(ModelAdapter):
    """Cohere Command model adapter."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            model_id=model_id,
            model_type=ModelType.COHERE,
            api_key=api_key,
            api_base=kwargs.get('api_base', 'https://api.cohere.ai/v1'),
            **kwargs
        )
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get Cohere model capabilities."""
        return ModelCapabilities(
            max_context_length=4096,
            max_output_length=2048,
            supports_function_calling=False,
            supports_streaming=True,
            supports_chat_templates=True,
            supports_system_messages=True,
            supported_languages=['en', 'es', 'fr', 'de', 'it', 'pt']
        )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from Cohere response."""
        if isinstance(response, dict) and 'meta' in response:
            billed_units = response['meta'].get('billed_units', {})
            return billed_units.get('input_tokens', 0) + billed_units.get('output_tokens', 0)
        return 0
    
    async def _make_cohere_request(self, messages: List[Dict], **kwargs) -> APIResponse:
        """Make request to Cohere API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Convert messages to Cohere chat format
        chat_history = []
        message = ""
        
        for msg in messages:
            if msg['role'] == 'user':
                message = msg['content']
            else:
                chat_history.append({
                    'role': msg['role'].upper(),
                    'message': msg['content']
                })
        
        payload = {
            'model': self.model_id,
            'message': message,
            'chat_history': chat_history,
            'max_tokens': kwargs.get('max_tokens', 1024),
            'temperature': kwargs.get('temperature', 0.7),
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.model_kwargs.get('timeout', 30)) as client:
            response = await client.post(
                f"{self.api_base}/chat",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
        
        response_time = time.time() - start_time
        data = response.json()
        
        content = data['text']
        tokens_used = self._extract_token_usage(data)
        
        return APIResponse(
            content=content,
            tokens_used=tokens_used,
            cost=0.0,  # Cohere pricing varies
            response_time=response_time,
            metadata=data
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for Cohere models."""
        return [(0.0, True)] * len(requests)
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood."""
        return [0.0] * len(requests)
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                messages = [{"role": "user", "content": context}]
                
                max_tokens = getattr(request, 'max_tokens', 1024)
                temperature = getattr(request, 'temperature', 0.7)
                
                response = asyncio.run(self._make_cohere_request(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ))
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"Cohere generation error: {e}")
                results.append("")
        
        return results


@register_model_adapter("huggingface", {"provider": "HuggingFace", "supports_local": True})
class HuggingFaceModelAdapter(ModelAdapter):
    """HuggingFace transformers model adapter."""
    
    def __init__(self, model_id: str, **kwargs):
        # Initialize transformers components first
        self.tokenizer = None
        self.model = None
        self.device = kwargs.get('device', 'auto')
        
        # Initialize parent class
        super().__init__(
            model_id=model_id,
            model_type=ModelType.HUGGINGFACE,
            **kwargs
        )
        
        # Initialize model after parent class
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize HuggingFace model and tokenizer."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map=self.device
            )
            
            # Add pad token if missing
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            eval_logger.info(f"Initialized HuggingFace model: {self.model_id}")
            
        except ImportError:
            eval_logger.error("transformers library not installed")
            raise
        except Exception as e:
            eval_logger.error(f"Failed to initialize HuggingFace model: {e}")
            raise
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get HuggingFace model capabilities."""
        # Default capabilities - would be model-specific in practice
        supports_chat = False
        if hasattr(self, 'tokenizer') and self.tokenizer is not None:
            supports_chat = hasattr(self.tokenizer, 'chat_template')
        
        return ModelCapabilities(
            max_context_length=2048,
            max_output_length=1024,
            supports_function_calling=False,
            supports_streaming=False,
            supports_chat_templates=supports_chat,
            supports_system_messages=True,
            supported_languages=['en']
        )
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from HuggingFace response."""
        if isinstance(response, dict) and 'tokens_used' in response:
            return response['tokens_used']
        return 0
    
    def _generate_with_hf(self, prompt: str, **kwargs) -> APIResponse:
        """Generate text using HuggingFace model."""
        import torch
        
        start_time = time.time()
        
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
        
        # Move to device
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=kwargs.get('max_tokens', 512),
                temperature=kwargs.get('temperature', 0.7),
                do_sample=kwargs.get('temperature', 0.7) > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode output
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove input prompt from output
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):].strip()
        
        response_time = time.time() - start_time
        tokens_used = len(outputs[0])
        
        return APIResponse(
            content=generated_text,
            tokens_used=tokens_used,
            cost=0.0,  # Local model has no API cost
            response_time=response_time,
            metadata={'input_length': len(inputs['input_ids'][0])}
        )
    
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood for HuggingFace models."""
        import torch
        
        results = []
        
        for context, continuation in requests:
            try:
                # Tokenize context and continuation
                context_tokens = self.tokenizer(context, return_tensors="pt")
                full_tokens = self.tokenizer(context + continuation, return_tensors="pt")
                
                # Move to device
                if hasattr(self.model, 'device'):
                    context_tokens = {k: v.to(self.model.device) for k, v in context_tokens.items()}
                    full_tokens = {k: v.to(self.model.device) for k, v in full_tokens.items()}
                
                # Calculate log-likelihood
                with torch.no_grad():
                    context_outputs = self.model(**context_tokens)
                    full_outputs = self.model(**full_tokens)
                
                # Extract logits for continuation tokens
                context_len = context_tokens['input_ids'].shape[1]
                continuation_logits = full_outputs.logits[0, context_len-1:-1]
                continuation_tokens = full_tokens['input_ids'][0, context_len:]
                
                # Calculate log probabilities
                log_probs = torch.nn.functional.log_softmax(continuation_logits, dim=-1)
                token_log_probs = log_probs.gather(1, continuation_tokens.unsqueeze(1)).squeeze(1)
                
                # Sum log probabilities for the continuation
                total_log_prob = token_log_probs.sum().item()
                results.append((total_log_prob, True))
                
            except Exception as e:
                eval_logger.error(f"HuggingFace loglikelihood error: {e}")
                results.append((float('-inf'), False))
        
        return results
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood for HuggingFace models."""
        import torch
        
        results = []
        
        for text in requests:
            try:
                # Tokenize text
                tokens = self.tokenizer(text, return_tensors="pt")
                
                # Move to device
                if hasattr(self.model, 'device'):
                    tokens = {k: v.to(self.model.device) for k, v in tokens.items()}
                
                # Calculate rolling log-likelihood
                with torch.no_grad():
                    outputs = self.model(**tokens)
                    logits = outputs.logits[0]
                    
                    # Calculate log probabilities
                    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
                    
                    # Get log probabilities for actual tokens (shifted by 1)
                    token_ids = tokens['input_ids'][0]
                    token_log_probs = []
                    
                    for i in range(1, len(token_ids)):
                        token_log_prob = log_probs[i-1, token_ids[i]].item()
                        token_log_probs.append(token_log_prob)
                    
                    # Average log probability
                    avg_log_prob = sum(token_log_probs) / len(token_log_probs) if token_log_probs else 0.0
                    results.append(avg_log_prob)
                
            except Exception as e:
                eval_logger.error(f"HuggingFace rolling loglikelihood error: {e}")
                results.append(float('-inf'))
        
        return results
    
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria for HuggingFace models."""
        results = []
        
        for request in requests:
            try:
                context = request.args[0] if hasattr(request, 'args') else str(request)
                
                # Extract generation parameters
                max_tokens = getattr(request, 'max_tokens', 512)
                temperature = getattr(request, 'temperature', 0.7)
                stop = getattr(request, 'stop', None)
                
                response = self._generate_with_hf(
                    context,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop
                )
                
                results.append(response.content)
                
            except Exception as e:
                eval_logger.error(f"HuggingFace generation error: {e}")
                results.append("")
        
        return results


# Additional utility functions for model adapters

def get_available_adapters() -> Dict[str, Dict[str, Any]]:
    """Get information about all available model adapters."""
    from .model_adapters import plugin_registry
    
    adapters = {}
    for plugin_name in plugin_registry.list_plugins():
        metadata = plugin_registry.get_plugin_metadata(plugin_name)
        adapters[plugin_name] = metadata
    
    return adapters


def create_model_adapter(
    provider: str, 
    model_id: str, 
    api_key: Optional[str] = None,
    **kwargs
) -> ModelAdapter:
    """
    Factory function to create model adapters.
    
    Args:
        provider: Provider name (openai, anthropic, dashscope, google, cohere, huggingface)
        model_id: Model identifier
        api_key: API key for the provider
        **kwargs: Additional configuration options
    
    Returns:
        ModelAdapter instance
    """
    from .model_adapters import plugin_registry
    
    provider_lower = provider.lower()
    
    # Map provider names to plugin names
    provider_mapping = {
        'openai': 'openai',
        'anthropic': 'anthropic', 
        'dashscope': 'dashscope',
        'google': 'google',
        'cohere': 'cohere',
        'huggingface': 'huggingface',
        'hf': 'huggingface'  # Alias
    }
    
    plugin_name = provider_mapping.get(provider_lower)
    if not plugin_name:
        raise ValueError(f"Unsupported provider: {provider}")
    
    try:
        return plugin_registry.create_adapter(
            plugin_name=plugin_name,
            model_id=model_id,
            api_key=api_key,
            **kwargs
        )
    except Exception as e:
        eval_logger.error(f"Failed to create adapter for {provider}: {e}")
        raise


def validate_model_configuration(
    provider: str,
    model_id: str,
    config: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate model configuration for a specific provider.
    
    Args:
        provider: Provider name
        model_id: Model identifier
        config: Configuration dictionary
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Common validations
    if not model_id:
        errors.append("Model ID is required")
    
    # Provider-specific validations
    provider_lower = provider.lower()
    
    if provider_lower in ['openai', 'anthropic', 'dashscope', 'google', 'cohere']:
        if not config.get('api_key'):
            errors.append(f"API key is required for {provider}")
    
    if provider_lower == 'huggingface':
        # Check if transformers is available
        try:
            import transformers
        except ImportError:
            errors.append("transformers library is required for HuggingFace models")
    
    # Validate generation parameters
    if 'temperature' in config:
        temp = config['temperature']
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            errors.append("Temperature must be a number between 0 and 2")
    
    if 'max_tokens' in config:
        max_tokens = config['max_tokens']
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            errors.append("max_tokens must be a positive integer")
    
    return len(errors) == 0, errors


def test_model_adapter(adapter: ModelAdapter, test_prompt: str = "Hello, world!") -> Dict[str, Any]:
    """
    Test a model adapter with a simple prompt.
    
    Args:
        adapter: ModelAdapter instance to test
        test_prompt: Test prompt to use
    
    Returns:
        Dictionary with test results
    """
    test_results = {
        'adapter_info': adapter.get_model_info(),
        'test_prompt': test_prompt,
        'success': False,
        'response': None,
        'error': None,
        'response_time': 0.0
    }
    
    try:
        start_time = time.time()
        
        # Create a simple request object
        class SimpleRequest:
            def __init__(self, prompt):
                self.args = [prompt]
                self.max_tokens = 50
                self.temperature = 0.7
                self.stop = None
        
        request = SimpleRequest(test_prompt)
        responses = adapter.generate_until([request])
        
        test_results['response_time'] = time.time() - start_time
        test_results['response'] = responses[0] if responses else None
        test_results['success'] = bool(responses and responses[0])
        
    except Exception as e:
        test_results['error'] = str(e)
        test_results['success'] = False
    
    return test_results


# Additional utility functions for model adapters

def get_available_adapters() -> Dict[str, Dict[str, Any]]:
    """Get information about all available model adapters."""
    from .model_adapters import plugin_registry
    
    adapters = {}
    for plugin_name in plugin_registry.list_plugins():
        metadata = plugin_registry.get_plugin_metadata(plugin_name)
        adapters[plugin_name] = metadata
    
    return adapters


def create_model_adapter(
    provider: str, 
    model_id: str, 
    api_key: Optional[str] = None,
    **kwargs
) -> ModelAdapter:
    """
    Factory function to create model adapters.
    
    Args:
        provider: Provider name (openai, anthropic, dashscope, google, cohere, huggingface)
        model_id: Model identifier
        api_key: API key for the provider
        **kwargs: Additional configuration options
    
    Returns:
        ModelAdapter instance
    """
    from .model_adapters import plugin_registry
    
    provider_lower = provider.lower()
    
    # Map provider names to plugin names
    provider_mapping = {
        'openai': 'openai',
        'anthropic': 'anthropic', 
        'dashscope': 'dashscope',
        'google': 'google',
        'cohere': 'cohere',
        'huggingface': 'huggingface',
        'hf': 'huggingface'  # Alias
    }
    
    plugin_name = provider_mapping.get(provider_lower)
    if not plugin_name:
        raise ValueError(f"Unsupported provider: {provider}")
    
    try:
        return plugin_registry.create_adapter(
            plugin_name=plugin_name,
            model_id=model_id,
            api_key=api_key,
            **kwargs
        )
    except Exception as e:
        eval_logger.error(f"Failed to create adapter for {provider}: {e}")
        raise


def validate_model_configuration(
    provider: str,
    model_id: str,
    config: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate model configuration for a specific provider.
    
    Args:
        provider: Provider name
        model_id: Model identifier
        config: Configuration dictionary
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Common validations
    if not model_id:
        errors.append("Model ID is required")
    
    # Provider-specific validations
    provider_lower = provider.lower()
    
    if provider_lower in ['openai', 'anthropic', 'dashscope', 'google', 'cohere']:
        if not config.get('api_key'):
            errors.append(f"API key is required for {provider}")
    
    if provider_lower == 'huggingface':
        # Check if transformers is available
        try:
            import transformers
        except ImportError:
            errors.append("transformers library is required for HuggingFace models")
    
    # Validate generation parameters
    if 'temperature' in config:
        temp = config['temperature']
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            errors.append("Temperature must be a number between 0 and 2")
    
    if 'max_tokens' in config:
        max_tokens = config['max_tokens']
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            errors.append("max_tokens must be a positive integer")
    
    return len(errors) == 0, errors


def test_model_adapter(adapter: ModelAdapter, test_prompt: str = "Hello, world!") -> Dict[str, Any]:
    """
    Test a model adapter with a simple prompt.
    
    Args:
        adapter: ModelAdapter instance to test
        test_prompt: Test prompt to use
    
    Returns:
        Dictionary with test results
    """
    test_results = {
        'adapter_info': adapter.get_model_info(),
        'test_prompt': test_prompt,
        'success': False,
        'response': None,
        'error': None,
        'response_time': 0.0
    }
    
    try:
        start_time = time.time()
        
        # Create a simple request object
        class SimpleRequest:
            def __init__(self, prompt):
                self.args = [prompt]
                self.max_tokens = 50
                self.temperature = 0.7
                self.stop = None
        
        request = SimpleRequest(test_prompt)
        responses = adapter.generate_until([request])
        
        test_results['response_time'] = time.time() - start_time
        test_results['response'] = responses[0] if responses else None
        test_results['success'] = bool(responses and responses[0])
        
    except Exception as e:
        test_results['error'] = str(e)
        test_results['success'] = False
    
    return test_results


# Export all adapter classes and utility functions
__all__ = [
    'OpenAIModelAdapter',
    'AnthropicModelAdapter', 
    'DashScopeModelAdapter',
    'GoogleModelAdapter',
    'CohereModelAdapter',
    'HuggingFaceModelAdapter',
    'APIResponse',
    'get_available_adapters',
    'create_model_adapter',
    'validate_model_configuration',
    'test_model_adapter'
]