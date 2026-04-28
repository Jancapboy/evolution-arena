"""
基因库核心模型 —— 整个进化系统的数据底层
这里的每一个字段都是可进化的"基因"
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class MindModel(str, Enum):
    """认知模式 —— 系统动态分配的思维策略"""
    DECOMPOSER = "decomposer"      # 拆解型：把问题转化为指标
    RETRIEVER = "retriever"        # 检索型：从外部获取信息
    GENERATOR = "generator"        # 创造型：生成方案/代码/内容
    CRITIC = "critic"              # 批判型：审计风险
    VALIDATOR = "validator"        # 验证型：检查正确性
    OPTIMIZER = "optimizer"        # 优化型：改进已有方案
    PATTERN_MATCHER = "pattern_matcher"  # 模式匹配型
    TEMPORAL_ANALYST = "temporal_analyst"  # 时序分析型
    INTEGRATOR = "integrator"      # 整合型：汇总多源信息


class Agent(BaseModel):
    """单个Agent的基因定义 —— 可完全由进化引擎修改"""
    id: str = Field(description="Agent唯一标识")
    mind_model: MindModel = Field(description="认知模式：决定这个Agent的思维类型")
    prompt_gene: str = Field(description="提示词基因：决定Agent的行为模式，可被进化重写")
    tools: list[str] = Field(default_factory=list, description="工具列表：如sql_query/python_exec")
    input_schema: list[str] = Field(default_factory=list, description="期望的输入数据类型")
    output_schema: list[str] = Field(default_factory=list, description="产出的输出数据类型")
    temperature_gene: float = Field(default=0.5, ge=0.0, le=2.0, description="创造性基因：0=保守，2=疯狂")


class TopologyEdge(BaseModel):
    """拓扑连接 —— 信息流动的神经通路，可被重连"""
    from_node: str = Field(alias="from", description="源节点ID")
    to_node: str = Field(alias="to", description="目标节点ID")
    trigger: str = Field(default="always", description="触发条件：如'risk_score < 0.3'")

    class Config:
        populate_by_name = True


class HistoryEntry(BaseModel):
    """进化历史记录 —— 用于分析进化轨迹"""
    gen: int = Field(description="世代号")
    fitness: float = Field(description="适应度得分")
    bottleneck: str = Field(description="本代瓶颈诊断")


class Species(BaseModel):
    """
    物种 —— 一个完整的可进化Agent系统
    这是系统的核心数据结构，全部存SQLite，全部是JSON
    """
    species_id: str = Field(description="物种唯一ID，如sales_predictor_v3")
    generation: int = Field(default=1, description="当前世代")
    fitness: float = Field(default=0.0, description="当前适应度 0-100")
    user_goal: str = Field(description="用户原始目标")
    
    agents: list[Agent] = Field(default_factory=list, description="Agent基因库")
    topology: list[TopologyEdge] = Field(default_factory=list, description="拓扑连接图")
    history: list[HistoryEntry] = Field(default_factory=list, description="进化历史")
    
    # 运行时状态（不存入基因库）
    status: Literal["created", "running", "evaluating", "evolving", "converged", "failed"] = "created"
    latest_result: Optional[str] = Field(default=None, description="最新执行结果")
    latest_diagnosis: Optional[str] = Field(default=None, description="最新评估诊断")
    
    class Config:
        populate_by_name = True


class EvolutionResult(BaseModel):
    """单次进化循环的结果"""
    species: Species
    message: str
    converged: bool = False


class CreateRequest(BaseModel):
    """用户创建新物种的请求"""
    goal: str = Field(description="用户目标描述")
    max_generations: int = Field(default=20, ge=1, le=100)
    fitness_threshold: float = Field(default=90.0, ge=0.0, le=100.0)


class SpeciesSummary(BaseModel):
    """物种列表的摘要信息"""
    species_id: str
    generation: int
    fitness: float
    status: str
    user_goal: str
    agent_count: int
    created_at: Optional[str] = None
