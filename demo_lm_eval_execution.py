#!/usr/bin/env python3
"""
演示如何通过API执行lm-eval任务的完整流程
"""

import requests
import json
import time
import sys

class LMEvalAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        self.session = requests.Session()
    
    def login(self, username="admin", password="admin123"):
        """登录获取访问令牌"""
        print("🔐 正在登录...")
        
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            print(f"✅ 登录成功！用户: {data['user_info']['username']}")
            print(f"🔑 Token: {self.access_token[:50]}...")
            return True
        else:
            print(f"❌ 登录失败: {response.text}")
            return False
    
    def get_available_tasks(self, category=None, limit=10):
        """获取可用任务列表"""
        print("\n📋 获取可用任务...")
        
        params = {"limit": limit}
        if category:
            params["category"] = category
        
        response = self.session.get(f"{self.base_url}/tasks", params=params)
        
        if response.status_code == 200:
            tasks = response.json()
            print(f"✅ 找到 {len(tasks)} 个任务:")
            for task in tasks:
                print(f"  - {task['task_id']}: {task['name']} ({task['difficulty']})")
            return tasks
        else:
            print(f"❌ 获取任务失败: {response.text}")
            return []
    
    def get_available_models(self, provider=None):
        """获取可用模型列表"""
        print("\n🤖 获取可用模型...")
        
        params = {}
        if provider:
            params["provider"] = provider
        
        response = self.session.get(f"{self.base_url}/models", params=params)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 找到 {len(models)} 个模型:")
            for model in models:
                print(f"  - {model['model_id']}: {model['name']} ({model['provider']})")
            return models
        else:
            print(f"❌ 获取模型失败: {response.text}")
            return []
    
    def create_evaluation(self, model_id, task_ids, configuration=None, metadata=None):
        """创建评估任务"""
        print(f"\n🚀 创建评估任务...")
        print(f"   模型: {model_id}")
        print(f"   任务: {', '.join(task_ids)}")
        
        payload = {
            "model_id": model_id,
            "task_ids": task_ids,
            "configuration": configuration or {
                "temperature": 0.7,
                "max_tokens": 1024,
                "limit": 3
            },
            "metadata": metadata or {
                "experiment_name": "api_demo",
                "description": "API演示评估"
            }
        }
        
        response = self.session.post(f"{self.base_url}/evaluations", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            evaluation_id = data["evaluation_id"]
            print(f"✅ 评估任务创建成功!")
            print(f"   评估ID: {evaluation_id}")
            print(f"   状态: {data['status']}")
            return evaluation_id
        else:
            print(f"❌ 创建评估失败: {response.text}")
            return None
    
    def get_evaluation_status(self, evaluation_id):
        """获取评估状态"""
        response = self.session.get(f"{self.base_url}/evaluations/{evaluation_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取状态失败: {response.text}")
            return None
    
    def get_evaluation_results(self, evaluation_id, include_details=True):
        """获取评估结果"""
        params = {"include_details": include_details}
        response = self.session.get(f"{self.base_url}/results/{evaluation_id}", params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取结果失败: {response.text}")
            return None
    
    def monitor_evaluation(self, evaluation_id, max_wait_time=300):
        """监控评估进度"""
        print(f"\n⏳ 监控评估进度 (最多等待 {max_wait_time} 秒)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            status_data = self.get_evaluation_status(evaluation_id)
            if not status_data:
                break
            
            status = status_data["status"]
            progress = status_data.get("progress", 0.0)
            
            print(f"   状态: {status}, 进度: {progress:.1%}")
            
            if status in ["completed", "failed", "cancelled"]:
                return status
            
            time.sleep(2)
        
        print("⚠️ 监控超时")
        return "timeout"
    
    def run_complete_evaluation(self, model_id, task_ids, configuration=None):
        """运行完整的评估流程"""
        print("🎯 开始完整的lm-eval评估流程")
        print("=" * 60)
        
        # 1. 登录
        if not self.login():
            return False
        
        # 2. 获取可用任务和模型
        tasks = self.get_available_tasks()
        models = self.get_available_models()
        
        # 3. 验证任务和模型
        available_task_ids = [t["task_id"] for t in tasks]
        available_model_ids = [m["model_id"] for m in models]
        
        invalid_tasks = [t for t in task_ids if t not in available_task_ids]
        if invalid_tasks:
            print(f"❌ 无效任务: {invalid_tasks}")
            return False
        
        if model_id not in available_model_ids:
            print(f"❌ 无效模型: {model_id}")
            return False
        
        # 4. 创建评估
        evaluation_id = self.create_evaluation(model_id, task_ids, configuration)
        if not evaluation_id:
            return False
        
        # 5. 监控进度
        final_status = self.monitor_evaluation(evaluation_id)
        
        # 6. 获取结果
        if final_status == "completed":
            print("\n📊 获取评估结果...")
            results = self.get_evaluation_results(evaluation_id)
            if results:
                self.display_results(results)
                return True
        
        print(f"❌ 评估未成功完成，最终状态: {final_status}")
        return False
    
    def display_results(self, results):
        """显示评估结果"""
        print("✅ 评估完成！结果如下:")
        print("-" * 40)
        
        print(f"评估ID: {results['evaluation_id']}")
        print(f"模型: {results['model_id']}")
        print(f"状态: {results['status']}")
        
        if "task_results" in results:
            print(f"\n📈 任务结果:")
            for task_result in results["task_results"]:
                print(f"  任务: {task_result['task_id']}")
                print(f"    状态: {task_result['status']}")
                print(f"    分数: {task_result['score']:.3f}")
                print(f"    执行时间: {task_result['execution_time']:.1f}s")
                
                if "metrics" in task_result:
                    print(f"    详细指标:")
                    for metric, value in task_result["metrics"].items():
                        print(f"      {metric}: {value:.3f}")
                print()
        
        if "summary_metrics" in results:
            print(f"📊 总体指标:")
            for metric, value in results["summary_metrics"].items():
                print(f"  {metric}: {value:.3f}")

def main():
    """主函数"""
    print("🎯 LM-Eval API 执行演示")
    print("=" * 60)
    
    # 创建客户端
    client = LMEvalAPIClient()
    
    # 定义评估参数
    model_id = "claude-3-haiku"
    task_ids = [
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_code_completion"
    ]
    
    configuration = {
        "temperature": 0.7,
        "max_tokens": 1024,
        "limit": 5  # 限制样本数量以加快演示
    }
    
    # 运行完整评估
    success = client.run_complete_evaluation(model_id, task_ids, configuration)
    
    if success:
        print("\n🎉 评估成功完成！")
        return 0
    else:
        print("\n💥 评估失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())