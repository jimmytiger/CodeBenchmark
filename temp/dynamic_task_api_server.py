#!/usr/bin/env python3
"""
动态任务创建API服务器
支持通过API动态创建、注册和执行评估任务
"""

import os
import sys
import logging
import json
import uuid
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
import jwt
import secrets

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入核心组件
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework, 
    EvaluationRequest, 
    ExecutionStatus
)
from evaluation_engine.core.task_registration import (
    ExtendedTaskRegistry, 
    TaskMetadata, 
    ScenarioConfig,
    AdvancedTask
)

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

class DynamicTaskRequest(BaseModel):
    """动态任务创建请求"""
    task_id: str = Field(..., description="任务唯一标识符")
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    category: str = Field(..., description="任务类别")
    difficulty: str = Field(..., description="难度级别")
    tags: List[str] = Field(default=[], description="任务标签")
    
    # 任务配置
    task_config: Dict[str, Any] = Field(..., description="任务配置")
    
    # 可选的场景配置（用于多轮任务）
    scenario_config: Optional[Dict[str, Any]] = Field(None, description="场景配置")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str
    created_at: datetime

class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[Dict[str, Any]]
    total: int
    dynamic_tasks: int
    static_tasks: int

class EvaluationRequest(BaseModel):
    """评估请求"""
    model_id: str
    task_ids: List[str]
    configuration: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

# 简化的认证管理器
class SimpleAuthManager:
    def __init__(self):
        self.secret_key = secrets.token_urlsafe(32)
        self.users = {
            "admin": {
                "password": "admin123",
                "roles": ["admin"],
                "user_id": "admin_001"
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

# 动态任务管理器
class DynamicTaskManager:
    """动态任务管理器"""
    
    def __init__(self):
        self.unified_framework = UnifiedEvaluationFramework()
        self.task_registry = ExtendedTaskRegistry()
        self.dynamic_tasks: Dict[str, Dict[str, Any]] = {}
        self.tasks_dir = Path("dynamic_tasks")
        self.tasks_dir.mkdir(exist_ok=True)
        
        logger.info("动态任务管理器初始化完成")
    
    def create_dynamic_task(self, request: DynamicTaskRequest) -> str:
        """创建动态任务"""
        task_id = request.task_id
        
        # 检查任务是否已存在
        if task_id in self.dynamic_tasks:
            raise ValueError(f"任务 {task_id} 已存在")
        
        # 创建任务元数据
        metadata = TaskMetadata(
            task_id=task_id,
            name=request.name,
            description=request.description,
            category=request.category,
            difficulty=request.difficulty,
            tags=request.tags,
            version="1.0.0"
        )
        
        # 创建任务配置文件
        task_config = {
            "task": task_id,
            "metadata": {
                "name": request.name,
                "description": request.description,
                "category": request.category,
                "difficulty": request.difficulty,
                "tags": request.tags,
                "version": "1.0.0",
                "created_at": datetime.utcnow().isoformat()
            },
            **request.task_config
        }
        
        # 保存任务配置
        config_file = self.tasks_dir / f"{task_id}.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(task_config, f, default_flow_style=False)
        
        # 注册任务
        self.task_registry.register_advanced_task(
            AdvancedTask, 
            task_id, 
            metadata
        )
        
        # 存储动态任务信息
        self.dynamic_tasks[task_id] = {
            "task_id": task_id,
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "difficulty": request.difficulty,
            "tags": request.tags,
            "config_file": str(config_file),
            "created_at": datetime.utcnow(),
            "metadata": metadata,
            "task_config": task_config
        }
        
        logger.info(f"动态任务创建成功: {task_id}")
        return task_id
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务（静态+动态）"""
        # 获取静态任务
        static_tasks = self.unified_framework.list_available_tasks()
        
        # 获取动态任务
        dynamic_task_list = []
        for task_id, task_info in self.dynamic_tasks.items():
            dynamic_task_list.append({
                "task_id": task_id,
                "name": task_info["name"],
                "description": task_info["description"],
                "category": task_info["category"],
                "difficulty": task_info["difficulty"],
                "tags": task_info["tags"],
                "type": "dynamic",
                "created_at": task_info["created_at"].isoformat()
            })
        
        # 格式化静态任务
        static_task_list = []
        for task_id in static_tasks:
            static_task_list.append({
                "task_id": task_id,
                "name": task_id.replace("_", " ").title(),
                "description": f"Static task: {task_id}",
                "category": "static",
                "difficulty": "unknown",
                "tags": [],
                "type": "static"
            })
        
        return {
            "dynamic_tasks": dynamic_task_list,
            "static_tasks": static_task_list,
            "total_dynamic": len(dynamic_task_list),
            "total_static": len(static_task_list),
            "total": len(dynamic_task_list) + len(static_task_list)
        }
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详细信息"""
        if task_id in self.dynamic_tasks:
            return self.dynamic_tasks[task_id]
        else:
            # 尝试从静态任务获取
            task_info = self.unified_framework.get_task_info(task_id)
            return task_info
    
    def delete_dynamic_task(self, task_id: str) -> bool:
        """删除动态任务"""
        if task_id not in self.dynamic_tasks:
            return False
        
        # 删除配置文件
        config_file = Path(self.dynamic_tasks[task_id]["config_file"])
        if config_file.exists():
            config_file.unlink()
        
        # 从注册表中移除
        del self.dynamic_tasks[task_id]
        
        logger.info(f"动态任务删除成功: {task_id}")
        return True
    
    def execute_task(self, task_id: str, model_id: str, configuration: Dict[str, Any]) -> str:
        """执行任务"""
        # 创建评估请求
        evaluation_request = EvaluationRequest(
            model=model_id,
            tasks=[task_id],
            limit=configuration.get("limit", 1),
            gen_kwargs=configuration.get("gen_kwargs", {})
        )
        
        # 执行评估
        result = self.unified_framework.evaluate(evaluation_request)
        
        return result.evaluation_id

# 创建FastAPI应用
app = FastAPI(
    title="Dynamic Task Creation API",
    description="支持动态创建和管理评估任务的API服务器",
    version="1.0.0"
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
task_manager = DynamicTaskManager()
security = HTTPBearer()

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "features": ["dynamic_task_creation", "task_execution", "task_management"]
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

@app.post("/tasks", response_model=TaskResponse)
async def create_dynamic_task(
    request: DynamicTaskRequest,
    current_user: Dict = Depends(get_current_user)
):
    """动态创建任务"""
    try:
        task_id = task_manager.create_dynamic_task(request)
        
        return TaskResponse(
            task_id=task_id,
            status="created",
            message=f"动态任务 {task_id} 创建成功",
            created_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建动态任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks", response_model=TaskListResponse)
async def list_all_tasks(
    task_type: Optional[str] = None,
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """获取所有任务列表"""
    try:
        all_tasks = task_manager.get_all_tasks()
        
        # 合并任务列表
        tasks = all_tasks["dynamic_tasks"] + all_tasks["static_tasks"]
        
        # 应用过滤器
        if task_type:
            tasks = [t for t in tasks if t["type"] == task_type]
        
        if category:
            tasks = [t for t in tasks if t["category"] == category]
        
        return TaskListResponse(
            tasks=tasks,
            total=len(tasks),
            dynamic_tasks=all_tasks["total_dynamic"],
            static_tasks=all_tasks["total_static"]
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取任务详细信息"""
    try:
        task_info = task_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}")
async def delete_dynamic_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """删除动态任务"""
    try:
        success = task_manager.delete_dynamic_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="动态任务不存在")
        
        return {"message": f"动态任务 {task_id} 删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除动态任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    model_id: str,
    configuration: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """执行任务"""
    try:
        evaluation_id = task_manager.execute_task(task_id, model_id, configuration)
        
        return {
            "evaluation_id": evaluation_id,
            "task_id": task_id,
            "model_id": model_id,
            "status": "started",
            "message": "任务执行已启动"
        }
        
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """主函数"""
    logger.info("🚀 启动动态任务创建API服务器")
    logger.info("=" * 70)
    
    logger.info("🌐 服务器配置:")
    logger.info(f"   - 主机: 0.0.0.0")
    logger.info(f"   - 端口: 8000")
    logger.info(f"   - API文档: http://localhost:8000/docs")
    logger.info(f"   - 健康检查: http://localhost:8000/health")
    
    logger.info("🔐 默认用户账号:")
    logger.info(f"   - 管理员: admin / admin123")
    
    logger.info("✨ 支持的功能:")
    logger.info(f"   - 动态任务创建")
    logger.info(f"   - 任务管理和删除")
    logger.info(f"   - 任务执行")
    logger.info(f"   - 静态任务查询")
    
    logger.info("🚀 启动服务器...")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")

if __name__ == "__main__":
    main()