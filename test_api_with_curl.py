#!/usr/bin/env python3
"""
API测试脚本 - 使用curl命令验证API服务
"""

import subprocess
import json
import time
import sys

class APITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
    
    def run_curl(self, method, endpoint, data=None, headers=None, params=None):
        """执行curl命令"""
        url = f"{self.base_url}{endpoint}"
        
        # 构建curl命令
        cmd = ["curl", "-s", "-X", method]
        
        # 添加headers
        if headers:
            for key, value in headers.items():
                cmd.extend(["-H", f"{key}: {value}"])
        
        # 添加数据
        if data:
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-d", json.dumps(data)])
        
        # 添加参数
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url += f"?{param_str}"
        
        cmd.append(url)
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw_output": result.stdout}
            else:
                return {"error": result.stderr, "stdout": result.stdout}
        
        except subprocess.TimeoutExpired:
            return {"error": "请求超时"}
        except Exception as e:
            return {"error": str(e)}
    
    def test_health_check(self):
        """测试健康检查"""
        print("\n1️⃣ 测试健康检查")
        print("-" * 40)
        
        response = self.run_curl("GET", "/health")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
        if "status" in response and response["status"] == "healthy":
            print("✅ 健康检查通过")
            return True
        else:
            print("❌ 健康检查失败")
            return False
    
    def test_login(self):
        """测试登录获取token"""
        print("\n2️⃣ 测试用户登录")
        print("-" * 40)
        
        # 测试管理员登录
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = self.run_curl("POST", "/auth/login", data=login_data)
        print(f"登录响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
        if "access_token" in response:
            self.access_token = response["access_token"]
            print("✅ 登录成功，获得访问令牌")
            print(f"🔑 Access Token: {self.access_token[:50]}...")
            return True
        else:
            print("❌ 登录失败")
            return False
    
    def test_authenticated_request(self):
        """测试需要认证的请求"""
        if not self.access_token:
            print("❌ 没有访问令牌，跳过认证测试")
            return False
        
        print("\n3️⃣ 测试认证请求")
        print("-" * 40)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # 测试获取任务列表
        response = self.run_curl("GET", "/tasks", headers=headers, params={"limit": 5})
        print(f"任务列表响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
        if "error" not in response:
            print("✅ 认证请求成功")
            return True
        else:
            print("❌ 认证请求失败")
            return False
    
    def test_models_endpoint(self):
        """测试模型列表端点"""
        if not self.access_token:
            print("❌ 没有访问令牌，跳过模型测试")
            return False
        
        print("\n4️⃣ 测试模型列表")
        print("-" * 40)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = self.run_curl("GET", "/models", headers=headers)
        print(f"模型列表响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
        if "error" not in response:
            print("✅ 模型列表获取成功")
            return True
        else:
            print("❌ 模型列表获取失败")
            return False
    
    def generate_curl_examples(self):
        """生成curl命令示例"""
        print("\n📋 Curl 命令示例")
        print("=" * 60)
        
        print("1. 健康检查:")
        print(f"curl -X GET {self.base_url}/health")
        
        print("\n2. 用户登录:")
        print(f"""curl -X POST {self.base_url}/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"username": "admin", "password": "admin123"}}'""")
        
        if self.access_token:
            print("\n3. 获取任务列表 (需要token):")
            print(f"""curl -X GET {self.base_url}/tasks \\
  -H "Authorization: Bearer {self.access_token[:20]}..." \\
  -G -d "limit=10" -d "category=single_turn" """)
            
            print("\n4. 获取模型列表 (需要token):")
            print(f"""curl -X GET {self.base_url}/models \\
  -H "Authorization: Bearer {self.access_token[:20]}..." """)
            
            print("\n5. 创建评估任务 (需要token):")
            print(f"""curl -X POST {self.base_url}/evaluations \\
  -H "Authorization: Bearer {self.access_token[:20]}..." \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model_id": "claude-3-haiku",
    "task_ids": ["single_turn_scenarios_function_generation"],
    "configuration": {{
      "temperature": 0.7,
      "max_tokens": 1024,
      "limit": 3
    }},
    "metadata": {{
      "experiment_name": "test_evaluation"
    }}
  }}'""")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始API测试")
        print("=" * 60)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("用户登录", self.test_login),
            ("认证请求", self.test_authenticated_request),
            ("模型列表", self.test_models_endpoint)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")
                results[test_name] = False
        
        # 显示测试结果摘要
        print("\n📊 测试结果摘要")
        print("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")
        
        print(f"\n总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！API服务运行正常")
        else:
            print("⚠️  部分测试失败，请检查服务配置")
        
        # 生成curl示例
        self.generate_curl_examples()
        
        return passed == total

def main():
    """主函数"""
    print("🔧 API服务测试工具")
    print("确保API服务器已在 http://localhost:8000 启动")
    
    # 等待用户确认
    input("按回车键开始测试...")
    
    tester = APITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ 测试完成！你现在可以使用生成的curl命令来验证API")
        return 0
    else:
        print("\n💥 测试失败！请检查API服务器状态")
        return 1

if __name__ == "__main__":
    sys.exit(main())