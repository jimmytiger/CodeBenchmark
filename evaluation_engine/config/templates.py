"""
Model template management system for configuration-driven evaluation.

This module provides template management functionality for different model types,
including prompt templates, system prompts, and model-specific formatting.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Pattern
from enum import Enum
from pathlib import Path
import json
import yaml


class ModelType(Enum):
    """Supported model types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class TemplateVariableType(Enum):
    """Types of template variables."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


@dataclass
class TemplateVariable:
    """Definition of a template variable."""
    name: str
    type: TemplateVariableType
    description: str
    required: bool = True
    default_value: Optional[Any] = None
    
    def __post_init__(self):
        """Validate template variable definition."""
        if not self.name:
            raise ValueError("Template variable name cannot be empty")
        if not self.description:
            raise ValueError("Template variable description cannot be empty")


@dataclass
class ModelTemplate:
    """Template definition for a specific model type."""
    name: str
    model_type: ModelType
    description: str
    prompt_template: str
    system_prompt: Optional[str] = None
    variables: List[TemplateVariable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate model template definition."""
        if not self.name:
            raise ValueError("Template name cannot be empty")
        if not self.description:
            raise ValueError("Template description cannot be empty")
        if not self.prompt_template:
            raise ValueError("Prompt template cannot be empty")


@dataclass
class TemplateValidationResult:
    """Result of template validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_variables: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a validation warning."""
        self.warnings.append(warning)


class ModelTemplateManager:
    """
    Manager for model templates and prompt formatting.
    
    This class handles loading, validating, and applying model templates
    for different model types. It supports built-in templates as well as
    custom user-defined templates.
    """
    
    def __init__(self):
        """Initialize the template manager."""
        self._templates: Dict[str, ModelTemplate] = {}
        self._variable_pattern: Pattern = re.compile(r'\{([^}]*)\}')
        self._load_builtin_templates()
    
    def get_model_template(self, model_type: str, model_name: str) -> Optional[ModelTemplate]:
        """
        Get a model template by type and name.
        
        Args:
            model_type: Type of the model (e.g., "openai", "anthropic")
            model_name: Specific model name or template identifier
            
        Returns:
            ModelTemplate if found, None otherwise
        """
        # Try exact match first
        template_key = f"{model_type}:{model_name}"
        if template_key in self._templates:
            return self._templates[template_key]
        
        # Try model type default
        default_key = f"{model_type}:default"
        if default_key in self._templates:
            return self._templates[default_key]
        
        return None
    
    def register_template(self, template: ModelTemplate) -> bool:
        """
        Register a new model template.
        
        Args:
            template: ModelTemplate to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate template before registration
            validation_result = self.validate_template_syntax(template.prompt_template)
            if not validation_result.is_valid:
                return False
            
            template_key = f"{template.model_type.value}:{template.name}"
            self._templates[template_key] = template
            return True
        except Exception:
            return False
    
    def apply_prompt_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Apply a prompt template with the given context variables.
        
        Args:
            template: Template string with {variable} placeholders
            context: Dictionary of variable values
            
        Returns:
            Formatted template string
            
        Raises:
            ValueError: If required variables are missing
        """
        # Find all variables in the template
        variables = self._variable_pattern.findall(template)
        
        # Check for missing required variables
        missing_vars = []
        for var in variables:
            if var not in context:
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required template variables: {missing_vars}")
        
        # Apply template formatting
        try:
            return template.format(**context)
        except KeyError as e:
            raise ValueError(f"Template variable not found in context: {e}")
        except Exception as e:
            raise ValueError(f"Template formatting error: {e}")
    
    def validate_template_syntax(self, template: str) -> TemplateValidationResult:
        """
        Validate template syntax and structure.
        
        Args:
            template: Template string to validate
            
        Returns:
            TemplateValidationResult with validation details
        """
        result = TemplateValidationResult(is_valid=True)
        
        if not template or not template.strip():
            result.add_error("Template cannot be empty")
            return result
        
        # Check for balanced braces
        open_braces = template.count('{')
        close_braces = template.count('}')
        if open_braces != close_braces:
            result.add_error(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # Find all variable references
        variables = self._variable_pattern.findall(template)
        
        # Check for empty variable names
        for var in variables:
            if not var or not var.strip():
                result.add_error("Empty variable name found in template")
        
        # Check for nested braces (not supported)
        if re.search(r'\{[^}]*\{', template):
            result.add_error("Nested braces are not supported in templates")
        
        return result
    
    def load_builtin_templates(self) -> Dict[str, ModelTemplate]:
        """
        Load all built-in model templates.
        
        Returns:
            Dictionary of loaded templates
        """
        return dict(self._templates)
    
    def load_template_from_file(self, file_path: str) -> Optional[ModelTemplate]:
        """
        Load a template from a file.
        
        Args:
            file_path: Path to the template file (JSON or YAML)
            
        Returns:
            ModelTemplate if loaded successfully, None otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    return None
            
            return self._parse_template_data(data)
        except Exception:
            return None
    
    def save_template_to_file(self, template: ModelTemplate, file_path: str) -> bool:
        """
        Save a template to a file.
        
        Args:
            template: ModelTemplate to save
            file_path: Path where to save the template
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            template_data = {
                'name': template.name,
                'model_type': template.model_type.value,
                'description': template.description,
                'prompt_template': template.prompt_template,
                'system_prompt': template.system_prompt,
                'variables': [
                    {
                        'name': var.name,
                        'type': var.type.value,
                        'description': var.description,
                        'required': var.required,
                        'default_value': var.default_value
                    }
                    for var in template.variables
                ],
                'metadata': template.metadata
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(template_data, f, default_flow_style=False)
                elif path.suffix.lower() == '.json':
                    json.dump(template_data, f, indent=2)
                else:
                    return False
            
            return True
        except Exception:
            return False
    
    def list_templates(self, model_type: Optional[str] = None) -> List[str]:
        """
        List available templates, optionally filtered by model type.
        
        Args:
            model_type: Optional model type filter
            
        Returns:
            List of template identifiers
        """
        if model_type:
            return [key for key in self._templates.keys() if key.startswith(f"{model_type}:")]
        return list(self._templates.keys())
    
    def _load_builtin_templates(self):
        """Load built-in templates for supported model types."""
        # OpenAI model templates
        self._load_openai_templates()
        
        # Anthropic Claude templates
        self._load_anthropic_templates()
        
        # Hugging Face model templates
        self._load_huggingface_templates()
    
    def _load_openai_templates(self):
        """Load built-in OpenAI model templates."""
        # Default OpenAI template
        openai_default = ModelTemplate(
            name="default",
            model_type=ModelType.OPENAI,
            description="Default OpenAI chat completion template",
            prompt_template="{question}",
            system_prompt="You are a helpful assistant. Please provide accurate and helpful responses.",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The question or prompt to send to the model",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "supports_chat_format": True,
                "recommended_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            }
        )
        self.register_template(openai_default)
        
        # Q&A format template
        openai_qa = ModelTemplate(
            name="qa",
            model_type=ModelType.OPENAI,
            description="Question and Answer format for OpenAI models",
            prompt_template="Question: {question}\n\nAnswer:",
            system_prompt="You are a knowledgeable assistant. Answer questions accurately and concisely.",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The question to answer",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "format": "qa",
                "recommended_models": ["gpt-3.5-turbo", "gpt-4"]
            }
        )
        self.register_template(openai_qa)
        
        # Few-shot learning template
        openai_fewshot = ModelTemplate(
            name="fewshot",
            model_type=ModelType.OPENAI,
            description="Few-shot learning template with examples",
            prompt_template="{examples}\n\nQuestion: {question}\nAnswer:",
            system_prompt="You are an assistant that learns from examples. Follow the pattern shown in the examples.",
            variables=[
                TemplateVariable(
                    name="examples",
                    type=TemplateVariableType.STRING,
                    description="Few-shot examples in the format 'Question: ... Answer: ...'",
                    required=True
                ),
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The question to answer",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "format": "fewshot",
                "recommended_models": ["gpt-3.5-turbo", "gpt-4"]
            }
        )
        self.register_template(openai_fewshot)
    
    def _load_anthropic_templates(self):
        """Load built-in Anthropic Claude model templates."""
        # Default Claude template
        claude_default = ModelTemplate(
            name="default",
            model_type=ModelType.ANTHROPIC,
            description="Default Anthropic Claude conversation template",
            prompt_template="Human: {question}\n\nAssistant:",
            system_prompt="You are Claude, an AI assistant created by Anthropic. You are helpful, harmless, and honest.",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The human's question or message",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "conversation_format": "human_assistant",
                "recommended_models": ["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
            }
        )
        self.register_template(claude_default)
        
        # Multi-turn conversation template
        claude_conversation = ModelTemplate(
            name="conversation",
            model_type=ModelType.ANTHROPIC,
            description="Multi-turn conversation template for Claude",
            prompt_template="{conversation_history}\n\nHuman: {question}\n\nAssistant:",
            system_prompt="You are Claude, an AI assistant. Continue the conversation naturally and helpfully.",
            variables=[
                TemplateVariable(
                    name="conversation_history",
                    type=TemplateVariableType.STRING,
                    description="Previous conversation turns in Human/Assistant format",
                    required=False,
                    default_value=""
                ),
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The current human message",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "conversation_format": "multi_turn",
                "recommended_models": ["claude-3-sonnet-20240229", "claude-3-opus-20240229"]
            }
        )
        self.register_template(claude_conversation)
        
        # Analysis template
        claude_analysis = ModelTemplate(
            name="analysis",
            model_type=ModelType.ANTHROPIC,
            description="Structured analysis template for Claude",
            prompt_template="Human: Please analyze the following:\n\n{content}\n\nProvide a detailed analysis covering:\n1. Key points\n2. Implications\n3. Recommendations\n\nAssistant:",
            system_prompt="You are Claude, an expert analyst. Provide thorough, structured analysis with clear reasoning.",
            variables=[
                TemplateVariable(
                    name="content",
                    type=TemplateVariableType.STRING,
                    description="The content to analyze",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "format": "analysis",
                "recommended_models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
            }
        )
        self.register_template(claude_analysis)
    
    def _load_huggingface_templates(self):
        """Load built-in Hugging Face model templates."""
        # Llama-2 Chat template
        llama2_chat = ModelTemplate(
            name="llama2-chat",
            model_type=ModelType.HUGGINGFACE,
            description="Llama-2 Chat model template with proper formatting",
            prompt_template="<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{question} [/INST]",
            system_prompt="You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The user's question or instruction",
                    required=True
                ),
                TemplateVariable(
                    name="system_prompt",
                    type=TemplateVariableType.STRING,
                    description="System prompt for the model",
                    required=False,
                    default_value="You are a helpful assistant."
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "format": "llama2_chat",
                "recommended_models": ["meta-llama/Llama-2-7b-chat-hf", "meta-llama/Llama-2-13b-chat-hf", "meta-llama/Llama-2-70b-chat-hf"]
            }
        )
        self.register_template(llama2_chat)
        
        # Mistral Instruct template
        mistral_instruct = ModelTemplate(
            name="mistral-instruct",
            model_type=ModelType.HUGGINGFACE,
            description="Mistral Instruct model template",
            prompt_template="<s>[INST] {question} [/INST]",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The instruction or question",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": False,
                "format": "mistral_instruct",
                "recommended_models": ["mistralai/Mistral-7B-Instruct-v0.1", "mistralai/Mistral-7B-Instruct-v0.2"]
            }
        )
        self.register_template(mistral_instruct)
        
        # CodeLlama template
        codellama = ModelTemplate(
            name="codellama",
            model_type=ModelType.HUGGINGFACE,
            description="CodeLlama model template for code generation",
            prompt_template="# {task_description}\n\n{code_context}\n\n# Complete the following:\n{question}",
            system_prompt="You are a helpful coding assistant. Generate clean, efficient, and well-documented code.",
            variables=[
                TemplateVariable(
                    name="task_description",
                    type=TemplateVariableType.STRING,
                    description="Description of the coding task",
                    required=True
                ),
                TemplateVariable(
                    name="code_context",
                    type=TemplateVariableType.STRING,
                    description="Existing code context or imports",
                    required=False,
                    default_value=""
                ),
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The specific code to generate or complete",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": True,
                "format": "code_generation",
                "recommended_models": ["codellama/CodeLlama-7b-Instruct-hf", "codellama/CodeLlama-13b-Instruct-hf"]
            }
        )
        self.register_template(codellama)
        
        # Default HuggingFace template
        hf_default = ModelTemplate(
            name="default",
            model_type=ModelType.HUGGINGFACE,
            description="Default Hugging Face model template",
            prompt_template="{question}",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The input text or question",
                    required=True
                )
            ],
            metadata={
                "supports_system_prompt": False,
                "format": "plain_text",
                "recommended_models": ["any"]
            }
        )
        self.register_template(hf_default)
    
    def register_custom_template(self, template_data: Dict[str, Any]) -> bool:
        """
        Register a custom template from dictionary data.
        
        Args:
            template_data: Dictionary containing template definition
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            template = self._parse_template_data(template_data)
            if template is None:
                return False
            
            return self.register_template(template)
        except Exception:
            return False
    
    def get_builtin_template_names(self, model_type: Optional[str] = None) -> List[str]:
        """
        Get names of built-in templates.
        
        Args:
            model_type: Optional model type filter
            
        Returns:
            List of built-in template names
        """
        builtin_templates = []
        
        if model_type is None or model_type == "openai":
            builtin_templates.extend(["openai:default", "openai:qa", "openai:fewshot"])
        
        if model_type is None or model_type == "anthropic":
            builtin_templates.extend(["anthropic:default", "anthropic:conversation", "anthropic:analysis"])
        
        if model_type is None or model_type == "huggingface":
            builtin_templates.extend([
                "huggingface:default", 
                "huggingface:llama2-chat", 
                "huggingface:mistral-instruct", 
                "huggingface:codellama"
            ])
        
        return builtin_templates
    
    def get_template_metadata(self, model_type: str, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific template.
        
        Args:
            model_type: Type of the model
            template_name: Name of the template
            
        Returns:
            Template metadata if found, None otherwise
        """
        template = self.get_model_template(model_type, template_name)
        if template:
            return template.metadata
        return None
    
    def apply_model_template(self, model_type: str, model_name: str, context: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Apply a model template with context and return formatted prompts.
        
        Args:
            model_type: Type of the model
            model_name: Name of the model or template
            context: Context variables for template substitution
            
        Returns:
            Dictionary with 'prompt' and optionally 'system_prompt' keys, or None if template not found
        """
        template = self.get_model_template(model_type, model_name)
        if not template:
            return None
        
        try:
            # Apply prompt template
            formatted_prompt = self.apply_prompt_template(template.prompt_template, context)
            
            result = {"prompt": formatted_prompt}
            
            # Apply system prompt if available
            if template.system_prompt:
                # Check if system prompt contains variables
                if self._variable_pattern.search(template.system_prompt):
                    formatted_system_prompt = self.apply_prompt_template(template.system_prompt, context)
                else:
                    formatted_system_prompt = template.system_prompt
                result["system_prompt"] = formatted_system_prompt
            
            return result
        except Exception:
            return None
    
    def format_for_model_type(self, model_type: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Format prompt and system prompt according to model type conventions.
        
        Args:
            model_type: Type of the model
            prompt: The main prompt text
            system_prompt: Optional system prompt
            
        Returns:
            Formatted prompt string ready for the model
        """
        if model_type == ModelType.OPENAI.value:
            # OpenAI models handle system prompts separately in the API
            return prompt
        
        elif model_type == ModelType.ANTHROPIC.value:
            # Anthropic models use Human/Assistant format
            if system_prompt:
                return f"System: {system_prompt}\n\n{prompt}"
            return prompt
        
        elif model_type == ModelType.HUGGINGFACE.value:
            # Hugging Face models may need special formatting
            if system_prompt:
                # Check if prompt already contains system prompt formatting
                if "[INST]" in prompt and "<<SYS>>" in prompt:
                    return prompt  # Already formatted
                elif "[INST]" in prompt:
                    # Mistral-style format
                    return prompt
                else:
                    # Generic format with system prompt
                    return f"System: {system_prompt}\n\n{prompt}"
            return prompt
        
        else:
            # Custom or unknown model type - return as-is
            return prompt
    
    def validate_template_context(self, template: ModelTemplate, context: Dict[str, Any]) -> TemplateValidationResult:
        """
        Validate that the provided context matches the template requirements.
        
        Args:
            template: The model template to validate against
            context: The context variables to validate
            
        Returns:
            TemplateValidationResult with validation details
        """
        result = TemplateValidationResult(is_valid=True)
        
        # Check required variables
        for variable in template.variables:
            if variable.required and variable.name not in context:
                result.missing_variables.append(variable.name)
                result.add_error(f"Required variable '{variable.name}' is missing from context")
        
        # Check for unused variables in context
        template_vars = {var.name for var in template.variables}
        prompt_vars = set(self._variable_pattern.findall(template.prompt_template))
        if template.system_prompt:
            prompt_vars.update(self._variable_pattern.findall(template.system_prompt))
        
        for context_var in context.keys():
            if context_var not in template_vars and context_var not in prompt_vars:
                result.unused_variables.append(context_var)
                result.add_warning(f"Context variable '{context_var}' is not used in template")
        
        # Validate variable types
        for variable in template.variables:
            if variable.name in context:
                value = context[variable.name]
                if not self._validate_variable_type(value, variable.type):
                    result.add_error(f"Variable '{variable.name}' has incorrect type. Expected {variable.type.value}")
        
        return result
    
    def _validate_variable_type(self, value: Any, expected_type: TemplateVariableType) -> bool:
        """
        Validate that a value matches the expected template variable type.
        
        Args:
            value: The value to validate
            expected_type: The expected variable type
            
        Returns:
            True if the type matches, False otherwise
        """
        if expected_type == TemplateVariableType.STRING:
            return isinstance(value, str)
        elif expected_type == TemplateVariableType.INTEGER:
            return isinstance(value, int)
        elif expected_type == TemplateVariableType.FLOAT:
            return isinstance(value, (int, float))
        elif expected_type == TemplateVariableType.BOOLEAN:
            return isinstance(value, bool)
        elif expected_type == TemplateVariableType.LIST:
            return isinstance(value, list)
        elif expected_type == TemplateVariableType.DICT:
            return isinstance(value, dict)
        else:
            return True  # Unknown type, allow anything
    
    def create_template_context(self, **kwargs) -> Dict[str, Any]:
        """
        Create a template context dictionary from keyword arguments.
        
        Args:
            **kwargs: Variable name-value pairs
            
        Returns:
            Dictionary suitable for template application
        """
        return dict(kwargs)
    
    def get_template_variables(self, model_type: str, template_name: str) -> List[TemplateVariable]:
        """
        Get the list of variables required by a template.
        
        Args:
            model_type: Type of the model
            template_name: Name of the template
            
        Returns:
            List of TemplateVariable objects, empty list if template not found
        """
        template = self.get_model_template(model_type, template_name)
        if template:
            return template.variables
        return []
    
    def _parse_template_data(self, data: Dict[str, Any]) -> Optional[ModelTemplate]:
        """
        Parse template data from dictionary.
        
        Args:
            data: Dictionary containing template data
            
        Returns:
            ModelTemplate if parsing successful, None otherwise
        """
        try:
            # Parse variables
            variables = []
            for var_data in data.get('variables', []):
                variable = TemplateVariable(
                    name=var_data['name'],
                    type=TemplateVariableType(var_data['type']),
                    description=var_data['description'],
                    required=var_data.get('required', True),
                    default_value=var_data.get('default_value')
                )
                variables.append(variable)
            
            # Create template
            template = ModelTemplate(
                name=data['name'],
                model_type=ModelType(data['model_type']),
                description=data['description'],
                prompt_template=data['prompt_template'],
                system_prompt=data.get('system_prompt'),
                variables=variables,
                metadata=data.get('metadata', {})
            )
            
            return template
        except Exception:
            return None