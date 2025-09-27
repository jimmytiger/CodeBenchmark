#!/usr/bin/env python3
"""
Multi-language Dataset Generator for AI Evaluation Engine

This tool generates datasets with multi-language support and cross-language
evaluation capabilities, expanding beyond single-language scenarios.
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProgrammingLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    SQL = "sql"
    SHELL = "shell"

class NaturalLanguage(Enum):
    ENGLISH = "en"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    KOREAN = "ko"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ITALIAN = "it"

@dataclass
class MultilingualProblem:
    """Multi-language problem with translations"""
    id: str
    base_language: str
    natural_language: str
    scenario: str
    difficulty: str
    context_mode: str
    translations: Dict[str, Dict[str, Any]]  # lang -> {prompt, reference, tests}
    cross_language_pairs: List[Tuple[str, str]]  # (source_lang, target_lang)
    metadata: Dict[str, Any]

class MultilingualDatasetGenerator:
    """Generator for multi-language datasets"""
    
    def __init__(self, base_path: str = "lm_eval/tasks"):
        self.base_path = Path(base_path)
        self.language_configs = self._load_language_configurations()
        self.translation_templates = self._load_translation_templates()
        self.cross_language_scenarios = self._define_cross_language_scenarios()
        
    def generate_multilingual_dataset(self, scenario: str, count: int = 100, 
                                    target_languages: List[str] = None,
                                    natural_languages: List[str] = None) -> List[MultilingualProblem]:
        """Generate multilingual dataset for a scenario"""
        if target_languages is None:
            target_languages = ["python", "javascript", "java", "cpp", "go"]
        
        if natural_languages is None:
            natural_languages = ["en", "zh", "es"]
        
        logger.info(f"Generating multilingual dataset for {scenario}")
        logger.info(f"Target programming languages: {target_languages}")
        logger.info(f"Natural languages: {natural_languages}")
        
        problems = []
        
        for i in range(count):
            problem = self._generate_multilingual_problem(
                scenario, i, target_languages, natural_languages
            )
            problems.append(problem)
        
        return problems
    
    def generate_cross_language_evaluation_dataset(self, count: int = 50) -> List[MultilingualProblem]:
        """Generate dataset specifically for cross-language evaluation"""
        logger.info("Generating cross-language evaluation dataset")
        
        problems = []
        cross_lang_pairs = [
            ("python", "javascript"),
            ("python", "java"),
            ("javascript", "typescript"),
            ("java", "kotlin"),
            ("cpp", "rust"),
            ("python", "go"),
            ("javascript", "python"),
            ("java", "cpp")
        ]
        
        for i in range(count):
            source_lang, target_lang = random.choice(cross_lang_pairs)
            problem = self._generate_cross_language_problem(i, source_lang, target_lang)
            problems.append(problem)
        
        return problems
    
    def _generate_multilingual_problem(self, scenario: str, index: int, 
                                     target_languages: List[str],
                                     natural_languages: List[str]) -> MultilingualProblem:
        """Generate a single multilingual problem"""
        problem_id = f"ml_{scenario}_{index:04d}"
        base_language = random.choice(target_languages)
        natural_language = random.choice(natural_languages)
        difficulty = random.choice(["simple", "intermediate", "complex"])
        context_mode = random.choice(["minimal_context", "full_context", "domain_context"])
        
        # Generate base problem content
        base_content = self._generate_base_problem_content(scenario, difficulty, base_language, natural_language, index)
        
        # Generate translations for other languages
        translations = {}
        for lang in target_languages:
            if lang != base_language:
                translation = self._translate_problem_content(base_content, base_language, lang, scenario)
                translations[lang] = translation
        
        # Add base language content
        translations[base_language] = base_content
        
        # Generate cross-language pairs for evaluation
        cross_language_pairs = []
        for source_lang in target_languages:
            for target_lang in target_languages:
                if source_lang != target_lang and self._is_valid_translation_pair(source_lang, target_lang):
                    cross_language_pairs.append((source_lang, target_lang))
        
        return MultilingualProblem(
            id=problem_id,
            base_language=base_language,
            natural_language=natural_language,
            scenario=scenario,
            difficulty=difficulty,
            context_mode=context_mode,
            translations=translations,
            cross_language_pairs=cross_language_pairs,
            metadata={
                "generated_at": self._get_timestamp(),
                "author": "multilingual_generator",
                "license": "MIT",
                "supported_languages": target_languages,
                "natural_language": natural_language,
                "cross_language_evaluation": True
            }
        )
    
    def _generate_cross_language_problem(self, index: int, source_lang: str, target_lang: str) -> MultilingualProblem:
        """Generate a problem specifically for cross-language translation"""
        problem_id = f"xl_{source_lang}_{target_lang}_{index:04d}"
        scenario = "code_translation"
        difficulty = random.choice(["simple", "intermediate", "complex"])
        
        # Generate source code
        source_content = self._generate_translation_source_code(source_lang, difficulty, index)
        
        # Generate target code
        target_content = self._translate_code_content(source_content, source_lang, target_lang)
        
        translations = {
            source_lang: {
                "prompt": f"Translate the following {source_lang} code to {target_lang}:",
                "source_code": source_content["code"],
                "reference": [source_content["code"]],
                "tests": source_content["tests"]
            },
            target_lang: {
                "prompt": f"Translated {target_lang} code:",
                "reference": [target_content["code"]],
                "tests": target_content["tests"]
            }
        }
        
        return MultilingualProblem(
            id=problem_id,
            base_language=source_lang,
            natural_language="en",
            scenario=scenario,
            difficulty=difficulty,
            context_mode="minimal_context",
            translations=translations,
            cross_language_pairs=[(source_lang, target_lang)],
            metadata={
                "generated_at": self._get_timestamp(),
                "author": "cross_language_generator",
                "license": "MIT",
                "translation_pair": f"{source_lang}->{target_lang}",
                "cross_language_evaluation": True
            }
        )
    
    def _generate_base_problem_content(self, scenario: str, difficulty: str, 
                                     language: str, natural_language: str, index: int) -> Dict[str, Any]:
        """Generate base problem content"""
        content_generators = {
            "code_completion": self._generate_code_completion_multilingual,
            "function_generation": self._generate_function_generation_multilingual,
            "algorithm_implementation": self._generate_algorithm_implementation_multilingual,
            "bug_fix": self._generate_bug_fix_multilingual,
            "api_design": self._generate_api_design_multilingual
        }
        
        generator = content_generators.get(scenario, self._generate_default_multilingual_content)
        return generator(difficulty, language, natural_language, index)
    
    def _generate_code_completion_multilingual(self, difficulty: str, language: str, 
                                             natural_language: str, index: int) -> Dict[str, Any]:
        """Generate multilingual code completion content"""
        templates = {
            "python": {
                "simple": {
                    "en": "Complete the function to calculate the sum of numbers in a list",
                    "zh": "完成函数以计算列表中数字的总和",
                    "es": "Completa la función para calcular la suma de números en una lista",
                    "code": "def sum_numbers(numbers):\n    total = 0\n    for num in numbers:\n        total += num\n    return total"
                },
                "intermediate": {
                    "en": "Complete the binary search implementation",
                    "zh": "完成二分搜索的实现",
                    "es": "Completa la implementación de búsqueda binaria",
                    "code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1"
                }
            },
            "javascript": {
                "simple": {
                    "en": "Complete the function to reverse a string",
                    "zh": "完成函数以反转字符串",
                    "es": "Completa la función para invertir una cadena",
                    "code": "function reverseString(str) {\n    return str.split('').reverse().join('');\n}"
                },
                "intermediate": {
                    "en": "Complete the async function to fetch user data",
                    "zh": "完成异步函数以获取用户数据",
                    "es": "Completa la función asíncrona para obtener datos de usuario",
                    "code": "async function fetchUserData(userId) {\n    try {\n        const response = await fetch(`/api/users/${userId}`);\n        return await response.json();\n    } catch (error) {\n        console.error('Error fetching user data:', error);\n        throw error;\n    }\n}"
                }
            },
            "java": {
                "simple": {
                    "en": "Complete the method to find the maximum value in an array",
                    "zh": "完成方法以找到数组中的最大值",
                    "es": "Completa el método para encontrar el valor máximo en un array",
                    "code": "public static int findMax(int[] arr) {\n    int max = arr[0];\n    for (int i = 1; i < arr.length; i++) {\n        if (arr[i] > max) {\n            max = arr[i];\n        }\n    }\n    return max;\n}"
                }
            }
        }
        
        lang_templates = templates.get(language, templates["python"])
        difficulty_templates = lang_templates.get(difficulty, lang_templates["simple"])
        
        prompt = difficulty_templates.get(natural_language, difficulty_templates["en"])
        code = difficulty_templates["code"]
        
        return {
            "prompt": prompt,
            "reference": [code],
            "tests": [{"type": "unit", "file": f"tests/test_ml_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_ml_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _generate_function_generation_multilingual(self, difficulty: str, language: str, 
                                                 natural_language: str, index: int) -> Dict[str, Any]:
        """Generate multilingual function generation content"""
        function_specs = {
            "simple": {
                "en": "Write a function to check if a number is prime",
                "zh": "编写一个函数来检查数字是否为质数",
                "es": "Escribe una función para verificar si un número es primo"
            },
            "intermediate": {
                "en": "Implement a function to merge two sorted arrays",
                "zh": "实现一个函数来合并两个已排序的数组",
                "es": "Implementa una función para fusionar dos arrays ordenados"
            },
            "complex": {
                "en": "Create a function to implement a LRU cache",
                "zh": "创建一个函数来实现LRU缓存",
                "es": "Crea una función para implementar una caché LRU"
            }
        }
        
        prompt = function_specs[difficulty].get(natural_language, function_specs[difficulty]["en"])
        reference_code = self._generate_reference_code(language, difficulty, "function_generation")
        
        return {
            "prompt": prompt,
            "reference": [reference_code],
            "tests": [{"type": "unit", "file": f"tests/test_func_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_func_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _generate_algorithm_implementation_multilingual(self, difficulty: str, language: str, 
                                                      natural_language: str, index: int) -> Dict[str, Any]:
        """Generate multilingual algorithm implementation content"""
        algorithm_specs = {
            "simple": {
                "en": "Implement bubble sort algorithm",
                "zh": "实现冒泡排序算法",
                "es": "Implementa el algoritmo de ordenamiento burbuja"
            },
            "intermediate": {
                "en": "Implement quicksort algorithm",
                "zh": "实现快速排序算法",
                "es": "Implementa el algoritmo quicksort"
            },
            "complex": {
                "en": "Implement Dijkstra's shortest path algorithm",
                "zh": "实现Dijkstra最短路径算法",
                "es": "Implementa el algoritmo de camino más corto de Dijkstra"
            }
        }
        
        prompt = algorithm_specs[difficulty].get(natural_language, algorithm_specs[difficulty]["en"])
        reference_code = self._generate_reference_code(language, difficulty, "algorithm_implementation")
        
        return {
            "prompt": prompt,
            "reference": [reference_code],
            "tests": [{"type": "unit", "file": f"tests/test_algo_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_algo_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _generate_bug_fix_multilingual(self, difficulty: str, language: str, 
                                     natural_language: str, index: int) -> Dict[str, Any]:
        """Generate multilingual bug fix content"""
        bug_descriptions = {
            "simple": {
                "en": "Fix the off-by-one error in this loop",
                "zh": "修复此循环中的偏移错误",
                "es": "Corrige el error de desplazamiento en este bucle"
            },
            "intermediate": {
                "en": "Fix the null pointer exception in this code",
                "zh": "修复此代码中的空指针异常",
                "es": "Corrige la excepción de puntero nulo en este código"
            },
            "complex": {
                "en": "Fix the race condition in this concurrent code",
                "zh": "修复此并发代码中的竞态条件",
                "es": "Corrige la condición de carrera en este código concurrente"
            }
        }
        
        prompt = bug_descriptions[difficulty].get(natural_language, bug_descriptions[difficulty]["en"])
        reference_code = self._generate_reference_code(language, difficulty, "bug_fix")
        
        return {
            "prompt": prompt,
            "reference": [reference_code],
            "tests": [{"type": "unit", "file": f"tests/test_bug_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_bug_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _generate_api_design_multilingual(self, difficulty: str, language: str, 
                                        natural_language: str, index: int) -> Dict[str, Any]:
        """Generate multilingual API design content"""
        api_specs = {
            "simple": {
                "en": "Design a REST API for user registration",
                "zh": "为用户注册设计REST API",
                "es": "Diseña una API REST para registro de usuarios"
            },
            "intermediate": {
                "en": "Design a REST API with authentication and authorization",
                "zh": "设计具有身份验证和授权的REST API",
                "es": "Diseña una API REST con autenticación y autorización"
            },
            "complex": {
                "en": "Design a microservices API with service discovery",
                "zh": "设计具有服务发现的微服务API",
                "es": "Diseña una API de microservicios con descubrimiento de servicios"
            }
        }
        
        prompt = api_specs[difficulty].get(natural_language, api_specs[difficulty]["en"])
        reference_code = self._generate_reference_code(language, difficulty, "api_design")
        
        return {
            "prompt": prompt,
            "reference": [reference_code],
            "tests": [{"type": "integration", "file": f"tests/test_api_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_api_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _generate_default_multilingual_content(self, difficulty: str, language: str, 
                                             natural_language: str, index: int) -> Dict[str, Any]:
        """Generate default multilingual content"""
        prompts = {
            "en": f"Solve this {difficulty} programming problem",
            "zh": f"解决这个{difficulty}编程问题",
            "es": f"Resuelve este problema de programación {difficulty}"
        }
        
        prompt = prompts.get(natural_language, prompts["en"])
        reference_code = f"# {difficulty.capitalize()} solution in {language}"
        
        return {
            "prompt": prompt,
            "reference": [reference_code],
            "tests": [{"type": "unit", "file": f"tests/test_default_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_default_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _translate_problem_content(self, base_content: Dict[str, Any], 
                                 source_lang: str, target_lang: str, scenario: str) -> Dict[str, Any]:
        """Translate problem content from source language to target language"""
        # This is a simplified translation - in production, you'd use more sophisticated translation
        translated_reference = self._translate_code(base_content["reference"][0], source_lang, target_lang)
        
        return {
            "prompt": base_content["prompt"],  # Keep prompt in natural language
            "reference": [translated_reference],
            "tests": [{"type": "unit", "file": f"tests/test_translated.{self._get_file_extension(target_lang)}", 
                      "cmd": f"{self._get_test_command(target_lang)} tests/test_translated.{self._get_file_extension(target_lang)}"}]
        }
    
    def _translate_code(self, code: str, source_lang: str, target_lang: str) -> str:
        """Translate code from source language to target language"""
        # Simplified code translation - in production, use more sophisticated methods
        translation_rules = {
            ("python", "javascript"): [
                ("def ", "function "),
                (":", " {"),
                ("    ", "  "),
                ("True", "true"),
                ("False", "false"),
                ("None", "null")
            ],
            ("javascript", "python"): [
                ("function ", "def "),
                (" {", ":"),
                ("  ", "    "),
                ("true", "True"),
                ("false", "False"),
                ("null", "None")
            ],
            ("python", "java"): [
                ("def ", "public static "),
                (":", " {"),
                ("    ", "    "),
                ("True", "true"),
                ("False", "false")
            ]
        }
        
        rules = translation_rules.get((source_lang, target_lang), [])
        translated_code = code
        
        for old, new in rules:
            translated_code = translated_code.replace(old, new)
        
        return translated_code
    
    def _generate_translation_source_code(self, language: str, difficulty: str, index: int) -> Dict[str, Any]:
        """Generate source code for translation scenarios"""
        code_templates = {
            "python": {
                "simple": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "intermediate": "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
                "complex": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef inorder_traversal(root):\n    result = []\n    def inorder(node):\n        if node:\n            inorder(node.left)\n            result.append(node.val)\n            inorder(node.right)\n    inorder(root)\n    return result"
            },
            "javascript": {
                "simple": "function factorial(n) {\n    if (n <= 1) return 1;\n    return n * factorial(n - 1);\n}",
                "intermediate": "function mergeSort(arr) {\n    if (arr.length <= 1) return arr;\n    const mid = Math.floor(arr.length / 2);\n    const left = mergeSort(arr.slice(0, mid));\n    const right = mergeSort(arr.slice(mid));\n    return merge(left, right);\n}",
                "complex": "class LRUCache {\n    constructor(capacity) {\n        this.capacity = capacity;\n        this.cache = new Map();\n    }\n    \n    get(key) {\n        if (this.cache.has(key)) {\n            const value = this.cache.get(key);\n            this.cache.delete(key);\n            this.cache.set(key, value);\n            return value;\n        }\n        return -1;\n    }\n}"
            }
        }
        
        code = code_templates.get(language, code_templates["python"])[difficulty]
        
        return {
            "code": code,
            "tests": [{"type": "unit", "file": f"tests/test_source_{index:04d}.{self._get_file_extension(language)}", 
                      "cmd": f"{self._get_test_command(language)} tests/test_source_{index:04d}.{self._get_file_extension(language)}"}]
        }
    
    def _translate_code_content(self, source_content: Dict[str, Any], source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate code content to target language"""
        translated_code = self._translate_code(source_content["code"], source_lang, target_lang)
        
        return {
            "code": translated_code,
            "tests": [{"type": "unit", "file": f"tests/test_target.{self._get_file_extension(target_lang)}", 
                      "cmd": f"{self._get_test_command(target_lang)} tests/test_target.{self._get_file_extension(target_lang)}"}]
        }
    
    def _generate_reference_code(self, language: str, difficulty: str, scenario: str) -> str:
        """Generate reference code for given parameters"""
        # Simplified reference code generation
        return f"# {difficulty.capitalize()} {scenario} implementation in {language}\n# Generated reference code"
    
    def _is_valid_translation_pair(self, source_lang: str, target_lang: str) -> bool:
        """Check if translation pair is valid"""
        # Define valid translation pairs
        valid_pairs = {
            ("python", "javascript"), ("python", "java"), ("python", "go"),
            ("javascript", "typescript"), ("javascript", "python"),
            ("java", "kotlin"), ("java", "scala"), ("java", "cpp"),
            ("cpp", "rust"), ("cpp", "c"), ("go", "rust"),
            ("csharp", "java"), ("php", "python"), ("ruby", "python")
        }
        
        return (source_lang, target_lang) in valid_pairs
    
    def _load_language_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load language-specific configurations"""
        return {
            "python": {"extension": "py", "test_command": "python -m pytest", "comment": "#"},
            "javascript": {"extension": "js", "test_command": "node", "comment": "//"},
            "typescript": {"extension": "ts", "test_command": "tsc && node", "comment": "//"},
            "java": {"extension": "java", "test_command": "javac && java", "comment": "//"},
            "cpp": {"extension": "cpp", "test_command": "g++ -o test && ./test", "comment": "//"},
            "go": {"extension": "go", "test_command": "go test", "comment": "//"},
            "rust": {"extension": "rs", "test_command": "cargo test", "comment": "//"},
            "sql": {"extension": "sql", "test_command": "psql -d test_db -f", "comment": "--"}
        }
    
    def _load_translation_templates(self) -> Dict[str, Dict[str, str]]:
        """Load translation templates for different language pairs"""
        return {
            "python_to_javascript": {
                "function_def": "def {name}({params}): -> function {name}({params}) {{",
                "return": "return {value} -> return {value};",
                "if_statement": "if {condition}: -> if ({condition}) {{",
                "for_loop": "for {var} in {iterable}: -> for (let {var} of {iterable}) {{"
            },
            "javascript_to_python": {
                "function_def": "function {name}({params}) {{ -> def {name}({params}):",
                "return": "return {value}; -> return {value}",
                "if_statement": "if ({condition}) {{ -> if {condition}:",
                "for_loop": "for (let {var} of {iterable}) {{ -> for {var} in {iterable}:"
            }
        }
    
    def _define_cross_language_scenarios(self) -> List[Dict[str, Any]]:
        """Define scenarios specifically for cross-language evaluation"""
        return [
            {
                "name": "algorithm_translation",
                "description": "Translate algorithm implementations between languages",
                "complexity": "intermediate",
                "focus": "algorithmic_logic"
            },
            {
                "name": "data_structure_translation",
                "description": "Translate data structure implementations",
                "complexity": "complex",
                "focus": "data_structures"
            },
            {
                "name": "api_translation",
                "description": "Translate API implementations between frameworks",
                "complexity": "complex",
                "focus": "api_design"
            },
            {
                "name": "utility_function_translation",
                "description": "Translate utility functions",
                "complexity": "simple",
                "focus": "basic_programming"
            }
        ]
    
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language"""
        config = self.language_configs.get(language, {"extension": "txt"})
        return config["extension"]
    
    def _get_test_command(self, language: str) -> str:
        """Get test command for language"""
        config = self.language_configs.get(language, {"test_command": "echo"})
        return config["test_command"]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_multilingual_datasets(self, problems: List[MultilingualProblem], output_dir: str = None):
        """Save multilingual datasets to files"""
        if output_dir:
            base_path = Path(output_dir)
        else:
            base_path = self.base_path / "multilingual_datasets"
        
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Group problems by scenario and natural language
        grouped_problems = {}
        for problem in problems:
            key = f"{problem.scenario}_{problem.natural_language}"
            if key not in grouped_problems:
                grouped_problems[key] = []
            grouped_problems[key].append(problem)
        
        # Save each group
        for group_key, problem_list in grouped_problems.items():
            group_file = base_path / f"{group_key}_problems.jsonl"
            with open(group_file, 'w', encoding='utf-8') as f:
                for problem in problem_list:
                    f.write(json.dumps(asdict(problem), ensure_ascii=False) + '\n')
            
            logger.info(f"Saved {len(problem_list)} multilingual problems to: {group_file}")
        
        # Save cross-language evaluation dataset
        cross_lang_problems = [p for p in problems if p.cross_language_pairs]
        if cross_lang_problems:
            cross_lang_file = base_path / "cross_language_evaluation.jsonl"
            with open(cross_lang_file, 'w', encoding='utf-8') as f:
                for problem in cross_lang_problems:
                    f.write(json.dumps(asdict(problem), ensure_ascii=False) + '\n')
            
            logger.info(f"Saved {len(cross_lang_problems)} cross-language problems to: {cross_lang_file}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Generate multilingual datasets for AI evaluation")
    parser.add_argument("--scenario", type=str, help="Specific scenario to generate")
    parser.add_argument("--count", type=int, default=100, help="Number of problems to generate")
    parser.add_argument("--programming-languages", nargs="+", default=["python", "javascript", "java", "cpp", "go"], 
                       help="Target programming languages")
    parser.add_argument("--natural-languages", nargs="+", default=["en", "zh", "es"], 
                       help="Natural languages for prompts")
    parser.add_argument("--cross-language-only", action="store_true", 
                       help="Generate only cross-language evaluation dataset")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--base-path", type=str, default="lm_eval/tasks", help="Base path for task directories")
    
    args = parser.parse_args()
    
    generator = MultilingualDatasetGenerator(args.base_path)
    
    all_problems = []
    
    if args.cross_language_only:
        logger.info("Generating cross-language evaluation dataset only")
        problems = generator.generate_cross_language_evaluation_dataset(args.count)
        all_problems.extend(problems)
    else:
        scenarios = [args.scenario] if args.scenario else ["code_completion", "function_generation", "algorithm_implementation", "bug_fix", "api_design"]
        
        for scenario in scenarios:
            logger.info(f"Generating multilingual dataset for scenario: {scenario}")
            problems = generator.generate_multilingual_dataset(
                scenario, args.count, args.programming_languages, args.natural_languages
            )
            all_problems.extend(problems)
    
    # Save generated datasets
    generator.save_multilingual_datasets(all_problems, args.output)
    
    logger.info(f"Multilingual dataset generation complete. Generated {len(all_problems)} problems.")

if __name__ == "__main__":
    main()