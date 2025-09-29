"""
Tests for the model template management system.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path

from evaluation_engine.config.templates import (
    ModelTemplateManager,
    ModelTemplate,
    TemplateVariable,
    ModelType,
    TemplateVariableType,
    TemplateValidationResult
)


class TestTemplateVariable:
    """Test cases for TemplateVariable class."""
    
    def test_template_variable_creation(self):
        """Test creating a template variable."""
        var = TemplateVariable(
            name="question",
            type=TemplateVariableType.STRING,
            description="The question to ask",
            required=True
        )
        
        assert var.name == "question"
        assert var.type == TemplateVariableType.STRING
        assert var.description == "The question to ask"
        assert var.required is True
        assert var.default_value is None
    
    def test_template_variable_with_default(self):
        """Test creating a template variable with default value."""
        var = TemplateVariable(
            name="temperature",
            type=TemplateVariableType.FLOAT,
            description="Model temperature",
            required=False,
            default_value=0.7
        )
        
        assert var.name == "temperature"
        assert var.default_value == 0.7
        assert var.required is False
    
    def test_template_variable_validation(self):
        """Test template variable validation."""
        with pytest.raises(ValueError, match="Template variable name cannot be empty"):
            TemplateVariable(
                name="",
                type=TemplateVariableType.STRING,
                description="Test"
            )
        
        with pytest.raises(ValueError, match="Template variable description cannot be empty"):
            TemplateVariable(
                name="test",
                type=TemplateVariableType.STRING,
                description=""
            )


class TestModelTemplate:
    """Test cases for ModelTemplate class."""
    
    def test_model_template_creation(self):
        """Test creating a model template."""
        variables = [
            TemplateVariable(
                name="question",
                type=TemplateVariableType.STRING,
                description="The question"
            )
        ]
        
        template = ModelTemplate(
            name="openai-default",
            model_type=ModelType.OPENAI,
            description="Default OpenAI template",
            prompt_template="Question: {question}\nAnswer:",
            system_prompt="You are a helpful assistant.",
            variables=variables
        )
        
        assert template.name == "openai-default"
        assert template.model_type == ModelType.OPENAI
        assert template.description == "Default OpenAI template"
        assert template.prompt_template == "Question: {question}\nAnswer:"
        assert template.system_prompt == "You are a helpful assistant."
        assert len(template.variables) == 1
        assert template.variables[0].name == "question"
    
    def test_model_template_validation(self):
        """Test model template validation."""
        with pytest.raises(ValueError, match="Template name cannot be empty"):
            ModelTemplate(
                name="",
                model_type=ModelType.OPENAI,
                description="Test",
                prompt_template="Test: {question}"
            )
        
        with pytest.raises(ValueError, match="Template description cannot be empty"):
            ModelTemplate(
                name="test",
                model_type=ModelType.OPENAI,
                description="",
                prompt_template="Test: {question}"
            )
        
        with pytest.raises(ValueError, match="Prompt template cannot be empty"):
            ModelTemplate(
                name="test",
                model_type=ModelType.OPENAI,
                description="Test template",
                prompt_template=""
            )


class TestTemplateValidationResult:
    """Test cases for TemplateValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test creating a validation result."""
        result = TemplateValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.missing_variables) == 0
        assert len(result.unused_variables) == 0
    
    def test_add_error(self):
        """Test adding an error to validation result."""
        result = TemplateValidationResult(is_valid=True)
        result.add_error("Test error")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
    
    def test_add_warning(self):
        """Test adding a warning to validation result."""
        result = TemplateValidationResult(is_valid=True)
        result.add_warning("Test warning")
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"


class TestModelTemplateManager:
    """Test cases for ModelTemplateManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ModelTemplateManager()
    
    def test_manager_initialization(self):
        """Test template manager initialization."""
        assert self.manager is not None
        assert hasattr(self.manager, '_templates')
        assert hasattr(self.manager, '_variable_pattern')
    
    def test_register_template(self):
        """Test registering a new template."""
        template = ModelTemplate(
            name="test-template",
            model_type=ModelType.OPENAI,
            description="Test template",
            prompt_template="Question: {question}\nAnswer:"
        )
        
        result = self.manager.register_template(template)
        assert result is True
        
        # Verify template was registered
        retrieved = self.manager.get_model_template("openai", "test-template")
        assert retrieved is not None
        assert retrieved.name == "test-template"
    
    def test_register_invalid_template(self):
        """Test registering an invalid template."""
        template = ModelTemplate(
            name="invalid-template",
            model_type=ModelType.OPENAI,
            description="Invalid template",
            prompt_template="Question: {question\nAnswer:"  # Missing closing brace
        )
        
        result = self.manager.register_template(template)
        assert result is False
    
    def test_get_model_template_exact_match(self):
        """Test getting a template with exact match."""
        template = ModelTemplate(
            name="specific-model",
            model_type=ModelType.OPENAI,
            description="Specific model template",
            prompt_template="Question: {question}\nAnswer:"
        )
        
        self.manager.register_template(template)
        
        retrieved = self.manager.get_model_template("openai", "specific-model")
        assert retrieved is not None
        assert retrieved.name == "specific-model"
    
    def test_get_model_template_default_fallback(self):
        """Test getting a template with default fallback."""
        # Register a default template
        default_template = ModelTemplate(
            name="default",
            model_type=ModelType.OPENAI,
            description="Default template",
            prompt_template="Question: {question}\nAnswer:"
        )
        
        self.manager.register_template(default_template)
        
        # Try to get a non-existent specific template
        retrieved = self.manager.get_model_template("openai", "non-existent")
        assert retrieved is not None
        assert retrieved.name == "default"
    
    def test_get_model_template_not_found(self):
        """Test getting a non-existent template."""
        retrieved = self.manager.get_model_template("unknown", "non-existent")
        assert retrieved is None
    
    def test_apply_prompt_template_success(self):
        """Test successful prompt template application."""
        template = "Question: {question}\nContext: {context}\nAnswer:"
        context = {
            "question": "What is AI?",
            "context": "Artificial Intelligence context"
        }
        
        result = self.manager.apply_prompt_template(template, context)
        expected = "Question: What is AI?\nContext: Artificial Intelligence context\nAnswer:"
        assert result == expected
    
    def test_apply_prompt_template_missing_variable(self):
        """Test prompt template application with missing variable."""
        template = "Question: {question}\nContext: {context}\nAnswer:"
        context = {"question": "What is AI?"}  # Missing 'context'
        
        with pytest.raises(ValueError, match="Missing required template variables"):
            self.manager.apply_prompt_template(template, context)
    
    def test_validate_template_syntax_valid(self):
        """Test validating valid template syntax."""
        template = "Question: {question}\nAnswer: {answer}"
        
        result = self.manager.validate_template_syntax(template)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_template_syntax_empty(self):
        """Test validating empty template."""
        result = self.manager.validate_template_syntax("")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Template cannot be empty" in result.errors[0]
    
    def test_validate_template_syntax_unbalanced_braces(self):
        """Test validating template with unbalanced braces."""
        template = "Question: {question\nAnswer: {answer}"  # Missing closing brace
        
        result = self.manager.validate_template_syntax(template)
        assert result.is_valid is False
        assert any("Unbalanced braces" in error for error in result.errors)
    
    def test_validate_template_syntax_empty_variable(self):
        """Test validating template with empty variable name."""
        template = "Question: {}\nAnswer: {answer}"
        
        result = self.manager.validate_template_syntax(template)
        assert result.is_valid is False
        assert any("Empty variable name" in error for error in result.errors)
    
    def test_validate_template_syntax_nested_braces(self):
        """Test validating template with nested braces."""
        template = "Question: {question{nested}}\nAnswer:"
        
        result = self.manager.validate_template_syntax(template)
        assert result.is_valid is False
        assert any("Nested braces are not supported" in error for error in result.errors)
    
    def test_list_templates_all(self):
        """Test listing all templates."""
        template1 = ModelTemplate(
            name="template1",
            model_type=ModelType.OPENAI,
            description="Template 1",
            prompt_template="Test: {question}"
        )
        
        template2 = ModelTemplate(
            name="template2",
            model_type=ModelType.ANTHROPIC,
            description="Template 2",
            prompt_template="Test: {question}"
        )
        
        self.manager.register_template(template1)
        self.manager.register_template(template2)
        
        templates = self.manager.list_templates()
        assert "openai:template1" in templates
        assert "anthropic:template2" in templates
    
    def test_list_templates_filtered(self):
        """Test listing templates filtered by model type."""
        template1 = ModelTemplate(
            name="template1",
            model_type=ModelType.OPENAI,
            description="Template 1",
            prompt_template="Test: {question}"
        )
        
        template2 = ModelTemplate(
            name="template2",
            model_type=ModelType.ANTHROPIC,
            description="Template 2",
            prompt_template="Test: {question}"
        )
        
        self.manager.register_template(template1)
        self.manager.register_template(template2)
        
        openai_templates = self.manager.list_templates("openai")
        assert "openai:template1" in openai_templates
        assert "anthropic:template2" not in openai_templates
    
    def test_save_and_load_template_json(self):
        """Test saving and loading template from JSON file."""
        template = ModelTemplate(
            name="test-template",
            model_type=ModelType.OPENAI,
            description="Test template",
            prompt_template="Question: {question}\nAnswer:",
            system_prompt="You are helpful.",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The question"
                )
            ]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save template
            result = self.manager.save_template_to_file(template, temp_path)
            assert result is True
            
            # Load template
            loaded_template = self.manager.load_template_from_file(temp_path)
            assert loaded_template is not None
            assert loaded_template.name == template.name
            assert loaded_template.model_type == template.model_type
            assert loaded_template.description == template.description
            assert loaded_template.prompt_template == template.prompt_template
            assert loaded_template.system_prompt == template.system_prompt
            assert len(loaded_template.variables) == 1
            assert loaded_template.variables[0].name == "question"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_save_and_load_template_yaml(self):
        """Test saving and loading template from YAML file."""
        template = ModelTemplate(
            name="test-template",
            model_type=ModelType.ANTHROPIC,
            description="Test template",
            prompt_template="Human: {question}\n\nAssistant:",
            variables=[
                TemplateVariable(
                    name="question",
                    type=TemplateVariableType.STRING,
                    description="The question"
                )
            ]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save template
            result = self.manager.save_template_to_file(template, temp_path)
            assert result is True
            
            # Load template
            loaded_template = self.manager.load_template_from_file(temp_path)
            assert loaded_template is not None
            assert loaded_template.name == template.name
            assert loaded_template.model_type == template.model_type
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_load_template_from_nonexistent_file(self):
        """Test loading template from non-existent file."""
        result = self.manager.load_template_from_file("/nonexistent/path.json")
        assert result is None
    
    def test_builtin_openai_templates(self):
        """Test that built-in OpenAI templates are loaded."""
        # Test default OpenAI template
        template = self.manager.get_model_template("openai", "default")
        assert template is not None
        assert template.name == "default"
        assert template.model_type == ModelType.OPENAI
        assert "question" in template.prompt_template
        
        # Test Q&A template
        qa_template = self.manager.get_model_template("openai", "qa")
        assert qa_template is not None
        assert qa_template.name == "qa"
        assert "Question:" in qa_template.prompt_template
        assert "Answer:" in qa_template.prompt_template
        
        # Test few-shot template
        fewshot_template = self.manager.get_model_template("openai", "fewshot")
        assert fewshot_template is not None
        assert fewshot_template.name == "fewshot"
        assert "examples" in fewshot_template.prompt_template
    
    def test_builtin_anthropic_templates(self):
        """Test that built-in Anthropic templates are loaded."""
        # Test default Claude template
        template = self.manager.get_model_template("anthropic", "default")
        assert template is not None
        assert template.name == "default"
        assert template.model_type == ModelType.ANTHROPIC
        assert "Human:" in template.prompt_template
        assert "Assistant:" in template.prompt_template
        
        # Test conversation template
        conv_template = self.manager.get_model_template("anthropic", "conversation")
        assert conv_template is not None
        assert conv_template.name == "conversation"
        assert "conversation_history" in conv_template.prompt_template
        
        # Test analysis template
        analysis_template = self.manager.get_model_template("anthropic", "analysis")
        assert analysis_template is not None
        assert analysis_template.name == "analysis"
        assert "analyze" in analysis_template.prompt_template.lower()
    
    def test_builtin_huggingface_templates(self):
        """Test that built-in Hugging Face templates are loaded."""
        # Test default HF template
        template = self.manager.get_model_template("huggingface", "default")
        assert template is not None
        assert template.name == "default"
        assert template.model_type == ModelType.HUGGINGFACE
        
        # Test Llama-2 chat template
        llama_template = self.manager.get_model_template("huggingface", "llama2-chat")
        assert llama_template is not None
        assert llama_template.name == "llama2-chat"
        assert "[INST]" in llama_template.prompt_template
        assert "[/INST]" in llama_template.prompt_template
        
        # Test Mistral template
        mistral_template = self.manager.get_model_template("huggingface", "mistral-instruct")
        assert mistral_template is not None
        assert mistral_template.name == "mistral-instruct"
        
        # Test CodeLlama template
        code_template = self.manager.get_model_template("huggingface", "codellama")
        assert code_template is not None
        assert code_template.name == "codellama"
        assert "code" in code_template.description.lower()
    
    def test_get_builtin_template_names(self):
        """Test getting built-in template names."""
        # Test all templates
        all_templates = self.manager.get_builtin_template_names()
        assert "openai:default" in all_templates
        assert "anthropic:default" in all_templates
        assert "huggingface:default" in all_templates
        
        # Test filtered by model type
        openai_templates = self.manager.get_builtin_template_names("openai")
        assert "openai:default" in openai_templates
        assert "openai:qa" in openai_templates
        assert "anthropic:default" not in openai_templates
        
        anthropic_templates = self.manager.get_builtin_template_names("anthropic")
        assert "anthropic:default" in anthropic_templates
        assert "anthropic:conversation" in anthropic_templates
        assert "openai:default" not in anthropic_templates
    
    def test_register_custom_template(self):
        """Test registering a custom template from dictionary."""
        template_data = {
            "name": "custom-template",
            "model_type": "openai",
            "description": "Custom test template",
            "prompt_template": "Custom: {input}",
            "system_prompt": "You are a custom assistant.",
            "variables": [
                {
                    "name": "input",
                    "type": "string",
                    "description": "Custom input",
                    "required": True
                }
            ],
            "metadata": {
                "custom": True
            }
        }
        
        result = self.manager.register_custom_template(template_data)
        assert result is True
        
        # Verify template was registered
        template = self.manager.get_model_template("openai", "custom-template")
        assert template is not None
        assert template.name == "custom-template"
        assert template.description == "Custom test template"
        assert template.metadata.get("custom") is True
    
    def test_register_invalid_custom_template(self):
        """Test registering an invalid custom template."""
        invalid_template_data = {
            "name": "invalid-template",
            "model_type": "invalid_type",  # Invalid model type
            "description": "Invalid template",
            "prompt_template": "Test: {input}"
        }
        
        result = self.manager.register_custom_template(invalid_template_data)
        assert result is False
    
    def test_get_template_metadata(self):
        """Test getting template metadata."""
        # Test existing template
        metadata = self.manager.get_template_metadata("openai", "default")
        assert metadata is not None
        assert "supports_system_prompt" in metadata
        assert metadata["supports_system_prompt"] is True
        
        # Test non-existent template
        metadata = self.manager.get_template_metadata("unknown", "non-existent")
        assert metadata is None
    
    def test_apply_model_template(self):
        """Test applying a complete model template."""
        context = {"question": "What is artificial intelligence?"}
        
        # Test OpenAI template
        result = self.manager.apply_model_template("openai", "default", context)
        assert result is not None
        assert "prompt" in result
        assert "system_prompt" in result
        assert "What is artificial intelligence?" in result["prompt"]
        assert "helpful assistant" in result["system_prompt"]
        
        # Test template with missing context
        incomplete_context = {}
        result = self.manager.apply_model_template("openai", "default", incomplete_context)
        assert result is None  # Should fail due to missing required variable
    
    def test_apply_model_template_with_variable_system_prompt(self):
        """Test applying template with variables in system prompt."""
        # Create a template with variables in system prompt
        template = ModelTemplate(
            name="variable-system",
            model_type=ModelType.OPENAI,
            description="Template with variable system prompt",
            prompt_template="Question: {question}",
            system_prompt="You are a {role}. {instructions}",
            variables=[
                TemplateVariable("question", TemplateVariableType.STRING, "The question"),
                TemplateVariable("role", TemplateVariableType.STRING, "The assistant role"),
                TemplateVariable("instructions", TemplateVariableType.STRING, "Additional instructions")
            ]
        )
        
        self.manager.register_template(template)
        
        context = {
            "question": "What is AI?",
            "role": "helpful AI assistant",
            "instructions": "Be concise and accurate."
        }
        
        result = self.manager.apply_model_template("openai", "variable-system", context)
        assert result is not None
        assert "What is AI?" in result["prompt"]
        assert "helpful AI assistant" in result["system_prompt"]
        assert "Be concise and accurate." in result["system_prompt"]
    
    def test_format_for_model_type_openai(self):
        """Test formatting for OpenAI model type."""
        prompt = "What is AI?"
        system_prompt = "You are helpful."
        
        formatted = self.manager.format_for_model_type("openai", prompt, system_prompt)
        # OpenAI handles system prompts separately, so should return just the prompt
        assert formatted == prompt
    
    def test_format_for_model_type_anthropic(self):
        """Test formatting for Anthropic model type."""
        prompt = "Human: What is AI?\n\nAssistant:"
        system_prompt = "You are Claude."
        
        formatted = self.manager.format_for_model_type("anthropic", prompt, system_prompt)
        assert "System: You are Claude." in formatted
        assert "Human: What is AI?" in formatted
    
    def test_format_for_model_type_huggingface(self):
        """Test formatting for Hugging Face model type."""
        # Test with already formatted Llama-2 style prompt
        llama_prompt = "<s>[INST] <<SYS>>\nYou are helpful.\n<</SYS>>\n\nWhat is AI? [/INST]"
        formatted = self.manager.format_for_model_type("huggingface", llama_prompt, "You are helpful.")
        assert formatted == llama_prompt  # Should not modify already formatted prompt
        
        # Test with plain prompt
        plain_prompt = "What is AI?"
        system_prompt = "You are helpful."
        formatted = self.manager.format_for_model_type("huggingface", plain_prompt, system_prompt)
        assert "System: You are helpful." in formatted
        assert "What is AI?" in formatted
    
    def test_validate_template_context_success(self):
        """Test successful template context validation."""
        template = ModelTemplate(
            name="test-validation",
            model_type=ModelType.OPENAI,
            description="Test template for validation",
            prompt_template="Question: {question}\nContext: {context}",
            variables=[
                TemplateVariable("question", TemplateVariableType.STRING, "The question", required=True),
                TemplateVariable("context", TemplateVariableType.STRING, "The context", required=False)
            ]
        )
        
        context = {
            "question": "What is AI?",
            "context": "Machine learning context"
        }
        
        result = self.manager.validate_template_context(template, context)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.missing_variables) == 0
    
    def test_validate_template_context_missing_required(self):
        """Test template context validation with missing required variable."""
        template = ModelTemplate(
            name="test-validation",
            model_type=ModelType.OPENAI,
            description="Test template for validation",
            prompt_template="Question: {question}",
            variables=[
                TemplateVariable("question", TemplateVariableType.STRING, "The question", required=True)
            ]
        )
        
        context = {}  # Missing required 'question'
        
        result = self.manager.validate_template_context(template, context)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "question" in result.missing_variables
        assert "Required variable 'question' is missing" in result.errors[0]
    
    def test_validate_template_context_unused_variables(self):
        """Test template context validation with unused variables."""
        template = ModelTemplate(
            name="test-validation",
            model_type=ModelType.OPENAI,
            description="Test template for validation",
            prompt_template="Question: {question}",
            variables=[
                TemplateVariable("question", TemplateVariableType.STRING, "The question", required=True)
            ]
        )
        
        context = {
            "question": "What is AI?",
            "unused_var": "This is not used"
        }
        
        result = self.manager.validate_template_context(template, context)
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert "unused_var" in result.unused_variables
        assert "not used in template" in result.warnings[0]
    
    def test_validate_template_context_wrong_type(self):
        """Test template context validation with wrong variable type."""
        template = ModelTemplate(
            name="test-validation",
            model_type=ModelType.OPENAI,
            description="Test template for validation",
            prompt_template="Question: {question}\nNumber: {number}",
            variables=[
                TemplateVariable("question", TemplateVariableType.STRING, "The question", required=True),
                TemplateVariable("number", TemplateVariableType.INTEGER, "A number", required=True)
            ]
        )
        
        context = {
            "question": "What is AI?",
            "number": "not a number"  # Wrong type
        }
        
        result = self.manager.validate_template_context(template, context)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "incorrect type" in result.errors[0]
    
    def test_create_template_context(self):
        """Test creating template context from keyword arguments."""
        context = self.manager.create_template_context(
            question="What is AI?",
            temperature=0.7,
            max_tokens=100
        )
        
        assert context["question"] == "What is AI?"
        assert context["temperature"] == 0.7
        assert context["max_tokens"] == 100
    
    def test_get_template_variables(self):
        """Test getting template variables."""
        # Test existing template
        variables = self.manager.get_template_variables("openai", "default")
        assert len(variables) > 0
        assert any(var.name == "question" for var in variables)
        
        # Test non-existent template
        variables = self.manager.get_template_variables("unknown", "non-existent")
        assert len(variables) == 0
    
    def test_variable_type_validation(self):
        """Test variable type validation helper method."""
        # Test string validation
        assert self.manager._validate_variable_type("hello", TemplateVariableType.STRING) is True
        assert self.manager._validate_variable_type(123, TemplateVariableType.STRING) is False
        
        # Test integer validation
        assert self.manager._validate_variable_type(42, TemplateVariableType.INTEGER) is True
        assert self.manager._validate_variable_type("42", TemplateVariableType.INTEGER) is False
        
        # Test float validation
        assert self.manager._validate_variable_type(3.14, TemplateVariableType.FLOAT) is True
        assert self.manager._validate_variable_type(42, TemplateVariableType.FLOAT) is True  # int is valid for float
        assert self.manager._validate_variable_type("3.14", TemplateVariableType.FLOAT) is False
        
        # Test boolean validation
        assert self.manager._validate_variable_type(True, TemplateVariableType.BOOLEAN) is True
        assert self.manager._validate_variable_type(1, TemplateVariableType.BOOLEAN) is False
        
        # Test list validation
        assert self.manager._validate_variable_type([1, 2, 3], TemplateVariableType.LIST) is True
        assert self.manager._validate_variable_type("list", TemplateVariableType.LIST) is False
        
        # Test dict validation
        assert self.manager._validate_variable_type({"key": "value"}, TemplateVariableType.DICT) is True
        assert self.manager._validate_variable_type("dict", TemplateVariableType.DICT) is False