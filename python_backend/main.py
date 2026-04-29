"""
FastAPI 主应用 —— 进化系统的外部接口
前端通过这里与闭环生命体交互
"""
import os
import sys
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 将当前目录加入路径
sys.path.insert(0, os.path.dirname(__file__))

from models import Species, CreateRequest, SpeciesSummary
from genesis import genesis
from evolution_loop import (
    run_evolution, save_species, load_species, 
    list_species, init_db, delete_species
)


# ========== 请求/响应模型 ==========

class CreateSpeciesRequest(BaseModel):
    goal: str = Field(description="用户目标描述")
    max_generations: int = Field(default=10, ge=1, le=50)
    fitness_threshold: float = Field(default=90.0, ge=0.0, le=100.0)


class EvolveRequest(BaseModel):
    species_id: str
    max_generations: int = 10
    fitness_threshold: float = 90.0


class EvolveResponse(BaseModel):
    species_id: str
    status: str
    message: str
    converged: bool


# ========== 生命周期 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    init_db()
    yield


app = FastAPI(
    title="Evolution Arena API",
    description="闭环自进化Agent系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API路由 ==========

@app.post("/api/species/create", response_model=dict)
async def create_species(request: CreateSpeciesRequest):
    """
    创世 —— 接收用户目标，生成第1代Agent拓扑
    """
    try:
        species = await genesis(request.goal)
        species.status = "created"
        save_species(species)
        
        return {
            "species_id": species.species_id,
            "generation": species.generation,
            "status": species.status,
            "agents": [{"id": a.id, "mind_model": a.mind_model.value} for a in species.agents],
            "topology": [{"from": e.from_node, "to": e.to_node} for e in species.topology]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创世失败: {str(e)}")


@app.post("/api/species/evolve", response_model=EvolveResponse)
async def evolve_species(request: EvolveRequest, background_tasks: BackgroundTasks):
    """
    启动进化循环 —— 在后台运行多代进化
    """
    species = load_species(request.species_id)
    if not species:
        raise HTTPException(status_code=404, detail=f"物种 {request.species_id} 不存在")
    
    # 在后台运行进化
    async def run_in_background():
        try:
            await run_evolution(
                species_id=request.species_id,
                max_generations=request.max_generations,
                fitness_threshold=request.fitness_threshold
            )
        except Exception as e:
            print(f"进化任务失败: {e}")
    
    background_tasks.add_task(run_in_background)
    
    return EvolveResponse(
        species_id=request.species_id,
        status="evolving",
        message=f"进化任务已启动，最多{request.max_generations}代",
        converged=False
    )


@app.get("/api/species/{species_id}", response_model=dict)
async def get_species(species_id: str):
    """
    获取物种完整信息（含基因、拓扑、历史）
    """
    species = load_species(species_id)
    if not species:
        raise HTTPException(status_code=404, detail=f"物种 {species_id} 不存在")
    
    return species.model_dump(by_alias=True)


@app.get("/api/species/{species_id}/generations", response_model=list)
async def get_generation_history(species_id: str):
    """
    获取物种的世代历史（用于前端时间轴）
    """
    species = load_species(species_id)
    if not species:
        raise HTTPException(status_code=404, detail=f"物种 {species_id} 不存在")
    
    return [
        {
            "gen": h.gen,
            "fitness": h.fitness,
            "bottleneck": h.bottleneck
        }
        for h in species.history
    ]


@app.get("/api/species", response_model=list[SpeciesSummary])
async def list_all_species():
    """
    列出所有物种摘要
    """
    species_list = list_species()
    return [
        SpeciesSummary(
            species_id=s["species_id"],
            generation=s["generation"],
            fitness=s["fitness"],
            status=s["status"],
            user_goal=s["user_goal"],
            agent_count=0  # 从data解析太复杂，前端可单独获取
        )
        for s in species_list
    ]


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "evolution-arena"}


@app.delete("/api/species/{species_id}")
async def remove_species(species_id: str):
    """
    删除物种——永久删除其基因库和进化历史
    """
    success = delete_species(species_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"物种 {species_id} 不存在")
    return {"deleted": True, "species_id": species_id}


@app.get("/api/species/{species_id}/export")
async def export_species(species_id: str):
    """
    导出物种完整基因——返回JSON下载
    """
    species = load_species(species_id)
    if not species:
        raise HTTPException(status_code=404, detail=f"物种 {species_id} 不存在")
    
    return {
        "species_id": species.species_id,
        "export_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "data": species.model_dump(by_alias=True)
    }


from datetime import datetime


# ========== 启动 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
