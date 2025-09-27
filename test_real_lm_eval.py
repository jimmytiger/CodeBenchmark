#!/usr/bin/env python3
"""
测试真实的lm-eval API执行
"""

import requests
import json
import time
import sys

def test_real_lm_eval_api():
    """测试真实的lm-eval API"""
    base_url = "http://localhost:8000"
    
    print("🎯 测试真实的 LM-Eval API")
    print("=" * 50)
    
    # 1. 健康检查
    print("1️⃣ 健康检查...")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✅ 服务健康")
        print(f"   - 版本: {health['version']}")
        print(f"   - 可用任务: {health['available_tasks']}")
        print(f"   - 可用模型: {health['available_models']}")
    else:
        print("❌ 服务不可用")
        return False
    
    # 2. 登录
    print("\n2️⃣ 用户登录...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    if login_response.status_code == 200:
        auth_data = login_response.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ 登录成功: {auth_data['user_info']['username']}")
    else:
        print("❌ 登录失败")
        return False
    
    # 3. 获取真实任务列表
    print("\n3️⃣ 获取真实任务列表...")
    tasks_response = requests.get(f"{base_url}/tasks?limit=10", headers=headers)
    
    if tasks_response.status_code == 200:
        tasks = tasks_response.json()
        print(f"✅ 发现 {len(tasks)} 个真实任务:")
        for task in tasks[:5]:
            print(f"   - {task['task_id']}: {task['name']} ({task['difficulty']})")
        if len(tasks) > 5:
            print(f"   ... 还有 {len(tasks) - 5} 个任务")
    else:
        print("❌ 获取任务失败")
        return False
    
    # 4. 获取模型列表
    print("\n4️⃣ 获取模型列表...")
    models_response = requests.get(f"{base_url}/models", headers=headers)
    
    if models_response.status_code == 200:
        models = models_response.json()
        print(f"✅ 发现 {len(models)} 个模型:")
        for model in models:
            print(f"   - {model['model_id']}: {model['name']} ({model['provider']})")
    else:
        print("❌ 获取模型失败")
        return False
    
    # 5. 创建真实评估任务
    print("\n5️⃣ 创建真实评估任务...")
    
    # 选择一个简单的任务进行测试
    test_task = "single_turn_scenarios_function_generation"
    test_model = "dummy"  # 使用dummy模型避免API密钥问题
    
    eval_request = {
        "model_id": test_model,
        "task_ids": [test_task],
        "configuration": {
            "limit": 2,  # 只测试2个样本
            "temperature": 0.7
        },
        "metadata": {
            "experiment_name": "real_api_test",
            "description": "测试真实API执行lm-eval任务"
        }
    }
    
    eval_response = requests.post(
        f"{base_url}/evaluations",
        json=eval_request,
        headers=headers
    )
    
    if eval_response.status_code == 200:
        eval_data = eval_response.json()
        evaluation_id = eval_data["evaluation_id"]
        print(f"✅ 评估任务已创建: {evaluation_id}")
        print(f"   - 状态: {eval_data['status']}")
        print(f"   - 任务: {test_task}")
        print(f"   - 模型: {test_model}")
    else:
        print(f"❌ 创建评估失败: {eval_response.text}")
        return False
    
    # 6. 监控评估进度
    print("\n6️⃣ 监控评估进度...")
    max_wait_time = 120  # 最多等待2分钟
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status_response = requests.get(
            f"{base_url}/evaluations/{evaluation_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data["status"]
            
            print(f"   状态: {status}")
            
            if status == "completed":
                print("✅ 评估完成！")
                break
            elif status == "failed":
                error = status_data.get("error", "未知错误")
                print(f"❌ 评估失败: {error}")
                return False
            
            time.sleep(5)
        else:
            print("❌ 获取状态失败")
            return False
    else:
        print("⚠️ 评估超时")
        return False
    
    # 7. 获取评估结果
    print("\n7️⃣ 获取评估结果...")
    results_response = requests.get(
        f"{base_url}/results/{evaluation_id}?include_details=true",
        headers=headers
    )
    
    if results_response.status_code == 200:
        results = results_response.json()
        print("✅ 获取结果成功!")
        
        print(f"\n📊 评估结果摘要:")
        print(f"   - 评估ID: {results['evaluation_id']}")
        print(f"   - 模型: {results['model_id']}")
        
        if "summary_metrics" in results:
            summary = results["summary_metrics"]
            print(f"   - 总体分数: {summary.get('overall_score', 'N/A')}")
            print(f"   - 完成任务数: {summary.get('completed_tasks', 0)}/{summary.get('total_tasks', 0)}")
        
        if "task_results" in results:
            print(f"\n📋 任务详细结果:")
            for task_result in results["task_results"]:
                print(f"   任务: {task_result['task_id']}")
                print(f"     - 状态: {task_result['status']}")
                print(f"     - 分数: {task_result.get('score', 'N/A')}")
                if "metrics" in task_result:
                    print(f"     - 指标: {task_result['metrics']}")
                print(f"     - 执行时间: {task_result.get('execution_time', 'N/A')}s")
        
        # 显示原始输出的一部分
        if "raw_output" in results:
            raw_output = results["raw_output"]
            if raw_output:
                print(f"\n📝 原始输出预览:")
                lines = raw_output.split('\n')[:10]
                for line in lines:
                    if line.strip():
                        print(f"   {line}")
                if len(raw_output.split('\n')) > 10:
                    print("   ...")
        
        return True
    else:
        print(f"❌ 获取结果失败: {results_response.text}")
        return False

def main():
    """主函数"""
    try:
        success = test_real_lm_eval_api()
        
        if success:
            print("\n🎉 真实API测试成功完成！")
            print("\n💡 接下来你可以:")
            print("   1. 尝试不同的任务和模型组合")
            print("   2. 配置API密钥使用真实的AI模型")
            print("   3. 调整评估参数进行更深入的测试")
            print("   4. 查看完整的API文档: http://localhost:8000/docs")
            return 0
        else:
            print("\n💥 测试失败！请检查服务器状态和配置")
            return 1
            
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
        return 0
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())