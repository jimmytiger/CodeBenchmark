#!/usr/bin/env python3
"""
EvaluationEngineV1.0 自定义任务 API 服务器

基于 EvaluationEngineV1.0 框架的完整 REST API 服务器，
支持单轮和多轮自定义任务的异步评估。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
import traceback
import os
from typing import Dict, List, Optional, Any

from custom_task_integration import (
    CustomTaskEvaluationEngine,
    CustomTaskConfig,
    EvaluationResult,
    TaskType,
    evaluate_custom_task,
    evaluate_custom_task_suite
)

app = Flask(__name__)
CORS(app)

# 全局状态管理
evaluation_jobs: Dict[str, Dict[str, Any]] = {}
results_storage = Path("./api_results")
results_storage.mkdir(exist_ok=True)

# 评估引擎实例
evaluation_engine = CustomTaskEvaluationEngine()


class EvaluationJob:
    """评估任务类"""
    
    def __init__(self, job_id: str, config: Dict[str, Any]):
        self.job_id = job_id
        self.config = config
        self.status = "pending"
        self.progress = 0
        self.result: Optional[EvaluationResult] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.output_path: Optional[str] = None


def run_evaluation_async(job_id: str, config: Dict[str, Any]):
    """异步运行评估任务"""
    job = evaluation_jobs[job_id]
    
    try:
        job["status"] = "running"
        job["started_at"] = datetime.now()
        job["progress"] = 10
        
        # 创建输出目录
        output_path = results_storage / job_id
        output_path.mkdir(exist_ok=True)
        job["output_path"] = str(output_path)
        
        job["progress"] = 30
        
        # 执行评估
        print(f"🚀 开始执行任务: {job_id}")
        print(f"📋 配置: {config}")
        
        task_names = config.get("tasks", [])
        model = config.get("model", "anthropic-chat")
        model_args = config.get("model_args", "model=claude-3-haiku-20240307")
        
        # 构建评估参数
        eval_kwargs = {
            "limit": config.get("limit", 5),
            "num_fewshot": config.get("num_fewshot", 0),
            "batch_size": config.get("batch_size", 1),
            "output_path": str(output_path),
            "verbosity": config.get("verbosity", "INFO")
        }
        
        if config.get("apply_chat_template", False):
            eval_kwargs["apply_chat_template"] = True
        
        job["progress"] = 50
        
        # 执行评估
        if len(task_names) == 1:
            # 单个任务
            result = evaluate_custom_task(
                task_name=task_names[0],
                model=model,
                model_args=model_args,
                **eval_kwargs
            )
            job["result"] = result
        else:
            # 多个任务
            results = evaluate_custom_task_suite(
                task_names=task_names,
                model=model,
                model_args=model_args,
                **eval_kwargs
            )
            # 合并结果
            job["result"] = {
                "task_results": results,
                "summary": {
                    "total_tasks": len(results),
                    "completed": len([r for r in results if r.status == "completed"]),
                    "failed": len([r for r in results if r.status == "failed"])
                }
            }
        
        job["progress"] = 90
        
        # 保存结果到文件
        result_file = output_path / "evaluation_result.json"
        with open(result_file, 'w') as f:
            json.dump({
                'job_id': job_id,
                'config': config,
                'result': job["result"].__dict__ if hasattr(job["result"], '__dict__') else job["result"],
                'timestamps': {
                    'created': job["created_at"].isoformat(),
                    'started': job["started_at"].isoformat() if job["started_at"] else None,
                    'completed': datetime.now().isoformat()
                }
            }, f, indent=2, default=str)
        
        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = datetime.now()
        
        print(f"✅ 任务 {job_id} 执行完成")
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now()
        job["progress"] = 100
        
        print(f"❌ 任务 {job_id} 执行失败: {e}")
        traceback.print_exc()


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in evaluation_jobs.values() if j["status"] == "running"]),
        "total_jobs": len(evaluation_jobs),
        "engine_info": {
            "framework": "EvaluationEngineV1.0",
            "supported_task_types": ["single_turn", "multi_turn", "custom"],
            "available_tasks": get_available_tasks()
        }
    })


@app.route('/tasks', methods=['GET'])
def list_available_tasks():
    """列出可用的自定义任务"""
    return jsonify({
        "available_tasks": get_available_tasks(),
        "task_categories": {
            "single_turn_scenarios": [
                "single_turn_scenarios_code_completion",
                "single_turn_scenarios_bug_fix",
                "single_turn_scenarios_code_translation",
                "single_turn_scenarios_documentation",
                "single_turn_scenarios_function_generation",
                "single_turn_scenarios_system_design",
                "single_turn_scenarios_algorithm_implementation",
                "single_turn_scenarios_api_design",
                "single_turn_scenarios_database_design",
                "single_turn_scenarios_performance_optimization",
                "single_turn_scenarios_full_stack",
                "single_turn_scenarios_testing_strategy",
                "single_turn_scenarios_security"
            ],
            "multi_turn_scenarios": [
                "multi_turn_scenarios.code_review_3_turn",
                "multi_turn_scenarios.iterative_problem_solving",
                "multi_turn_scenarios.teaching_dialogue",
                "multi_turn_scenarios.debugging_session",
                "multi_turn_scenarios.design_iteration",
                "multi_turn_scenarios.collaborative_development",
                "multi_turn_scenarios.requirements_refinement",
                "multi_turn_scenarios.performance_tuning"
            ],
            "suites": [
                "single_turn_scenarios_suite",
                "single_turn_scenarios_python",
                "single_turn_scenarios_intermediate"
            ]
        }
    })


@app.route('/evaluate', methods=['POST'])
def start_evaluation():
    """启动评估任务"""
    try:
        config = request.get_json()
        
        # 验证必需字段
        required_fields = ["model", "tasks"]
        for field in required_fields:
            if field not in config:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # 验证任务名称
        available_tasks = get_available_tasks()
        invalid_tasks = [task for task in config["tasks"] if task not in available_tasks]
        if invalid_tasks:
            return jsonify({
                "error": f"Invalid tasks: {invalid_tasks}",
                "available_tasks": available_tasks
            }), 400
        
        # 设置默认值
        config.setdefault("model_args", "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0")
        config.setdefault("num_fewshot", 0)
        config.setdefault("batch_size", 1)
        config.setdefault("limit", 5)
        config.setdefault("verbosity", "INFO")
        
        # 自动检测是否需要 chat template
        multi_turn_tasks = [task for task in config["tasks"] if "multi_turn" in task]
        if multi_turn_tasks:
            config.setdefault("apply_chat_template", True)
        
        # 生成任务ID
        job_id = str(uuid.uuid4())[:8]
        
        # 创建任务
        job = {
            "job_id": job_id,
            "config": config,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "output_path": None
        }
        
        evaluation_jobs[job_id] = job
        
        # 启动异步评估
        thread = threading.Thread(target=run_evaluation_async, args=(job_id, config))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "job_id": job_id,
            "status": "pending",
            "message": "Custom task evaluation started",
            "check_status_url": f"/status/{job_id}",
            "config": config,
            "framework": "EvaluationEngineV1.0"
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """获取任务状态"""
    if job_id not in evaluation_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = evaluation_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "created_at": job["created_at"].isoformat(),
        "started_at": job["started_at"].isoformat() if job["started_at"] else None,
        "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
        "output_path": job["output_path"],
        "framework": "EvaluationEngineV1.0"
    }
    
    if job["error"]:
        response["error"] = job["error"]
    
    return jsonify(response)


@app.route('/results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    """获取评估结果"""
    if job_id not in evaluation_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = evaluation_jobs[job_id]
    
    if job["status"] != "completed":
        return jsonify({
            "error": "Job not completed",
            "status": job["status"],
            "progress": job["progress"]
        }), 400
    
    # 处理结果数据
    result_data = job["result"]
    
    if isinstance(result_data, EvaluationResult):
        # 单个任务结果
        summary = {
            "task_id": result_data.task_id,
            "task_type": result_data.task_type.value,
            "status": result_data.status,
            "execution_time": result_data.execution_time
        }
        
        full_results = {
            "task_id": result_data.task_id,
            "task_type": result_data.task_type.value,
            "status": result_data.status,
            "results": result_data.results,
            "execution_time": result_data.execution_time,
            "created_at": result_data.created_at.isoformat() if result_data.created_at else None,
            "completed_at": result_data.completed_at.isoformat() if result_data.completed_at else None
        }
    else:
        # 多个任务结果
        summary = result_data.get("summary", {})
        full_results = result_data
    
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "summary": summary,
        "full_results": full_results,
        "config": job["config"],
        "framework": "EvaluationEngineV1.0"
    })


@app.route('/jobs', methods=['GET'])
def list_jobs():
    """列出所有任务"""
    jobs_list = []
    for job_id, job in evaluation_jobs.items():
        jobs_list.append({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "created_at": job["created_at"].isoformat(),
            "model": job["config"].get("model", "unknown"),
            "tasks": job["config"].get("tasks", []),
            "duration": (
                (job["completed_at"] - job["started_at"]).total_seconds() 
                if job["started_at"] and job["completed_at"] 
                else None
            ),
            "framework": "EvaluationEngineV1.0"
        })
    
    return jsonify({
        "jobs": jobs_list, 
        "total": len(jobs_list),
        "framework": "EvaluationEngineV1.0"
    })


@app.route('/engine/info', methods=['GET'])
def get_engine_info():
    """获取评估引擎信息"""
    return jsonify({
        "framework": "EvaluationEngineV1.0",
        "version": "1.0.0",
        "description": "Multi-Turn Evaluation Engine with Custom Task Integration",
        "supported_features": [
            "Single-turn task evaluation",
            "Multi-turn task evaluation", 
            "Custom task integration",
            "Unified environment interface",
            "Comprehensive error handling",
            "Async task processing"
        ],
        "supported_models": [
            "anthropic-chat",
            "openai-chat",
            "openai-completions",
            "dashscope",
            "hf (HuggingFace)",
            "claude-code-local"
        ],
        "task_categories": {
            "single_turn": 13,
            "multi_turn": 8,
            "total_available": len(get_available_tasks())
        }
    })


@app.route('/demo', methods=['GET'])
def demo_page():
    """演示页面"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EvaluationEngineV1.0 Custom Task API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
            button { padding: 12px 24px; margin: 8px; background: #007cba; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
            button:hover { background: #005a87; }
            button.secondary { background: #6c757d; }
            button.success { background: #28a745; }
            pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border-left: 4px solid #007cba; }
            .status { padding: 15px; margin: 15px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .badge { background: #007cba; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 EvaluationEngineV1.0</h1>
                <h2>Custom Task API Demo</h2>
                <span class="badge">Framework Version 1.0</span>
            </div>
            
            <div class="section">
                <h2>📡 API 端点</h2>
                <div class="grid">
                    <div>
                        <h3>基础端点</h3>
                        <ul>
                            <li><strong>GET /health</strong> - 健康检查</li>
                            <li><strong>GET /tasks</strong> - 列出可用任务</li>
                            <li><strong>GET /engine/info</strong> - 引擎信息</li>
                        </ul>
                    </div>
                    <div>
                        <h3>评估端点</h3>
                        <ul>
                            <li><strong>POST /evaluate</strong> - 启动评估</li>
                            <li><strong>GET /status/&lt;job_id&gt;</strong> - 查看状态</li>
                            <li><strong>GET /results/&lt;job_id&gt;</strong> - 获取结果</li>
                            <li><strong>GET /jobs</strong> - 列出所有任务</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🚀 快速测试</h2>
                <div class="grid">
                    <div>
                        <button onclick="checkHealth()">检查健康状态</button>
                        <button onclick="listTasks()" class="secondary">列出可用任务</button>
                        <button onclick="getEngineInfo()" class="success">引擎信息</button>
                    </div>
                    <div>
                        <button onclick="startSingleTurnEval()">单轮任务评估</button>
                        <button onclick="startMultiTurnEval()">多轮任务评估</button>
                        <button onclick="listJobs()" class="secondary">查看任务列表</button>
                    </div>
                </div>
                <div id="output"></div>
            </div>
            
            <div class="section">
                <h2>📋 示例请求</h2>
                
                <h3>单轮场景评估</h3>
                <pre>curl -X POST http://localhost:5000/evaluate \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    "tasks": ["single_turn_scenarios_code_completion"],
    "limit": 5,
    "num_fewshot": 0,
    "batch_size": 1
  }'</pre>
                
                <h3>多轮场景评估</h3>
                <pre>curl -X POST http://localhost:5000/evaluate \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    "tasks": ["multi_turn_scenarios.code_review_3_turn"],
    "limit": 3,
    "apply_chat_template": true
  }'</pre>
                
                <h3>任务套件评估</h3>
                <pre>curl -X POST http://localhost:5000/evaluate \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307",
    "tasks": [
      "single_turn_scenarios_code_completion",
      "single_turn_scenarios_bug_fix",
      "multi_turn_scenarios.code_review_3_turn"
    ],
    "limit": 3
  }'</pre>
            </div>
        </div>
        
        <script>
            function showOutput(content, type = 'info') {
                const output = document.getElementById('output');
                output.innerHTML = `<div class="status ${type}"><pre>${JSON.stringify(content, null, 2)}</pre></div>`;
            }
            
            async function checkHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    showOutput(data, 'success');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
            
            async function listTasks() {
                try {
                    const response = await fetch('/tasks');
                    const data = await response.json();
                    showOutput(data, 'info');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
            
            async function getEngineInfo() {
                try {
                    const response = await fetch('/engine/info');
                    const data = await response.json();
                    showOutput(data, 'success');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
            
            async function startSingleTurnEval() {
                try {
                    const config = {
                        model: "anthropic-chat",
                        model_args: "model=claude-3-haiku-20240307,max_tokens=512,temperature=0.0",
                        tasks: ["single_turn_scenarios_code_completion"],
                        limit: 2,
                        num_fewshot: 0,
                        batch_size: 1
                    };
                    
                    const response = await fetch('/evaluate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    });
                    
                    const data = await response.json();
                    showOutput(data, response.ok ? 'success' : 'error');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
            
            async function startMultiTurnEval() {
                try {
                    const config = {
                        model: "anthropic-chat",
                        model_args: "model=claude-3-haiku-20240307,max_tokens=512,temperature=0.0",
                        tasks: ["multi_turn_scenarios.code_review_3_turn"],
                        limit: 1,
                        apply_chat_template: true
                    };
                    
                    const response = await fetch('/evaluate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    });
                    
                    const data = await response.json();
                    showOutput(data, response.ok ? 'success' : 'error');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
            
            async function listJobs() {
                try {
                    const response = await fetch('/jobs');
                    const data = await response.json();
                    showOutput(data, 'success');
                } catch (error) {
                    showOutput({error: error.message}, 'error');
                }
            }
        </script>
    </body>
    </html>
    """
    return html


def get_available_tasks() -> List[str]:
    """获取可用任务列表"""
    return [
        # Single-turn scenarios
        "single_turn_scenarios_suite",
        "single_turn_scenarios_code_completion",
        "single_turn_scenarios_bug_fix",
        "single_turn_scenarios_code_translation",
        "single_turn_scenarios_documentation",
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_system_design",
        "single_turn_scenarios_algorithm_implementation",
        "single_turn_scenarios_api_design",
        "single_turn_scenarios_database_design",
        "single_turn_scenarios_performance_optimization",
        "single_turn_scenarios_full_stack",
        "single_turn_scenarios_testing_strategy",
        "single_turn_scenarios_security",
        "single_turn_scenarios_python",
        "single_turn_scenarios_intermediate",
        "single_turn_scenarios_minimal_context",
        
        # Multi-turn scenarios
        "multi_turn_scenarios.code_review_3_turn",
        "multi_turn_scenarios.iterative_problem_solving",
        "multi_turn_scenarios.teaching_dialogue",
        "multi_turn_scenarios.debugging_session",
        "multi_turn_scenarios.design_iteration",
        "multi_turn_scenarios.collaborative_development",
        "multi_turn_scenarios.requirements_refinement",
        "multi_turn_scenarios.performance_tuning",
        
        # Other custom tasks
        "multi_turn_coding_universal",
        "python_coding_suite"
    ]


if __name__ == '__main__':
    print("🚀 启动 EvaluationEngineV1.0 自定义任务 API 服务器...")
    print("📡 API 端点:")
    print("   GET  /health          - 健康检查")
    print("   GET  /tasks           - 列出可用任务")
    print("   GET  /engine/info     - 引擎信息")
    print("   POST /evaluate        - 启动评估")
    print("   GET  /status/<job_id> - 查看状态")
    print("   GET  /results/<job_id>- 获取结果")
    print("   GET  /jobs            - 列出任务")
    print("   GET  /demo            - 演示页面")
    print()
    print("🌐 演示页面: http://localhost:5000/demo")
    print("📚 框架: EvaluationEngineV1.0")
    print()
    
    # 检查环境
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  警告: 未设置 ANTHROPIC_API_KEY 环境变量")
    
    print(f"📋 可用任务数量: {len(get_available_tasks())}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)