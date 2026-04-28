"""
模拟模式 —— 当没有DeepSeek API Key时，使用预定义数据展示系统流程
这让用户可以在填入API Key前体验完整界面
"""
import uuid
import json
from models import Species, Agent, TopologyEdge, HistoryEntry


def create_mock_species(user_goal: str) -> Species:
    """创建一个模拟物种，展示销售数据分析任务的Agent拓扑"""
    
    species_id = f"species_{uuid.uuid4().hex[:8]}"
    
    agents = [
        Agent(
            id="a1",
            mind_model="decomposer",
            prompt_gene="你是数据拆解专家。将用户的业务目标分解为可量化的数据指标。输出必须包含：关键指标列表、数据来源建议、分析维度。用中文回答。",
            tools=["sql_query"],
            input_schema=["raw_goal"],
            output_schema=["metrics_list", "data_sources"],
            temperature_gene=0.2
        ),
        Agent(
            id="a2",
            mind_model="retriever",
            prompt_gene="你是数据检索专家。根据指标列表从数据库中提取相关数据。使用SQL查询数据，返回结构化的数据表。用中文回答。",
            tools=["sql_query", "data_fetcher"],
            input_schema=["metrics_list", "data_sources"],
            output_schema=["raw_data", "data_summary"],
            temperature_gene=0.3
        ),
        Agent(
            id="a3",
            mind_model="temporal_analyst",
            prompt_gene="你是时序分析专家。识别数据中的季节性模式、趋势和周期性。特别关注Q4数据的时间特征。用中文回答。",
            tools=["python_exec"],
            input_schema=["raw_data", "data_summary"],
            output_schema=["seasonal_patterns", "trend_analysis"],
            temperature_gene=0.4
        ),
        Agent(
            id="a4",
            mind_model="generator",
            prompt_gene="你是预测模型专家。基于历史数据和时序分析，生成3种不同的下季度预测方案。每种方案需包含：预测方法、预期结果、置信度。用中文回答。",
            tools=["python_exec", "ml_models"],
            input_schema=["seasonal_patterns", "trend_analysis"],
            output_schema=["prediction_models", "forecasts"],
            temperature_gene=0.8
        ),
        Agent(
            id="a5",
            mind_model="critic",
            prompt_gene="你是严格的模型审计员。评估每个预测方案的风险：过拟合风险、数据偏差、假设合理性。给出风险评分(0-1)和改进建议。用中文回答。",
            tools=[],
            input_schema=["prediction_models", "forecasts"],
            output_schema=["risk_scores", "suggestions"],
            temperature_gene=0.2
        )
    ]
    
    topology = [
        TopologyEdge(from_node="input_gate", to_node="a1", trigger="always"),
        TopologyEdge(from_node="a1", to_node="a2", trigger="metrics_list.length > 0"),
        TopologyEdge(from_node="a2", to_node="a3", trigger="raw_data != null"),
        TopologyEdge(from_node="a3", to_node="a4", trigger="always"),
        TopologyEdge(from_node="a4", to_node="a5", trigger="always"),
        TopologyEdge(from_node="a5", to_node="output_gate", trigger="risk_score < 0.5")
    ]
    
    return Species(
        species_id=species_id,
        generation=1,
        fitness=0.0,
        user_goal=user_goal,
        agents=agents,
        topology=topology,
        history=[
            HistoryEntry(gen=1, fitness=0.0, bottleneck="初始创建，尚未执行")
        ],
        status="created"
    )


def mock_evolve(species: Species) -> Species:
    """模拟进化 —— 基于当前代生成下一代的模拟数据"""
    import copy
    new_species = copy.deepcopy(species)
    new_species.generation += 1
    
    # 模拟fitness提升
    fitness_gains = [15, 22, 18, 12, 8, 5, 3, 2, 1, 0]
    gen_idx = min(species.generation - 1, len(fitness_gains) - 1)
    new_species.fitness = min(species.fitness + fitness_gains[gen_idx], 95)
    
    # 模拟诊断
    diagnoses = [
        ("a1", "a1的指标拆解不够具体，缺少时间维度"),
        ("a2", "a2的数据查询范围过宽，需要增加筛选条件"),
        ("a3", "a3发现了明显的季节性模式但Q4数据不完整"),
        ("a4", "a4的预测模型可以考虑加入外部因素"),
        ("a5", "a5的风险评估过于保守，部分可行方案被误杀"),
        ("a4", "a4的第三个方案置信度过低"),
        ("a2", "a2的数据提取速度可以优化"),
        ("a1", "a1输出格式需要标准化"),
        ("a3", "时序分析的窗口大小需要调整"),
        ("system", "各代表现稳定，接近收敛")
    ]
    
    d_idx = min(species.generation - 1, len(diagnoses) - 1)
    weak_point, diagnosis = diagnoses[d_idx]
    
    new_species.latest_diagnosis = json.dumps({
        "fitness": new_species.fitness,
        "weak_point": weak_point,
        "diagnosis": diagnosis,
        "dimension_scores": {
            "accuracy": min(50 + new_species.fitness * 0.4, 95),
            "completeness": min(40 + new_species.fitness * 0.5, 92),
            "executability": min(60 + new_species.fitness * 0.3, 90)
        }
    }, ensure_ascii=False)
    
    # 模拟历史
    new_species.history.append(HistoryEntry(
        gen=new_species.generation,
        fitness=new_species.fitness,
        bottleneck=diagnosis
    ))
    
    # 模拟进化变异：修改某个agent的prompt
    if new_species.generation <= 5:
        # 前期：重写a2的prompt
        for agent in new_species.agents:
            if agent.id == "a2":
                agent.prompt_gene += "\n[进化备注] 已优化查询策略，增加数据筛选和时间范围限定。"
                agent.temperature_gene = min(agent.temperature_gene + 0.1, 1.0)
    elif new_species.generation <= 8:
        # 中期：插入新agent a3.5
        if not any(a.id == "a3.5" for a in new_species.agents):
            new_agent = Agent(
                id="a3.5",
                mind_model="pattern_matcher",
                prompt_gene="你是模式匹配专家。识别历史数据中的重复模式，为预测模型提供特征工程支持。用中文回答。",
                tools=["python_exec"],
                input_schema=["raw_data"],
                output_schema=["patterns", "features"],
                temperature_gene=0.5
            )
            new_species.agents.insert(3, new_agent)
            # 更新topology
            new_species.topology = [
                t for t in new_species.topology 
                if not (t.from_node == "a3" and t.to_node == "a4")
            ]
            new_species.topology.extend([
                TopologyEdge(from_node="a3", to_node="a3.5", trigger="always"),
                TopologyEdge(from_node="a3.5", to_node="a4", trigger="always")
            ])
    else:
        # 后期：微调所有agent
        for agent in new_species.agents:
            agent.prompt_gene += f"\n[第{new_species.generation}代优化] 根据历史表现持续改进。"
    
    # 模拟结果
    new_species.latest_result = json.dumps({
        "generation": new_species.generation,
        "fitness": new_species.fitness,
        "predictions": [
            {"method": "ARIMA", "q1_forecast": "¥2.4M", "confidence": 0.82},
            {"method": "Prophet", "q1_forecast": "¥2.6M", "confidence": 0.78},
            {"method": "LSTM", "q1_forecast": "¥2.5M", "confidence": 0.71}
        ],
        "key_insight": "Q4促销活动带动销售增长35%，预计Q1季节性回落后恢复平稳增长",
        "risk_flags": ["春节物流影响", "竞品价格战"] if new_species.generation < 5 else []
    }, ensure_ascii=False)
    
    return new_species


def mock_evaluate(species: Species) -> Species:
    """模拟评估 —— 给出一个合理的fitness分数"""
    import random
    random.seed(species.generation * 100)
    
    base_scores = [25, 45, 58, 68, 75, 82, 87, 90, 93, 95]
    idx = min(species.generation - 1, len(base_scores) - 1)
    species.fitness = base_scores[idx] + random.randint(-3, 3)
    species.fitness = max(0, min(100, species.fitness))
    
    weak_points = ["a1", "a2", "a3", "a4", "a5", "system"]
    diagnoses = [
        "指标拆解不够细，缺少维度细分",
        "数据查询结果包含噪声",
        "季节性检测精度待提升", 
        "预测模型欠拟合",
        "风险评估过于严格",
        "整体流程顺畅，接近最优"
    ]
    
    wp = weak_points[idx % len(weak_points)]
    diag = diagnoses[idx % len(diagnoses)]
    
    species.latest_diagnosis = json.dumps({
        "fitness": species.fitness,
        "weak_point": wp,
        "diagnosis": diag,
        "dimension_scores": {
            "accuracy": min(40 + species.fitness * 0.5, 95),
            "completeness": min(35 + species.fitness * 0.55, 92),
            "executability": min(50 + species.fitness * 0.4, 90)
        }
    }, ensure_ascii=False)
    
    if species.history:
        species.history[-1].fitness = species.fitness
        species.history[-1].bottleneck = diag
    
    return species
