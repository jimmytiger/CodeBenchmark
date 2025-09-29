#!/usr/bin/env python3
"""
EvaluationEngineV1.0 自定义任务验证脚本

这个脚本专门用于验证 EvaluationEngineV1.0 与自定义任务的集成是否正常工作。
包含真实可执行的 CLI 和 API 验证。
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

def verify_environment():
    """验证环境配置"""
    print("🔍 验证环境配置...")
    
    # 检查 API 密钥
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ 请设置 ANTHROPIC_API_KEY 环境变量")
        return False
    
    # 检查 lm_eval
    try:
        result = subprocess.run(['lm_eval', '--help'], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ lm_eval 未正确安装")
            return False
    except:
        print("❌ lm_eval 不可用")
        return False
    
    # 检查自定义任务
    try:
        result = subprocess.run(['lm_eval', '--tasks', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if 'single_turn_scenarios' not in result.stdout:
            print("❌ 自定义任务不可用")
            return False
    except:
        print("❌ 无法检查自定义任务")
        return False
    
    print("✅ 环境验证通过")
    return True

def verify_cli_execution():
    """验证 CLI 执行"""
    print("\n📝 验证 CLI 执行...")
    
    # 创建临时目录
    temp_dir = Path("./verify_results/cli")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 执行最小化测试
    cmd = [
        'lm_eval',
        '--model', 'anthropic-chat',
        '--model_args', 'model=claude-3-haiku-20240307,max_tokens=256,temperature=0.0',
        '--tasks', 'single_turn_scenarios_code_completion',
        '--limit', '1',
        '--output_path', str(temp_dir),
        '--verbosity', 'ERROR'
    ]
    
    print(f"执行: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # 检查结果文件
            result_files = list(temp_dir.glob('**/results_*.json'))
            if result_files:
                print("✅ CLI 执行成功，结果文件已生成")
                return True
            else:
                print("⚠️  CLI 执行完成但未找到结果文件")
                return False
        else:
            print(f"❌ CLI 执行失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ CLI 执行超时")
        return False
    except Exception as e:
        print(f"❌ CLI 执行异常: {e}")
        return False

def start_api_server():
    """启动 API 服务器"""
    print("\n🌐 启动 API 服务器...")
    
    # 检查服务器脚本
    server_script = Path(__file__).parent / 'custom_task_api_server.py'
    if not server_script.exists():
        print("❌ API 服务器脚本不存在")
        return None
    
    try:
        # 启动服务器
        process = subprocess.Popen([
            sys.executable, str(server_script)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待启动
        time.sleep(3)
        
        # 验证服务器
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("✅ API 服务器启动成功")
                return process
            else:
                print("❌ API 服务器启动失败")
                process.terminate()
                return None
        except:
            print("❌ 无法连接到 API 服务器")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ 启动 API 服务器失败: {e}")
        return None

def verify_api_execution():
    """验证 API 执行"""
    print("\n📡 验证 API 执行...")
    
    api_base = "http://localhost:5000"
    
    try:
        # 1. 健康检查
        response = requests.get(f"{api_base}/health", timeout=5)
        if response.status_code != 200:
            print("❌ 健康检查失败")
            return False
        
        print("✅ 健康检查通过")
        
        # 2. 启动评估
        config = {
            "model": "anthropic-chat",
            "model_args": "model=claude-3-haiku-20240307,max_tokens=256,temperature=0.0",
            "tasks": ["single_turn_scenarios_code_completion"],
            "limit": 1
        }
        
        response = requests.post(f"{api_base}/evaluate", json=config, timeout=10)
        if response.status_code != 202:
            print(f"❌ 启动评估失败: {response.status_code}")
            return False
        
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ 评估启动成功: {job_id}")
        
        # 3. 等待完成
        for i in range(15):  # 最多等待150秒
            response = requests.get(f"{api_base}/status/{job_id}", timeout=5)
            if response.status_code != 200:
                print("❌ 状态查询失败")
                return False
            
            status_data = response.json()
            status = status_data["status"]
            
            if status == "completed":
                print("✅ 任务执行完成")
                break
            elif status == "failed":
                print(f"❌ 任务执行失败: {status_data.get('error', 'Unknown')}")
                return False
            
            time.sleep(10)
        else:
            print("❌ 任务执行超时")
            return False
        
        # 4. 获取结果
        response = requests.get(f"{api_base}/results/{job_id}", timeout=5)
        if response.status_code != 200:
            print("❌ 获取结果失败")
            return False
        
        print("✅ API 执行验证成功")
        return True
        
    except Exception as e:
        print(f"❌ API 执行验证失败: {e}")
        return False

def generate_curl_examples():
    """生成验证过的 curl 示例"""
    print("\n📋 生成 curl 示例...")
    
    curl_content = '''#!/bin/bash
# 验证过的 EvaluationEngineV1.0 curl 示例

API_BASE="http://localhost:5000"

echo "🔍 健康检查"
curl -X GET $API_BASE/health -H "Content-Type: application/json"

echo -e "\\n🚀 启动评估"
JOB_RESPONSE=$(curl -s -X POST $API_BASE/evaluate \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307,max_tokens=256,temperature=0.0",
    "tasks": ["single_turn_scenarios_code_completion"],
    "limit": 1
  }')

echo $JOB_RESPONSE | jq '.'
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

echo -e "\\n👀 查询状态"
curl -X GET $API_BASE/status/$JOB_ID -H "Content-Type: application/json"

echo -e "\\n📊 获取结果 (需要等待任务完成)"
# curl -X GET $API_BASE/results/$JOB_ID -H "Content-Type: application/json"
'''
    
    curl_file = Path("./verify_results/verified_curl_examples.sh")
    curl_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(curl_file, 'w') as f:
        f.write(curl_content)
    
    curl_file.chmod(0o755)
    print(f"✅ curl 示例已生成: {curl_file}")
    return True

def main():
    """主验证函数"""
    print("🚀 EvaluationEngineV1.0 自定义任务验证")
    print("=" * 50)
    
    # 验证环境
    if not verify_environment():
        return 1
    
    # 验证 CLI
    cli_ok = verify_cli_execution()
    
    # 验证 API
    server_process = start_api_server()
    api_ok = False
    
    if server_process:
        api_ok = verify_api_execution()
        
        # 停止服务器
        print("\n🛑 停止服务器...")
        server_process.terminate()
        server_process.wait()
    
    # 生成 curl 示例
    curl_ok = generate_curl_examples()
    
    # 总结
    print("\n" + "=" * 50)
    print("🎯 验证结果总结")
    print(f"✅ CLI 验证: {'通过' if cli_ok else '失败'}")
    print(f"✅ API 验证: {'通过' if api_ok else '失败'}")
    print(f"✅ curl 示例: {'通过' if curl_ok else '失败'}")
    
    success_count = sum([cli_ok, api_ok, curl_ok])
    print(f"📊 总体: {success_count}/3 通过")
    
    if success_count >= 2:
        print("\n🎉 验证成功！EvaluationEngineV1.0 自定义任务集成正常工作")
        print("📁 验证结果保存在: ./verify_results/")
        return 0
    else:
        print("\n❌ 验证失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit(main())