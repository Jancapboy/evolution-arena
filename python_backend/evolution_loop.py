"""
进化循环控制器 —— 管理整个闭环流程
控制节奏，判断收敛，防止无限循环
"""
import asyncio
import json
import os
import sqlite3
from typing import Optional, Callable
from datetime import datetime
from models import Species, EvolutionResult
from genesis import genesis
from executor import execute_generation
from evaluator import evaluate
from evolver import mutate


# ========== 数据库管理 ==========
DB_PATH = os.path.join(os.path.dirname(__file__), "evolution.db")


def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS species (
            species_id TEXT PRIMARY KEY,
            generation INTEGER,
            fitness REAL,
            status TEXT,
            user_goal TEXT,
            data TEXT,  -- JSON
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_species(species: Species):
    """保存物种到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    data_json = species.model_dump_json(by_alias=True)
    
    cursor.execute("""
        INSERT OR REPLACE INTO species 
        (species_id, generation, fitness, status, user_goal, data, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        species.species_id,
        species.generation,
        species.fitness,
        species.status,
        species.user_goal,
        data_json,
        now
    ))
    
    conn.commit()
    conn.close()


def load_species(species_id: str) -> Optional[Species]:
    """从数据库加载物种"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM species WHERE species_id = ?", (species_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Species.model_validate_json(row[0])
    return None


def list_species() -> list[dict]:
    """列出所有物种摘要"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT species_id, generation, fitness, status, user_goal, updated_at
        FROM species ORDER BY updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "species_id": r[0],
            "generation": r[1],
            "fitness": r[2],
            "status": r[3],
            "user_goal": r[4],
            "updated_at": r[5]
        }
        for r in rows
    ]


# ========== 进化循环 ==========

async def run_evolution(
    species_id: str,
    max_generations: int = 20,
    fitness_threshold: float = 90.0,
    stagnation_limit: int = 5,
    progress_callback: Optional[Callable[[Species, str], None]] = None
) -> EvolutionResult:
    """
    运行完整进化循环
    
    停止条件：
    - fitness > threshold 连续3代
    - 达到max_generations
    - fitness连续stagnation_limit代无提升（触发大变异）
    """
    species = load_species(species_id)
    if not species:
        return EvolutionResult(
            species=Species(species_id="", user_goal="", status="failed"),
            message=f"物种 {species_id} 不存在",
            converged=False
        )
    
    high_fitness_streak = 0
    last_fitness = 0.0
    stagnation_count = 0
    
    for gen in range(species.generation, max_generations + 1):
        if progress_callback:
            progress_callback(species, f"Generation {gen}: 执行中...")
        
        # 1. 执行
        try:
            species, context = await execute_generation(species)
            save_species(species)
        except Exception as e:
            species.status = "failed"
            save_species(species)
            return EvolutionResult(species=species, message=f"执行失败: {str(e)}", converged=False)
        
        if progress_callback:
            progress_callback(species, f"Generation {gen}: 评估中...")
        
        # 2. 评估
        try:
            species = await evaluate(species, context)
            save_species(species)
        except Exception as e:
            species.status = "failed"
            save_species(species)
            return EvolutionResult(species=species, message=f"评估失败: {str(e)}", converged=False)
        
        if progress_callback:
            progress_callback(species, f"Generation {gen}: fitness={species.fitness:.1f}")
        
        # 3. 检查收敛条件
        # 条件A: 高fitness连续3代
        if species.fitness >= fitness_threshold:
            high_fitness_streak += 1
            if high_fitness_streak >= 3:
                species.status = "converged"
                save_species(species)
                return EvolutionResult(
                    species=species,
                    message=f"收敛！连续{high_fitness_streak}代fitness>={fitness_threshold}",
                    converged=True
                )
        else:
            high_fitness_streak = 0
        
        # 条件B: 停滞检测 —— 连续N代fitness变化<5分才算停滞
        fitness_change = abs(species.fitness - last_fitness)
        if fitness_change < 5.0:
            stagnation_count += 1
            if stagnation_count >= stagnation_limit:
                if progress_callback:
                    progress_callback(species, f"Generation {gen}: 停滞检测(变化{fitness_change:.1f}分)，强制大变异！")
                stagnation_count = 0
        else:
            stagnation_count = 0
        
        last_fitness = species.fitness
        
        # 4. 进化（最后一代不进化）
        if gen < max_generations:
            diagnosis = species.latest_diagnosis or "{\"diagnosis\":\"无诊断\"}"
            
            # 如果停滞，在诊断中注入强制变异指令
            if stagnation_count >= stagnation_limit - 1:
                diagnosis += "\n[系统指令] 检测到进化停滞，请执行激进变异：同时ADD_AGENT和CHANGE_MIND_MODEL"
            
            if progress_callback:
                progress_callback(species, f"Generation {gen}: 进化中...")
            
            try:
                species = await mutate(species, diagnosis)
                save_species(species)
            except Exception as e:
                species.status = "failed"
                save_species(species)
                return EvolutionResult(species=species, message=f"进化失败: {str(e)}", converged=False)
        
        if progress_callback:
            progress_callback(species, f"Generation {gen}: 完成")
    
    # 达到最大代数
    species.status = "converged"
    save_species(species)
    return EvolutionResult(
        species=species,
        message=f"达到最大代数 {max_generations}",
        converged=True
    )


# 初始化数据库
init_db()
