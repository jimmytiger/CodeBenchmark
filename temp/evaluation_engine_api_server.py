#!/usr/bin/env python3
"""
真正的Evaluation Engine API服务器
使用完整的Evaluation Engine架构，从API层到Core Layer的完整流程
"""

import os
import sys
import logging
import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import jwt
import secrets

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入Evaluation Engine核心组件
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework, 
    EvaluationRequest, 
    EvaluationResult,
    ExecutionStatus
)
from evaluation_engine.core.task_registration import ExtendedTaskRegistry, extended_registry
from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager
from evaluation_engine.core.analysis_engine import AnalysisEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API数据模型
class LoginRequest(BaseModel):
    username: str
    password: str

class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]

class APIEvaluationRequest(BaseModel):
    model_id: str
    task_ids: List[str]
    configuration: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class APIEvaluationResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str
    created_at: datetime

# 认证管理器
class SimpleAuthManager:
    def __init__(self):
        self.secret_key = secrets.token_urlsafe(32)
        self.users = {
            "admin": {
                "password": "admin123",
                "roles": ["admin"],
                "user_id": "admin_001"
            },
            "evaluator": {
                "password": "eval123", 
                "roles": ["evaluator"],
                "user_id": "eval_001"
            }
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        if username in self.users and self.users[username]["password"] == password:
            return self.users[username]
        return None
    
    def create_token(self, user: Dict[str, Any]) -> str:
        payload = {
            "user_id": user["user_id"],
            "username": user.get("username", ""),
            "roles": user["roles"],
            "exp": datetime.utcnow().timestamp() + 3600
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if datetime.utcnow().timestamp() > payload["exp"]:
                return None
            return payload
        except:
            return None

# Evaluation Engine集成管理器
class EvaluationEngineManager:
    """集成所有Evaluation Engine核心组件的管理器"""
    
    def __init__(self):
        logger.info("🔧 初始化Evaluation Engine核心组件...")
        
        # 初始化核心组件
        self.unified_framework = UnifiedEvaluationFramework()
        self.task_registry = ExtendedTaskRegistry()
        self.model_config_manager = AdvancedModelConfigurationManager()
        self.analysis_engine = AnalysisEngine()
        
        # 发现可用任务和模型
        self.available_tasks = self._discover_tasks()
        self.available_models = self._discover_models()
        
        logger.info(f"✅ 发现 {len(self.available_tasks)} 个任务")
        logger.info(f"✅ 发现 {len(self.available_models)} 个模型")
    
    def _discover_tasks(self) -> List[Dict[str, Any]]:
        """发现可用任务"""
        try:
            # 使用统一框架获取任务列表
            all_tasks = self.unified_framework.list_available_tasks()
            logger.info(f"发现所有任务数: {len(all_tasks)}")
            
            # 过滤single_turn_scenarios任务
            single_turn_tasks = [t for t in all_tasks if "single_turn_scenarios" in t]
            logger.info(f"过滤后single_turn任务数: {len(single_turn_tasks)}")
            
            # 如果没有single_turn_scenarios任务，使用一些通用任务
            if not single_turn_tasks:
                # 选择一些可用的任务作为示例
                sample_tasks = [t for t in all_tasks if any(keyword in t.lower() for keyword in 
                               ['function', 'code', 'bug', 'algorithm', 'api', 'system'])][:10]
                single_turn_tasks = sample_tasks
                logger.info(f"使用示例任务数: {len(single_turn_tasks)}")
            
            tasks = []
            for task_name in single_turn_tasks:
                # 获取任务详细信息
                task_info = self.unified_framework.get_task_info(task_name)
                
                # 构建任务元数据
                task_meta = {
                    "task_id": task_name,
                    "name": self._format_task_name(task_name),
                    "category": "single_turn" if "single_turn" in task_name else "general",
                    "difficulty": self._infer_difficulty(task_name),
                    "description": f"Evaluate {self._format_task_name(task_name)} capabilities",
                    "languages": ["python"],
                    "tags": ["coding", task_name.split("_")[-1] if "_" in task_name else task_name],
                    "estimated_duration": 60,
                    "available": task_info.get("available", True) if task_info else True,
                    "is_multi_turn": task_info.get("is_multi_turn", False) if task_info else False
                }
                tasks.append(task_meta)
            
            logger.info(f"最终构建任务数: {len(tasks)}")
            return tasks
            
        except Exception as e:
            logger.error(f"发现任务失败: {e}")
            return []
    
    def _discover_models(self) -> List[Dict[str, Any]]:
        """发现可用模型"""
        models = [
            {
                "model_id": "dummy",
                "name": "Dummy Model (测试用)",
                "provider": "lm-eval",
                "version": "1.0",
                "capabilities": ["text_generation", "code_completion"],
                "supported_tasks": ["single_turn_scenarios"],
                "rate_limits": {"requests_per_minute": 1000, "tokens_per_minute": 1000000},
                "cost_per_token": 0.0,
                "model_args": ""
            },
            {
                "model_id": "claude-local",
                "name": "Claude (Local)",
                "provider": "anthropic",
                "version": "3-haiku",
                "capabilities": ["text_generation", "code_completion"],
                "supported_tasks": ["single_turn_scenarios"],
                "rate_limits": {"requests_per_minute": 60, "tokens_per_minute": 100000},
                "cost_per_token": 0.00025,
                "model_args": "model=claude-3-haiku-20240307"
            },
            {
                "model_id": "openai-completions",
                "name": "GPT-3.5 Turbo",
                "provider": "openai",
                "version": "0125",
                "capabilities": ["text_generation", "code_completion"],
                "supported_tasks": ["single_turn_scenarios"],
                "rate_limits": {"requests_per_minute": 60, "tokens_per_minute": 90000},
                "cost_per_token": 0.0005,
                "model_args": "model=gpt-3.5-turbo"
            },
            {
                "model_id": "deepseek",
                "name": "DeepSeek Coder",
                "provider": "deepseek",
                "version": "latest",
                "capabilities": ["text_generation", "code_completion"],
                "supported_tasks": ["single_turn_scenarios"],
                "rate_limits": {"requests_per_minute": 100, "tokens_per_minute": 200000},
                "cost_per_token": 0.0001,
                "model_args": "model=deepseek-coder"
            }
        ]
        return models
    
    def _format_task_name(self, task_name: str) -> str:
        """格式化任务名称"""
        name = task_name.replace("single_turn_scenarios_", "").replace("_", " ").title()
        return name
    
    def _infer_difficulty(self, task_name: str) -> str:
        """推断任务难度"""
        difficulty_map = {
            "function_generation": "intermediate",
            "code_completion": "beginner", 
            "bug_fix": "advanced",
            "algorithm_implementation": "advanced",
            "api_design": "intermediate",
            "system_design": "expert",
            "security": "advanced",
            "database_design": "intermediate",
            "performance_optimization": "advanced",
            "full_stack": "expert",
            "testing_strategy": "intermediate",
            "documentation": "beginner",
            "code_translation": "intermediate"
        }
        
        for key, difficulty in difficulty_map.items():
            if key in task_name:
                return difficulty
        return "intermediate"
    
    async def create_evaluation(self, api_request: APIEvaluationRequest, user: Dict[str, Any]) -> str:
        """使用Evaluation Engine创建评估任务"""
        logger.info(f"🚀 创建评估任务 - 用户: {user['user_id']}")
        
        # 构建EvaluationRequest
        config = api_request.configuration or {}
        
        evaluation_request = EvaluationRequest(
            model=api_request.model_id,
            tasks=api_request.task_ids,
            limit=config.get("limit", 3),
            num_fewshot=config.get("num_fewshot", 0),
            batch_size=config.get("batch_size", 1),
            use_cache=config.get("use_cache", True),
            write_out=True,
            output_base_path=f"results/eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            log_samples=True,
            verbosity="INFO",
            gen_kwargs={
                "temperature": config.get("temperature", 0.7),
                "max_gen_toks": config.get("max_tokens", 1024)
            }
        )
        
        # 验证请求
        validation_issues = self.unified_framework.validate_evaluation_request(evaluation_request)
        if validation_issues:
            raise ValueError(f"验证失败: {'; '.join(validation_issues)}")
        
        # 使用统一框架执行评估
        logger.info("📊 使用UnifiedEvaluationFramework执行评估...")
        result = self.unified_framework.evaluate(evaluation_request)
        
        logger.info(f"✅ 评估任务创建完成: {result.evaluation_id}")
        return result.evaluation_id
    
    def get_evaluation_status(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """获取评估状态"""
        result = self.unified_framework.get_evaluation_status(evaluation_id)
        if not result:
            return None
        
        return {
            "evaluation_id": result.evaluation_id,
            "status": result.status.value,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "error": result.error,
            "progress": 1.0 if result.status == ExecutionStatus.COMPLETED else 0.5 if result.status == ExecutionStatus.RUNNING else 0.0
        }
    
    def get_evaluation_results(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """获取评估结果"""
        result = self.unified_framework.get_evaluation_status(evaluation_id)
        if not result or result.status != ExecutionStatus.COMPLETED:
            return None
        
        return {
            "evaluation_id": result.evaluation_id,
            "model_id": str(result.request.model),
            "task_results": self._format_task_results(result),
            "summary_metrics": result.metrics_summary or {},
            "analysis": result.analysis or {},
            "execution_time": self.unified_framework._calculate_execution_time(result),
            "completed_at": result.end_time,
            "raw_results": result.results
        }
    
    def _format_task_results(self, result: EvaluationResult) -> List[Dict[str, Any]]:
        """格式化任务结果"""
        task_results = []
        
        if result.results:
            for task_name, task_data in result.results.items():
                task_result = {
                    "task_id": task_name,
                    "status": "completed",
                    "metrics": {},
                    "execution_time": 0.0
                }
                
                # 提取指标
                if isinstance(task_data, dict):
                    for metric_name, metric_value in task_data.items():
                        if isinstance(metric_value, (int, float)):
                            task_result["metrics"][metric_name] = metric_value
                
                # 计算综合分数
                if task_result["metrics"]:
                    task_result["score"] = sum(task_result["metrics"].values()) / len(task_result["metrics"])
                else:
                    task_result["score"] = 0.0
                
                task_results.append(task_result)
        
        return task_results

# 创建FastAPI应用
app = FastAPI(
    title="Evaluation Engine API (完整架构版)",
    description="使用完整Evaluation Engine架构的API服务器",
    version="1.0.0-full"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
auth_manager = SimpleAuthManager()
evaluation_engine = EvaluationEngineManager()
security = HTTPBearer()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-full",
        "architecture": "complete_evaluation_engine",
        "components": {
            "unified_framework": "active",
            "task_registry": "active", 
            "model_config_manager": "active",
            "analysis_engine": "active"
        },
        "available_tasks": len(evaluation_engine.available_tasks),
        "available_models": len(evaluation_engine.available_models)
    }

@app.post("/auth/login", response_model=AuthToken)
async def login(credentials: LoginRequest):
    """用户登录"""
    user = auth_manager.authenticate(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth_manager.create_token(user)
    
    return AuthToken(
        access_token=access_token,
        expires_in=3600,
        user_info={
            "user_id": user["user_id"],
            "username": credentials.username,
            "roles": user["roles"]
        }
    )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    user = auth_manager.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.get("/tasks")
async def list_tasks(
    limit: int = 50,
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """获取任务列表（通过Evaluation Engine）"""
    tasks = evaluation_engine.available_tasks
    
    if category:
        tasks = [t for t in tasks if t["category"] == category]
    
    return tasks[:limit]

@app.get("/models")
async def list_models(
    provider: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """获取模型列表"""
    models = evaluation_engine.available_models
    
    if provider:
        models = [m for m in models if m["provider"] == provider]
    
    return models

@app.post("/evaluations", response_model=APIEvaluationResponse)
async def create_evaluation(
    request: APIEvaluationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """创建评估任务（使用完整的Evaluation Engine架构）"""
    logger.info(f"📥 收到评估请求 - 模型: {request.model_id}, 任务: {request.task_ids}")
    
    # 验证任务和模型
    available_task_ids = [t["task_id"] for t in evaluation_engine.available_tasks]
    available_model_ids = [m["model_id"] for m in evaluation_engine.available_models]
    
    invalid_tasks = [t for t in request.task_ids if t not in available_task_ids]
    if invalid_tasks:
        raise HTTPException(status_code=400, detail=f"Invalid tasks: {invalid_tasks}")
    
    if request.model_id not in available_model_ids:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model_id}")
    
    try:
        # 使用Evaluation Engine创建评估
        evaluation_id = await evaluation_engine.create_evaluation(request, current_user)
        
        return APIEvaluationResponse(
            evaluation_id=evaluation_id,
            status="completed",  # 同步执行，直接完成
            message="Evaluation completed using Evaluation Engine",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"创建评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluations/{evaluation_id}")
async def get_evaluation_status(
    evaluation_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取评估状态"""
    status = evaluation_engine.get_evaluation_status(evaluation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return status

@app.get("/results/{evaluation_id}")
async def get_evaluation_results(
    evaluation_id: str,
    include_details: bool = False,
    current_user: Dict = Depends(get_current_user)
):
    """获取评估结果"""
    results = evaluation_engine.get_evaluation_results(evaluation_id)
    if not results:
        raise HTTPException(status_code=404, detail="Results not found or evaluation not completed")
    
    if not include_details:
        # 移除详细输出
        results = results.copy()
        results.pop("raw_results", None)
        results.pop("analysis", None)
    
    return results

@app.get("/framework/info")
async def get_framework_info(current_user: Dict = Depends(get_current_user)):
    """获取Evaluation Engine框架信息"""
    return {
        "framework_version": "1.0.0",
        "components": {
            "unified_framework": {
                "class": "UnifiedEvaluationFramework",
                "active_evaluations": len(evaluation_engine.unified_framework.active_evaluations)
            },
            "task_registry": {
                "class": "ExtendedTaskRegistry", 
                "registered_tasks": len(evaluation_engine.task_registry.task_metadata)
            },
            "model_config_manager": {
                "class": "AdvancedModelConfigurationManager"
            },
            "analysis_engine": {
                "class": "AnalysisEngine"
            }
        },
        "architecture_layers": [
            "API Layer (FastAPI)",
            "Task Management Layer", 
            "Core Layer (UnifiedEvaluationFramework)",
            "Engine Layer (Prompt, Data, Metrics, Analysis, Sandbox)"
        ]
    }

def main():
    """主函数"""
    logger.info("🚀 启动完整架构的 Evaluation Engine API 服务器")
    logger.info("=" * 70)
    
    logger.info("🏗️ 架构层次:")
    logger.info("   1. API Layer - FastAPI REST接口")
    logger.info("   2. Task Management Layer - 任务和配置管理")
    logger.info("   3. Core Layer - UnifiedEvaluationFramework")
    logger.info("   4. Engine Layer - 各种专业引擎")
    
    logger.info("🌐 服务器配置:")
    logger.info(f"   - 主机: 0.0.0.0")
    logger.info(f"   - 端口: 8000")
    logger.info(f"   - API文档: http://localhost:8000/docs")
    logger.info(f"   - 健康检查: http://localhost:8000/health")
    logger.info(f"   - 框架信息: http://localhost:8000/framework/info")
    
    logger.info("🔐 默认用户账号:")
    logger.info(f"   - 管理员: admin / admin123")
    logger.info(f"   - 评估员: evaluator / eval123")
    
    logger.info("📋 核心组件状态:")
    logger.info(f"   - 可用任务: {len(evaluation_engine.available_tasks)}")
    logger.info(f"   - 可用模型: {len(evaluation_engine.available_models)}")
    
    logger.info("🚀 启动服务器...")
    logger.info("按 Ctrl+C 停止服务器")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")

if __name__ == "__main__":
    main()