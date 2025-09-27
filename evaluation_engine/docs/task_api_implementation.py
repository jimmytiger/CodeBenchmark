#!/usr/bin/env python3
"""
任务配置API端点实现示例

这个文件展示了如何实现任务配置相关的API端点，包括：
1. 任务发现和查询
2. 自定义任务创建
3. 任务配置管理
4. 任务验证和测试
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json
import logging
from pathlib import Path as FilePath

# 导入evaluation engine组件
from evaluation_engine.core.task_registration import ExtendedTaskRegistry, TaskMetadata, AdvancedTask
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.api.auth import AuthManager

logger = logging.getLogger(__name__)

# 创建路由器
task_router = APIRouter(prefix="/tasks", tags=["Task Management"])

# 初始化组件
task_registry = ExtendedTaskRegistry()
framework = UnifiedEvaluationFramework()
auth_manager = AuthManager()
security = HTTPBearer()


# Pydantic模型定义
class TaskConfigRequest(BaseModel):
    """任务配置请求模型"""
    task_id: str = Field(..., description="任务唯一标识符")
    name: str = Field(..., description="任务名称")
    category: str = Field(..., description="任务类别")
    difficulty: str = Field(..., description="难度级别")
    description: str = Field(..., description="任务描述")
    languages: List[str] = Field(default_factory=list, description="支持的编程语言")
    tags: List[str] = Field(default_factory=list, description="任务标签")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间(秒)")
    
    configuration: Dict[str, Any] = Field(..., description="任务配置")
    requirements: List[str] = Field(default_factory=list, description="任务要求")
    sample_data: List[Dict[str, Any]] = Field(default_factory=list, description="样本数据")
    
    @validator('task_id')
    def validate_task_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Task ID must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Task ID can only contain letters, numbers, hyphens, and underscores')
        return v


class TaskUpdateRequest(BaseModel):
    """任务更新请求模型"""
    configuration: Optional[Dict[str, Any]] = Field(None, description="更新的配置")
    requirements: Optional[List[str]] = Field(None, description="更新的要求")
    sample_data: Optional[List[Dict[str, Any]]] = Field(None, description="更新的样本数据")


class TaskValidationResponse(BaseModel):
    """任务验证响应模型"""
    is_valid: bool = Field(..., description="是否有效")
    validation_results: Dict[str, Any] = Field(..., description="验证结果详情")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    errors: List[str] = Field(default_factory=list, description="错误信息")


class TaskTestRequest(BaseModel):
    """任务测试请求模型"""
    sample_input: Dict[str, Any] = Field(..., description="测试输入")
    model_id: Optional[str] = Field("dummy", description="测试使用的模型")
    configuration: Optional[Dict[str, Any]] = Field(None, description="测试配置")


# API端点实现

@task_router.get("/", response_model=Dict[str, Any])
async def list_tasks(
    category: Optional[str] = Query(None, description="按类别筛选"),
    difficulty: Optional[str] = Query(None, description="按难度筛选"),
    language: Optional[str] = Query(None, description="按编程语言筛选"),
    tags: Optional[str] = Query(None, description="按标签筛选(逗号分隔)"),
    limit: int = Query(50, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    列出所有可用任务，支持筛选和分页
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 获取所有任务
        all_tasks = framework.list_available_tasks()
        
        # 应用筛选条件
        filtered_tasks = []
        for task_name in all_tasks:
            task_info = framework.get_task_info(task_name)
            if not task_info:
                continue
            
            # 类别筛选
            if category and task_info.get('metadata', {}).get('category') != category:
                continue
            
            # 难度筛选
            if difficulty and task_info.get('metadata', {}).get('difficulty') != difficulty:
                continue
            
            # 语言筛选
            if language:
                task_languages = task_info.get('metadata', {}).get('languages', [])
                if language not in task_languages:
                    continue
            
            # 标签筛选
            if tags:
                search_tags = [tag.strip() for tag in tags.split(',')]
                task_tags = task_info.get('metadata', {}).get('tags', [])
                if not any(tag in task_tags for tag in search_tags):
                    continue
            
            # 构建任务信息
            task_item = {
                "task_id": task_name,
                "name": task_info.get('metadata', {}).get('name', task_name),
                "category": task_info.get('metadata', {}).get('category', 'general'),
                "difficulty": task_info.get('metadata', {}).get('difficulty', 'intermediate'),
                "description": task_info.get('metadata', {}).get('description', ''),
                "languages": task_info.get('metadata', {}).get('languages', []),
                "tags": task_info.get('metadata', {}).get('tags', []),
                "estimated_duration": task_info.get('metadata', {}).get('estimated_time'),
                "available": task_info.get('available', False)
            }
            
            filtered_tasks.append(task_item)
        
        # 分页
        total = len(filtered_tasks)
        paginated_tasks = filtered_tasks[offset:offset + limit]
        
        return {
            "items": paginated_tasks,
            "total": total,
            "page": (offset // limit) + 1,
            "page_size": limit,
            "has_next": offset + limit < total,
            "has_previous": offset > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@task_router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_detail(
    task_id: str = Path(..., description="任务ID"),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取特定任务的详细信息
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 获取任务信息
        task_info = framework.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 获取任务元数据
        metadata = task_registry.get_task_metadata(task_id)
        scenario_config = task_registry.get_scenario_config(task_id)
        
        # 构建详细信息
        detail = {
            "task_id": task_id,
            "name": metadata.name if metadata else task_id,
            "category": metadata.category if metadata else "general",
            "difficulty": metadata.difficulty if metadata else "intermediate",
            "description": metadata.description if metadata else "",
            "languages": metadata.tags if metadata else [],
            "tags": metadata.tags if metadata else [],
            "estimated_duration": metadata.estimated_time if metadata else None,
            "available": task_info.get('available', False),
            "is_multi_turn": task_info.get('is_multi_turn', False),
            
            "requirements": [],
            "evaluation_criteria": [],
            "sample_input": None,
            "sample_output": None,
            "metrics": [],
            "dependencies": metadata.dependencies if metadata else []
        }
        
        # 添加场景配置信息
        if scenario_config:
            detail["scenario_config"] = {
                "scenario_type": scenario_config.scenario_type,
                "max_turns": scenario_config.max_turns,
                "conversation_timeout": scenario_config.conversation_timeout,
                "enable_context_retention": scenario_config.enable_context_retention,
                "scenario_metrics": scenario_config.scenario_metrics,
                "success_criteria": scenario_config.success_criteria
            }
        
        return detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get task detail")


@task_router.post("/custom", response_model=Dict[str, Any])
async def create_custom_task(
    task_config: TaskConfigRequest,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    创建自定义任务
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 检查任务ID是否已存在
        existing_task = framework.get_task_info(task_config.task_id)
        if existing_task and existing_task.get('available'):
            raise HTTPException(status_code=409, detail="Task ID already exists")
        
        # 创建任务元数据
        metadata = TaskMetadata(
            task_id=task_config.task_id,
            name=task_config.name,
            description=task_config.description,
            category=task_config.category,
            difficulty=task_config.difficulty,
            tags=task_config.tags,
            dependencies=[],
            estimated_time=task_config.estimated_duration
        )
        
        # 验证配置
        validation_result = _validate_task_configuration(task_config.configuration)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid configuration: {validation_result['errors']}"
            )
        
        # 创建任务类
        custom_task_class = _create_custom_task_class(task_config)
        
        # 注册任务
        task_registry.register_advanced_task(
            custom_task_class,
            task_config.task_id,
            metadata
        )
        
        # 保存任务配置到文件
        _save_task_configuration(task_config)
        
        logger.info(f"Created custom task: {task_config.task_id}")
        
        return {
            "task_id": task_config.task_id,
            "status": "created",
            "message": "Custom task created successfully",
            "validation_results": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create custom task")


@task_router.put("/{task_id}")
async def update_task_configuration(
    task_id: str = Path(..., description="任务ID"),
    update_request: TaskUpdateRequest = ...,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    更新任务配置
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 检查任务是否存在
        task_info = framework.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 加载现有配置
        config_file = FilePath(f"tasks/custom/{task_id}.json")
        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Task configuration not found")
        
        with open(config_file, 'r') as f:
            existing_config = json.load(f)
        
        # 更新配置
        if update_request.configuration:
            existing_config["configuration"].update(update_request.configuration)
        
        if update_request.requirements:
            existing_config["requirements"] = update_request.requirements
        
        if update_request.sample_data:
            existing_config["sample_data"] = update_request.sample_data
        
        # 验证更新后的配置
        validation_result = _validate_task_configuration(existing_config["configuration"])
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid updated configuration: {validation_result['errors']}"
            )
        
        # 保存更新后的配置
        with open(config_file, 'w') as f:
            json.dump(existing_config, f, indent=2)
        
        logger.info(f"Updated task configuration: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "updated",
            "message": "Task configuration updated successfully",
            "validation_results": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task configuration")


@task_router.post("/{task_id}/validate", response_model=TaskValidationResponse)
async def validate_task_configuration(
    task_id: str = Path(..., description="任务ID"),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    验证任务配置
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 检查任务是否存在
        task_info = framework.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 加载任务配置
        config_file = FilePath(f"tasks/custom/{task_id}.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                task_config = json.load(f)
        else:
            # 对于内置任务，使用默认验证
            task_config = {"configuration": {}}
        
        # 执行验证
        validation_results = {
            "dataset_accessible": True,
            "metrics_available": True,
            "dependencies_satisfied": True,
            "configuration_valid": True
        }
        
        warnings = []
        errors = []
        
        # 验证数据集
        if "dataset_config" in task_config.get("configuration", {}):
            dataset_path = task_config["configuration"]["dataset_config"].get("dataset_path")
            if dataset_path and not FilePath(dataset_path).exists():
                validation_results["dataset_accessible"] = False
                errors.append(f"Dataset file not found: {dataset_path}")
        
        # 验证生成配置
        if "generation_config" in task_config.get("configuration", {}):
            gen_config = task_config["configuration"]["generation_config"]
            
            # 检查温度设置
            temperature = gen_config.get("temperature", 0.7)
            if temperature < 0.1:
                warnings.append("Temperature is very low, may reduce creativity")
            elif temperature > 0.9:
                warnings.append("Temperature is very high, may reduce consistency")
            
            # 检查token限制
            max_tokens = gen_config.get("max_tokens", 2048)
            if max_tokens > 4000:
                warnings.append("Max tokens is very high, may increase cost and latency")
        
        # 验证依赖项
        metadata = task_registry.get_task_metadata(task_id)
        if metadata and metadata.dependencies:
            available_tasks = set(framework.list_available_tasks())
            missing_deps = set(metadata.dependencies) - available_tasks
            if missing_deps:
                validation_results["dependencies_satisfied"] = False
                errors.append(f"Missing dependencies: {list(missing_deps)}")
        
        is_valid = all(validation_results.values()) and len(errors) == 0
        
        return TaskValidationResponse(
            is_valid=is_valid,
            validation_results=validation_results,
            warnings=warnings,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating task configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate task configuration")


@task_router.post("/{task_id}/test")
async def test_task_configuration(
    task_id: str = Path(..., description="任务ID"),
    test_request: TaskTestRequest = ...,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    测试任务配置
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 检查任务是否存在
        task_info = framework.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 创建测试评估请求
        from evaluation_engine.core.unified_framework import EvaluationRequest
        
        test_config = test_request.configuration or {}
        
        eval_request = EvaluationRequest(
            model=test_request.model_id,
            tasks=[task_id],
            limit=1,
            gen_kwargs=test_config.get("generation_config", {}),
            predict_only=True,
            verbosity="INFO"
        )
        
        # 执行测试评估
        result = framework.evaluate(eval_request)
        
        # 构建测试结果
        test_result = {
            "task_id": task_id,
            "test_status": result.status.value,
            "execution_time": framework._calculate_execution_time(result),
            "sample_input": test_request.sample_input,
            "model_output": None,
            "error_message": result.error
        }
        
        # 如果评估成功，提取输出
        if result.status.value == "completed" and result.samples:
            if result.samples and len(result.samples) > 0:
                sample = result.samples[0]
                if 'resps' in sample and sample['resps']:
                    test_result["model_output"] = sample['resps'][0][0]
        
        return test_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing task configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test task configuration")


@task_router.delete("/{task_id}")
async def delete_custom_task(
    task_id: str = Path(..., description="任务ID"),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """
    删除自定义任务
    """
    try:
        # 验证认证
        user = await auth_manager.validate_token(auth.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # 检查是否为自定义任务
        config_file = FilePath(f"tasks/custom/{task_id}.json")
        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Custom task not found")
        
        # 删除配置文件
        config_file.unlink()
        
        # 从注册表中移除
        if task_id in task_registry.task_metadata:
            del task_registry.task_metadata[task_id]
        
        logger.info(f"Deleted custom task: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "deleted",
            "message": "Custom task deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting custom task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete custom task")


# 辅助函数

def _validate_task_configuration(configuration: Dict[str, Any]) -> Dict[str, Any]:
    """验证任务配置"""
    errors = []
    warnings = []
    
    # 验证数据集配置
    if "dataset_config" in configuration:
        dataset_config = configuration["dataset_config"]
        
        if "dataset_path" not in dataset_config:
            errors.append("Dataset path is required")
        
        if "sample_size" in dataset_config:
            sample_size = dataset_config["sample_size"]
            if not isinstance(sample_size, int) or sample_size <= 0:
                errors.append("Sample size must be a positive integer")
    
    # 验证评估配置
    if "evaluation_config" in configuration:
        eval_config = configuration["evaluation_config"]
        
        if "metrics" not in eval_config:
            errors.append("Metrics are required in evaluation config")
        
        if "evaluation_criteria" in eval_config:
            criteria = eval_config["evaluation_criteria"]
            total_weight = sum(
                criterion.get("weight", 0) 
                for criterion in criteria.values() 
                if isinstance(criterion, dict)
            )
            
            if abs(total_weight - 1.0) > 0.01:
                warnings.append(f"Evaluation criteria weights sum to {total_weight}, should be 1.0")
    
    # 验证生成配置
    if "generation_config" in configuration:
        gen_config = configuration["generation_config"]
        
        temperature = gen_config.get("temperature", 0.7)
        if not 0.0 <= temperature <= 2.0:
            errors.append("Temperature must be between 0.0 and 2.0")
        
        max_tokens = gen_config.get("max_tokens", 2048)
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            errors.append("Max tokens must be a positive integer")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def _create_custom_task_class(task_config: TaskConfigRequest) -> type:
    """创建自定义任务类"""
    
    class CustomTask(AdvancedTask):
        def __init__(self):
            super().__init__()
            self.task_id = task_config.task_id
            self.config = task_config.configuration
        
        def doc_to_text(self, doc):
            """将文档转换为文本"""
            if isinstance(doc, dict):
                return doc.get("prompt", doc.get("input", str(doc)))
            return str(doc)
        
        def doc_to_target(self, doc):
            """提取目标答案"""
            if isinstance(doc, dict):
                return doc.get("expected_output", doc.get("target", ""))
            return ""
        
        def construct_requests(self, doc, ctx):
            """构建请求"""
            # 这里可以根据任务配置自定义请求构建逻辑
            return super().construct_requests(doc, ctx)
    
    # 设置类名
    CustomTask.__name__ = f"CustomTask_{task_config.task_id}"
    CustomTask.__qualname__ = f"CustomTask_{task_config.task_id}"
    
    return CustomTask


def _save_task_configuration(task_config: TaskConfigRequest):
    """保存任务配置到文件"""
    config_dir = FilePath("tasks/custom")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / f"{task_config.task_id}.json"
    
    config_data = {
        "task_id": task_config.task_id,
        "name": task_config.name,
        "category": task_config.category,
        "difficulty": task_config.difficulty,
        "description": task_config.description,
        "languages": task_config.languages,
        "tags": task_config.tags,
        "estimated_duration": task_config.estimated_duration,
        "configuration": task_config.configuration,
        "requirements": task_config.requirements,
        "sample_data": task_config.sample_data,
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)


# 导出路由器
__all__ = ["task_router"]