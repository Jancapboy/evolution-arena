"""
进化引擎 (Evolver) —— 闭环的心脏
让DeepSeek基于诊断，修改物种基因
这个函数让系统第一次拥有了"自我修改"的能力
"""
import os
import json
import copy
from models import Species, Agent, TopologyEdge, HistoryEntry
from deepseek_client import call_deepseek, EVOLUTION_SYSTEM_PROMPT


async def mutate(species: Species, diagnosis: str) -> Species:
    """
    基因编辑 —— 基于诊断修改物种基因，生成新一代
    如果API Key未设置，使用模拟进化
    """
    # 模拟模式
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import mock_evolve
        new_species = mock_evolve(species)
        new_species.status = "created"
        return new_species
    
    # 深度复制当前物种（保留备份）
    species_json = species.model_dump(by_alias=True)
    
    # 清理运行时字段，只保留基因
    species_json.pop("status", None)
    species_json.pop("latest_result", None)
    species_json.pop("latest_diagnosis", None)
    
    prompt = f"""
    当前物种表现：{species.fitness}分
    诊断报告：{diagnosis}
    
    现有基因：
    {json.dumps(species_json, ensure_ascii=False, indent=2)}
    
    可选的认知模式（mind_model）必须从以下列表中选择：
    [decomposer, retriever, generator, critic, validator, optimizer, pattern_matcher, temporal_analyst, integrator]
    
    请执行以下至少一种变异：
    1. MUTATE_PROMPT: 重写某个agent的prompt_gene，针对诊断中的弱点改进
    2. ADD_AGENT: 新增一个agent，填补能力缺口。新agent的id使用小数如"a1.5"
    3. REMOVE_AGENT: 删除贡献度低的agent（谨慎使用，只有agent>=4时才考虑）
    4. REWIRE: 修改topology，改变信息流动，或放宽/收紧trigger条件
    5. MUTATE_TEMPERATURE: 调整temperature_gene（0.0-2.0）
    6. CHANGE_MIND_MODEL: 改变agent的认知模式（必须从上面的列表选）
    
    诊断指导（关键规则）：
    - 如果诊断说"某个agent输出不清晰" → MUTATE_PROMPT重写该agent的提示词
    - 如果诊断说"缺少某个能力" → ADD_AGENT新增专门agent
    - 如果诊断说"某个agent过于严格/宽松" → MUTATE_TEMPERATURE调整
    - 如果诊断说"信息流动有问题" → REWIRE修改topology
    - 如果诊断说"某步骤缺失" → ADD_AGENT插入中间节点
    - 如果诊断说某个agent是瓶颈 → CHANGE_MIND_MODEL更换其认知模式
    
    **搜索数据相关诊断（重要）：**
    - 如果诊断说"搜索数据不足/为空" → 检查retriever/pattern_matcher的tools是否包含sql_query，如没有则CHANGE_MIND_MODEL改为retriever并添加sql_query工具
    - 如果诊断说"有数据但未有效利用" → MUTATE_PROMPT让该agent明确要求"引用search_results.cases中的具体案例"和"使用search_results.key_metrics中的量化指标"
    - 如果诊断说"数据引用不充分" → 检查retriever的prompt是否明确要求引用search_results，如果没有则MUTATE_PROMPT添加引用要求
    - 如果诊断说"generator未遵循搜索数据" → MUTATE_PROMPT让generator明确要求"基于search_results中的数据生成方案，不得编造与搜索数据矛盾的内容"
    - 如果诊断说"缺乏量化指标" → MUTATE_PROMPT让retriever明确要求"从search_results中提取所有量化指标，整理为key-value格式输出"
    - 如果诊断说"缺乏行业案例" → MUTATE_PROMPT让retriever明确要求"从search_results.cases中提取至少3个具体案例，包含公司名称和效果数据"
    
    重要规则：
    - generation必须+1
    - 保留history并追加新条目（记录本代变异原因）
    - agents数量保持在2-6之间
    - 拓扑必须仍然是DAG（不能形成环）
    - mind_model必须从限定列表中选择
    - retriever/pattern_matcher 必须配置 ["sql_query"] 工具（系统会自动搜索互联网获取真实数据）
    - 返回完整的Species JSON
    - history新条目的bottleneck字段要记录具体变异原因
    """
    
    try:
        result = await call_deepseek(
            prompt=prompt,
            system_prompt=EVOLUTION_SYSTEM_PROMPT,
            temperature=0.8,  # 进化需要一定创造性
            response_format="json_object"
        )
        
        # 解析新的物种基因
        new_species = _parse_evolved_species(result, species, diagnosis)
        new_species.status = "created"
        
        return new_species
        
    except Exception as e:
        # 进化失败，回退到保守策略：只微调prompt
        return _fallback_mutation(species, diagnosis, str(e))


def _parse_evolved_species(data: dict, parent: Species, diagnosis: str = "") -> Species:
    """解析DeepSeek返回的进化后JSON"""
    agents_data = data.get("agents", [])
    topology_data = data.get("topology", [])
    generation = data.get("generation", parent.generation + 1)
    
    # 如果DeepSeek没正确增加generation，强制+1
    if generation <= parent.generation:
        generation = parent.generation + 1
    
    agents = []
    for agent_data in agents_data:
        agents.append(Agent(
            id=agent_data["id"],
            mind_model=agent_data.get("mind_model", "decomposer"),
            prompt_gene=agent_data.get("prompt_gene", "执行你的任务"),
            tools=agent_data.get("tools", []),
            input_schema=agent_data.get("input_schema", []),
            output_schema=agent_data.get("output_schema", []),
            temperature_gene=agent_data.get("temperature_gene", 0.5)
        ))
    
    topology = []
    for edge_data in topology_data:
        topology.append(TopologyEdge(
            from_node=edge_data.get("from", edge_data.get("from_node", "")),
            to_node=edge_data.get("to", edge_data.get("to_node", "")),
            trigger=edge_data.get("trigger", "always")
        ))
    
    # 保留历史，使用诊断信息作为瓶颈描述
    history = list(parent.history)
    bottleneck = data.get("mutation_note", "")
    if not bottleneck and diagnosis:
        diag_text = diagnosis.replace("\n", " ")[:60]
        bottleneck = f"针对: {diag_text}"
    elif not bottleneck:
        bottleneck = "基因变异"
    history.append(HistoryEntry(
        gen=generation,
        fitness=parent.fitness,
        bottleneck=bottleneck
    ))
    
    return Species(
        species_id=parent.species_id,
        generation=generation,
        fitness=0.0,  # 新世代需要重新评估
        user_goal=parent.user_goal,
        agents=agents,
        topology=topology,
        history=history
    )


def _fallback_mutation(species: Species, diagnosis: str, error_msg: str) -> Species:
    """
    保守回退策略 —— 当DeepSeek进化失败时使用
    只进行安全的微调，不改变结构
    """
    new_species = copy.deepcopy(species)
    new_species.generation += 1
    new_species.fitness = 0.0
    
    # 在每个agent的prompt末尾追加改进指令
    for agent in new_species.agents:
        agent.prompt_gene += f"\n\n[进化备注] 上一代问题: {diagnosis[:200]}。请特别注意改进。"
    
    new_species.history.append(HistoryEntry(
        gen=new_species.generation,
        fitness=species.fitness,
        bottleneck=f"保守变异（进化失败: {error_msg[:100]}）"
    ))
    
    new_species.status = "created"
    return new_species
