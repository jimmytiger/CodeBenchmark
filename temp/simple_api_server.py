#!/usr/bin/env python3
"""
简化版API服务器 - 用于快速测试和演示
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime
import jwt
import secrets

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 简化的数据模型
class LoginRequest(BaseModel):
    username: str
    password: str

class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]

class EvaluationRequest(BaseModel):
    model_id: str
    task_ids: List[str]
    configuration: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class EvaluationResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str
    created_at: datetime

# 简化的认证管理器
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
        """验证用户"""
        if username in self.users and self.users[username]["password"] == password:
            return self.users[username]
        return None
    
    def create_token(self, user: Dict[str, Any]) -> str:
        """创建JWT令牌"""
        payload = {
            "user_id": user["user_id"],
            "username": user.get("username", ""),
            "roles": user["roles"],
            "exp": datetime.utcnow().timestamp() + 3600  # 1小时过期
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if datetime.utcnow().timestamp() > payload["exp"]:
                return None
            return payload
        except:
            return None

# 创建FastAPI应用
app = FastAPI(
    title="AI Evaluation Engine API (简化版)",
    description="用于测试的简化版API服务器",
    version="1.0.0-simple"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化认证管理器
auth_manager = SimpleAuthManager()
security = HTTPBearer()

# 存储活跃的评估
active_evaluations = {}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-simple",
        "active_evaluations": len(active_evaluations)
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
    limit: int = 10,
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """获取任务列表"""
    # 模拟任务数据
    tasks = [
        {
            "task_id": "single_turn_scenarios_function_generation",
            "name": "Function Generation",
            "category": "single_turn",
            "difficulty": "intermediate",
            "description": "Generate Python functions based on specifications",
            "languages": ["python"],
            "tags": ["coding", "generation"],
            "estimated_duration": 30
        },
        {
            "task_id": "single_turn_scenarios_code_completion",
            "name": "Code Completion",
            "category": "single_turn", 
            "difficulty": "beginner",
            "description": "Complete partial code snippets",
            "languages": ["python", "javascript"],
            "tags": ["coding", "completion"],
            "estimated_duration": 20
        },
        {
            "task_id": "single_turn_scenarios_bug_fix",
            "name": "Bug Fix",
            "category": "single_turn",
            "difficulty": "advanced",
            "description": "Identify and fix bugs in code",
            "languages": ["python"],
            "tags": ["debugging", "analysis"],
            "estimated_duration": 45
        }
    ]
    
    # 应用过滤器
    if category:
        tasks = [t for t in tasks if t["category"] == category]
    
    return tasks[:limit]

@app.get("/models")
async def list_models(
    provider: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """获取模型列表"""
    models = [
        {
            "model_id": "claude-3-haiku",
            "name": "Claude 3 Haiku",
            "provider": "anthropic",
            "version": "20240307",
            "capabilities": ["text_generation", "code_completion"],
            "supported_tasks": ["single_turn_scenarios"],
            "rate_limits": {
                "requests_per_minute": 60,
                "tokens_per_minute": 100000
            },
            "cost_per_token": 0.00025
        },
        {
            "model_id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "openai",
            "version": "0125",
            "capabilities": ["text_generation", "code_completion"],
            "supported_tasks": ["single_turn_scenarios"],
            "rate_limits": {
                "requests_per_minute": 60,
                "tokens_per_minute": 90000
            },
            "cost_per_token": 0.0005
        }
    ]
    
    if provider:
        models = [m for m in models if m["provider"] == provider]
    
    return models

@app.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    request: EvaluationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """创建评估任务"""
    import uuid
    
    evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
    
    # 存储评估信息
    active_evaluations[evaluation_id] = {
        "status": "created",
        "model_id": request.model_id,
        "task_ids": request.task_ids,
        "configuration": request.configuration or {},
        "metadata": request.metadata or {},
        "user_id": current_user["user_id"],
        "created_at": datetime.utcnow(),
        "progress": 0.0
    }
    
    logger.info(f"Created evaluation {evaluation_id} for user {current_user['user_id']}")
    
    return EvaluationResponse(
        evaluation_id=evaluation_id,
        status="created",
        message="Evaluation created successfully",
        created_at=datetime.utcnow()
    )

@app.get("/evaluations/{evaluation_id}")
async def get_evaluation_status(
    evaluation_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取评估状态"""
    if evaluation_id not in active_evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    evaluation = active_evaluations[evaluation_id]
    
    return {
        "evaluation_id": evaluation_id,
        "status": evaluation["status"],
        "progress": evaluation.get("progress", 0.0),
        "model_id": evaluation["model_id"],
        "task_ids": evaluation["task_ids"],
        "created_at": evaluation["created_at"],
        "user_id": evaluation["user_id"]
    }

@app.get("/results/{evaluation_id}")
async def get_evaluation_results(
    evaluation_id: str,
    include_details: bool = False,
    current_user: Dict = Depends(get_current_user)
):
    """获取评估结果"""
    if evaluation_id not in active_evaluations:
        raise HTTPException(status_code=404, detail="Results not found")
    
    evaluation = active_evaluations[evaluation_id]
    
    # 模拟结果数据
    results = {
        "evaluation_id": evaluation_id,
        "model_id": evaluation["model_id"],
        "status": "completed",
        "task_results": [
            {
                "task_id": task_id,
                "status": "completed",
                "score": 0.85,
                "metrics": {
                    "accuracy": 0.8,
                    "completeness": 0.9,
                    "quality": 0.85
                },
                "execution_time": 30.5
            }
            for task_id in evaluation["task_ids"]
        ],
        "summary_metrics": {
            "overall_score": 0.85,
            "average_execution_time": 30.5
        },
        "completed_at": datetime.utcnow()
    }
    
    if include_details:
        for task_result in results["task_results"]:
            task_result["output"] = "# Generated code example\ndef example_function():\n    return 'Hello, World!'"
    
    return results

def main():
    """主函数"""
    logger.info("🚀 启动简化版 AI Evaluation Engine API 服务器")
    logger.info("=" * 60)
    
    logger.info("🌐 服务器配置:")
    logger.info(f"   - 主机: 0.0.0.0")
    logger.info(f"   - 端口: 8000")
    logger.info(f"   - API文档: http://localhost:8000/docs")
    logger.info(f"   - 健康检查: http://localhost:8000/health")
    
    logger.info("🔐 默认用户账号:")
    logger.info(f"   - 管理员: admin / admin123")
    logger.info(f"   - 评估员: evaluator / eval123")
    
    logger.info("🚀 启动服务器...")
    logger.info("按 Ctrl+C 停止服务器")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")

if __name__ == "__main__":
    main()