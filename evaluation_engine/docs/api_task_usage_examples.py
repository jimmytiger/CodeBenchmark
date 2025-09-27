#!/usr/bin/env python3
"""
API任务配置使用示例

这个文件展示了如何通过API调用配置和管理任务的完整示例，包括：
1. 任务发现和查询
2. 创建自定义任务
3. 配置任务参数
4. 验证和测试任务
5. 使用任务进行评估
"""

import requests
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime


class TaskAPIClient:
    """任务API客户端"""
    
    def __init__(self, api_base: str = "http://localhost:8000", access_token: str = None):
        self.api_base = api_base
        self.access_token = access_token
        self.headers = {
            "Content-Type": "application/json"
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
    
    def set_access_token(self, token: str):
        """设置访问令牌"""
        self.access_token = token
        self.headers["Authorization"] = f"Bearer {token}"
    
    def login(self, username: str, password: str) -> bool:
        """登录并获取访问令牌"""
        try:
            response = requests.post(
                f"{self.api_base}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.set_access_token(auth_data["access_token"])
                print(f"✅ 登录成功，用户: {auth_data['user_info']['username']}")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False
    
    def list_tasks(self, **filters) -> List[Dict[str, Any]]:
        """列出任务"""
        try:
            response = requests.get(
                f"{self.api_base}/tasks",
                headers=self.headers,
                params=filters
            )
            
            if response.status_code == 200:
                return response.json()["items"]
            else:
                print(f"❌ 获取任务列表失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 获取任务列表异常: {e}")
            return []
    
    def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        try:
            response = requests.get(
                f"{self.api_base}/tasks/{task_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"❌ 任务未找到: {task_id}")
                return None
            else:
                print(f"❌ 获取任务详情失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取任务详情异常: {e}")
            return None
    
    def create_custom_task(self, task_config: Dict[str, Any]) -> bool:
        """创建自定义任务"""
        try:
            response = requests.post(
                f"{self.api_base}/tasks/custom",
                headers=self.headers,
                json=task_config
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 任务创建成功: {result['task_id']}")
                return True
            else:
                print(f"❌ 任务创建失败: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ 任务创建异常: {e}")
            return False
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务配置"""
        try:
            response = requests.put(
                f"{self.api_base}/tasks/{task_id}",
                headers=self.headers,
                json=updates
            )
            
            if response.status_code == 200:
                print(f"✅ 任务更新成功: {task_id}")
                return True
            else:
                print(f"❌ 任务更新失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 任务更新异常: {e}")
            return False
    
    def validate_task(self, task_id: str) -> Dict[str, Any]:
        """验证任务配置"""
        try:
            response = requests.post(
                f"{self.api_base}/tasks/{task_id}/validate",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 任务验证失败: {response.status_code}")
                return {"is_valid": False, "errors": ["API call failed"]}
                
        except Exception as e:
            print(f"❌ 任务验证异常: {e}")
            return {"is_valid": False, "errors": [str(e)]}
    
    def test_task(self, task_id: str, sample_input: Dict[str, Any], model_id: str = "dummy") -> Dict[str, Any]:
        """测试任务"""
        try:
            test_request = {
                "sample_input": sample_input,
                "model_id": model_id
            }
            
            response = requests.post(
                f"{self.api_base}/tasks/{task_id}/test",
                headers=self.headers,
                json=test_request
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 任务测试失败: {response.status_code}")
                return {"test_status": "failed", "error_message": response.text}
                
        except Exception as e:
            print(f"❌ 任务测试异常: {e}")
            return {"test_status": "failed", "error_message": str(e)}
    
    def create_evaluation(self, model_id: str, task_ids: List[str], configuration: Dict[str, Any] = None) -> Optional[str]:
        """创建评估"""
        try:
            eval_request = {
                "model_id": model_id,
                "task_ids": task_ids,
                "configuration": configuration or {}
            }
            
            response = requests.post(
                f"{self.api_base}/evaluations",
                headers=self.headers,
                json=eval_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 评估创建成功: {result['evaluation_id']}")
                return result['evaluation_id']
            else:
                print(f"❌ 评估创建失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 评估创建异常: {e}")
            return None
    
    def get_evaluation_status(self, evaluation_id: str) -> Dict[str, Any]:
        """获取评估状态"""
        try:
            response = requests.get(
                f"{self.api_base}/evaluations/{evaluation_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unknown", "error": f"API call failed: {response.status_code}"}
                
        except Exception as e:
            return {"status": "unknown", "error": str(e)}
    
    def get_evaluation_results(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """获取评估结果"""
        try:
            response = requests.get(
                f"{self.api_base}/results/{evaluation_id}",
                headers=self.headers,
                params={"include_details": True}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取评估结果失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取评估结果异常: {e}")
            return None


def example_1_task_discovery():
    """示例1: 任务发现和查询"""
    print("🔍 示例1: 任务发现和查询")
    print("=" * 50)
    
    client = TaskAPIClient()
    
    # 模拟登录
    if not client.login("admin", "admin123"):
        print("登录失败，使用模拟数据演示")
        return
    
    # 列出所有任务
    print("\n📋 列出所有任务:")
    all_tasks = client.list_tasks(limit=10)
    for task in all_tasks:
        print(f"  - {task['task_id']}: {task['name']} ({task['category']}, {task['difficulty']})")
    
    # 按类别筛选
    print("\n📋 单轮任务:")
    single_turn_tasks = client.list_tasks(category="single_turn", limit=5)
    for task in single_turn_tasks:
        print(f"  - {task['task_id']}: {task['description'][:50]}...")
    
    # 按难度筛选
    print("\n📋 高级任务:")
    advanced_tasks = client.list_tasks(difficulty="advanced", limit=5)
    for task in advanced_tasks:
        print(f"  - {task['task_id']}: {task['name']}")
    
    # 获取任务详情
    if all_tasks:
        task_id = all_tasks[0]['task_id']
        print(f"\n📄 任务详情: {task_id}")
        detail = client.get_task_detail(task_id)
        if detail:
            print(f"  名称: {detail['name']}")
            print(f"  描述: {detail['description']}")
            print(f"  语言: {detail['languages']}")
            print(f"  标签: {detail['tags']}")
            print(f"  依赖: {detail['dependencies']}")


def example_2_create_custom_task():
    """示例2: 创建自定义任务"""
    print("\n🛠️ 示例2: 创建自定义任务")
    print("=" * 50)
    
    client = TaskAPIClient()
    
    # 模拟登录
    if not client.login("admin", "admin123"):
        print("登录失败，跳过此示例")
        return
    
    # 定义自定义任务配置
    custom_task_config = {
        "task_id": "python_code_optimization",
        "name": "Python代码优化任务",
        "category": "single_turn",
        "difficulty": "advanced",
        "description": "优化Python代码的性能和可读性",
        "languages": ["python"],
        "tags": ["optimization", "performance", "refactoring"],
        "estimated_duration": 180,
        
        "configuration": {
            "dataset_config": {
                "dataset_path": "datasets/optimization_tasks.jsonl",
                "sample_size": 200,
                "preprocessing": {
                    "normalize_whitespace": True,
                    "validate_syntax": True
                }
            },
            
            "evaluation_config": {
                "metrics": [
                    "performance_improvement",
                    "code_quality",
                    "readability_score"
                ],
                "evaluation_criteria": {
                    "performance_improvement": {"weight": 0.4, "threshold": 0.2},
                    "code_quality": {"weight": 0.3, "threshold": 0.8},
                    "readability_score": {"weight": 0.3, "threshold": 0.7}
                },
                "aggregation_method": "weighted_average",
                "pass_threshold": 0.7
            },
            
            "generation_config": {
                "temperature": 0.3,
                "max_tokens": 2048,
                "top_p": 0.9,
                "stop_sequences": ["```", "\n\n# End of optimization"]
            },
            
            "context_config": {
                "context_mode": "domain_context",
                "context_sources": [
                    {
                        "type": "performance_patterns",
                        "path": "knowledge/python_performance.md",
                        "weight": 0.5
                    },
                    {
                        "type": "optimization_examples",
                        "path": "examples/optimization/",
                        "weight": 0.5
                    }
                ]
            }
        },
        
        "requirements": [
            "保持原有功能不变",
            "提升代码性能",
            "改善代码可读性",
            "遵循Python最佳实践"
        ],
        
        "sample_data": [
            {
                "input": {
                    "original_code": "def find_duplicates(lst):\n    duplicates = []\n    for i in range(len(lst)):\n        for j in range(i+1, len(lst)):\n            if lst[i] == lst[j] and lst[i] not in duplicates:\n                duplicates.append(lst[i])\n    return duplicates",
                    "requirements": "优化查找重复元素的算法"
                },
                "expected_output": {
                    "optimized_code": "def find_duplicates(lst):\n    seen = set()\n    duplicates = set()\n    for item in lst:\n        if item in seen:\n            duplicates.add(item)\n        else:\n            seen.add(item)\n    return list(duplicates)",
                    "improvements": [
                        "使用集合提高查找效率",
                        "时间复杂度从O(n²)降到O(n)",
                        "避免重复添加相同元素"
                    ]
                }
            }
        ]
    }
    
    # 创建任务
    if client.create_custom_task(custom_task_config):
        task_id = custom_task_config["task_id"]
        
        # 验证任务
        print(f"\n🔍 验证任务: {task_id}")
        validation = client.validate_task(task_id)
        
        print(f"验证结果: {'✅ 通过' if validation['is_valid'] else '❌ 失败'}")
        
        if validation.get('warnings'):
            print("⚠️ 警告:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        if validation.get('errors'):
            print("❌ 错误:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        # 测试任务
        print(f"\n🧪 测试任务: {task_id}")
        test_input = {
            "original_code": "def sum_list(numbers):\n    total = 0\n    for i in range(len(numbers)):\n        total += numbers[i]\n    return total",
            "requirements": "优化求和函数"
        }
        
        test_result = client.test_task(task_id, test_input)
        print(f"测试状态: {test_result['test_status']}")
        
        if test_result.get('model_output'):
            print(f"模型输出: {test_result['model_output'][:100]}...")
        
        if test_result.get('error_message'):
            print(f"错误信息: {test_result['error_message']}")


def example_3_task_configuration_management():
    """示例3: 任务配置管理"""
    print("\n⚙️ 示例3: 任务配置管理")
    print("=" * 50)
    
    client = TaskAPIClient()
    
    # 模拟登录
    if not client.login("admin", "admin123"):
        print("登录失败，跳过此示例")
        return
    
    task_id = "python_code_optimization"  # 使用示例2创建的任务
    
    # 更新任务配置
    print(f"🔧 更新任务配置: {task_id}")
    
    updates = {
        "configuration": {
            "generation_config": {
                "temperature": 0.2,  # 降低温度以提高一致性
                "max_tokens": 3000   # 增加token限制
            },
            "evaluation_config": {
                "evaluation_criteria": {
                    "performance_improvement": {"weight": 0.5, "threshold": 0.3},
                    "code_quality": {"weight": 0.3, "threshold": 0.8},
                    "readability_score": {"weight": 0.2, "threshold": 0.7}
                }
            }
        },
        "requirements": [
            "保持原有功能不变",
            "显著提升代码性能",
            "改善代码可读性",
            "遵循Python最佳实践",
            "添加适当的注释和文档"  # 新增要求
        ]
    }
    
    if client.update_task(task_id, updates):
        # 重新验证更新后的配置
        print(f"\n🔍 重新验证任务: {task_id}")
        validation = client.validate_task(task_id)
        
        print(f"验证结果: {'✅ 通过' if validation['is_valid'] else '❌ 失败'}")
        
        # 显示验证详情
        if validation.get('validation_results'):
            results = validation['validation_results']
            print("验证详情:")
            for key, value in results.items():
                status = "✅" if value else "❌"
                print(f"  {status} {key}: {value}")


def example_4_batch_task_management():
    """示例4: 批量任务管理"""
    print("\n📦 示例4: 批量任务管理")
    print("=" * 50)
    
    client = TaskAPIClient()
    
    # 模拟登录
    if not client.login("admin", "admin123"):
        print("登录失败，跳过此示例")
        return
    
    # 定义任务模板
    task_templates = [
        {
            "base_name": "python_debugging",
            "variants": [
                {"difficulty": "beginner", "max_tokens": 1024, "temperature": 0.3},
                {"difficulty": "intermediate", "max_tokens": 2048, "temperature": 0.4},
                {"difficulty": "advanced", "max_tokens": 3072, "temperature": 0.5}
            ]
        },
        {
            "base_name": "code_review",
            "variants": [
                {"focus": "security", "max_tokens": 2048, "temperature": 0.2},
                {"focus": "performance", "max_tokens": 2048, "temperature": 0.3},
                {"focus": "maintainability", "max_tokens": 2048, "temperature": 0.4}
            ]
        }
    ]
    
    created_tasks = []
    
    # 批量创建任务
    for template in task_templates:
        base_name = template["base_name"]
        
        for i, variant in enumerate(template["variants"]):
            task_id = f"{base_name}_{list(variant.keys())[0]}_{list(variant.values())[0]}"
            
            task_config = {
                "task_id": task_id,
                "name": f"{base_name.replace('_', ' ').title()} - {list(variant.values())[0].title()}",
                "category": "single_turn",
                "difficulty": variant.get("difficulty", "intermediate"),
                "description": f"专门的{base_name}任务，专注于{list(variant.values())[0]}",
                "languages": ["python"],
                "tags": [base_name, list(variant.keys())[0]],
                "estimated_duration": 120,
                
                "configuration": {
                    "generation_config": {
                        "temperature": variant.get("temperature", 0.4),
                        "max_tokens": variant.get("max_tokens", 2048),
                        "top_p": 0.9
                    },
                    "evaluation_config": {
                        "metrics": ["accuracy", "quality", "completeness"],
                        "evaluation_criteria": {
                            "accuracy": {"weight": 0.4, "threshold": 0.8},
                            "quality": {"weight": 0.3, "threshold": 0.7},
                            "completeness": {"weight": 0.3, "threshold": 0.7}
                        }
                    }
                },
                
                "requirements": [
                    f"专注于{list(variant.values())[0]}方面",
                    "提供清晰的解释",
                    "遵循最佳实践"
                ]
            }
            
            if client.create_custom_task(task_config):
                created_tasks.append(task_id)
                print(f"✅ 创建任务: {task_id}")
            else:
                print(f"❌ 创建任务失败: {task_id}")
    
    print(f"\n📊 批量创建结果: {len(created_tasks)} 个任务创建成功")
    
    # 批量验证任务
    print("\n🔍 批量验证任务:")
    validation_results = {}
    
    for task_id in created_tasks:
        validation = client.validate_task(task_id)
        validation_results[task_id] = validation
        
        status = "✅" if validation['is_valid'] else "❌"
        print(f"  {status} {task_id}: {'通过' if validation['is_valid'] else '失败'}")
    
    # 统计验证结果
    valid_tasks = [tid for tid, result in validation_results.items() if result['is_valid']]
    print(f"\n📈 验证摘要: {len(valid_tasks)}/{len(created_tasks)} 个任务通过验证")
    
    return created_tasks


def example_5_task_evaluation_workflow():
    """示例5: 任务评估工作流程"""
    print("\n🚀 示例5: 任务评估工作流程")
    print("=" * 50)
    
    client = TaskAPIClient()
    
    # 模拟登录
    if not client.login("admin", "admin123"):
        print("登录失败，跳过此示例")
        return
    
    # 使用之前创建的任务进行评估
    task_ids = [
        "python_code_optimization",
        "python_debugging_difficulty_beginner",
        "code_review_focus_security"
    ]
    
    # 创建评估
    print("📋 创建评估任务...")
    evaluation_config = {
        "limit": 3,  # 限制样本数量
        "temperature": 0.4,
        "max_tokens": 2048,
        "context_mode": "full_context"
    }
    
    evaluation_id = client.create_evaluation(
        model_id="claude-3-haiku",
        task_ids=task_ids,
        configuration=evaluation_config
    )
    
    if not evaluation_id:
        print("❌ 评估创建失败")
        return
    
    # 监控评估进度
    print(f"\n📊 监控评估进度: {evaluation_id}")
    
    max_wait_time = 300  # 最大等待5分钟
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = client.get_evaluation_status(evaluation_id)
        
        if status.get('status') in ['completed', 'failed', 'cancelled']:
            break
        
        progress = status.get('progress', 0)
        current_task = status.get('current_task', 'unknown')
        
        print(f"  进度: {progress:.1%} - 当前任务: {current_task}")
        time.sleep(10)  # 等待10秒
    
    # 获取评估结果
    final_status = client.get_evaluation_status(evaluation_id)
    
    if final_status.get('status') == 'completed':
        print(f"\n✅ 评估完成!")
        
        results = client.get_evaluation_results(evaluation_id)
        if results:
            print(f"总体分数: {results['overall_score']:.3f}")
            print(f"执行时间: {results['execution_time']:.1f}s")
            
            print("\n📊 各任务结果:")
            for task_result in results['task_results']:
                print(f"  任务: {task_result['task_id']}")
                print(f"    分数: {task_result['score']:.3f}")
                print(f"    状态: {task_result['status']}")
                
                if task_result.get('metrics'):
                    print(f"    指标:")
                    for metric, value in task_result['metrics'].items():
                        print(f"      {metric}: {value:.3f}")
                print()
    
    elif final_status.get('status') == 'failed':
        print(f"❌ 评估失败: {final_status.get('error_message', 'Unknown error')}")
    
    else:
        print(f"⏰ 评估超时，当前状态: {final_status.get('status', 'unknown')}")


def main():
    """主函数 - 运行所有示例"""
    print("🎯 API任务配置使用示例")
    print("=" * 60)
    
    try:
        # 示例1: 任务发现和查询
        example_1_task_discovery()
        
        # 示例2: 创建自定义任务
        example_2_create_custom_task()
        
        # 示例3: 任务配置管理
        example_3_task_configuration_management()
        
        # 示例4: 批量任务管理
        created_tasks = example_4_batch_task_management()
        
        # 示例5: 任务评估工作流程
        example_5_task_evaluation_workflow()
        
        print("\n🎉 所有示例运行完成!")
        print("=" * 60)
        
        print("\n📋 示例总结:")
        print("1. ✅ 任务发现和查询 - 学会如何搜索和筛选任务")
        print("2. ✅ 创建自定义任务 - 学会如何定义和创建新任务")
        print("3. ✅ 任务配置管理 - 学会如何更新和管理任务配置")
        print("4. ✅ 批量任务管理 - 学会如何批量创建和管理任务")
        print("5. ✅ 任务评估工作流程 - 学会如何使用任务进行完整评估")
        
        print("\n💡 下一步建议:")
        print("- 根据实际需求创建自定义任务")
        print("- 使用A/B测试优化任务配置")
        print("- 集成到自动化评估流水线中")
        print("- 监控任务性能和结果质量")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()