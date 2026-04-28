"""
创世引擎 (Genesis) —— 将用户目标转化为初始Agent拓扑
这是生命的第一道火花
"""
import os
import uuid
from models import Species, Agent, TopologyEdge, HistoryEntry
from deepseek_client import call_deepseek, GENESIS_SYSTEM_PROMPT


async def genesis(user_goal: str) -> Species:
    """
    接收用户目标，调用DeepSeek生成初始Agent拓扑
    如果API Key未设置，使用模拟模式展示流程
    """
    # 检查API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import create_mock_species
        species = create_mock_species(user_goal)
        species.status = "created"
        return species
    
    species_id = f"species_{uuid.uuid4().hex[:8]}"
    
    prompt = f"""
    用户目标："{user_goal}"
    
    请设计一个Agent协作系统来完成这个目标。
    要求：
    1. 3-5个Agent，每个有明确的认知分工
    2. 拓扑必须是DAG，数据从input_gate流入，从output_gate流出
    3. Agent的prompt_gene必须包含具体的任务指令和约束
    4. 如果任务涉及代码生成，给对应agent配置"python_exec"工具
    5. 如果任务涉及数据分析，给对应agent配置"sql_query"或"data_analysis"工具
    
    返回严格JSON格式。
    """
    
    # 调用DeepSeek生成初始基因
    result = await call_deepseek(
        prompt=prompt,
        system_prompt=GENESIS_SYSTEM_PROMPT,
        temperature=0.7,
        response_format="json_object"
    )
    
    # 解析并构建Species
    agents_data = result.get("agents", [])
    topology_data = result.get("topology", [])
    
    agents = []
    for agent_data in agents_data:
        agents.append(Agent(
            id=agent_data["id"],
            mind_model=agent_data["mind_model"],
            prompt_gene=agent_data["prompt_gene"],
            tools=agent_data.get("tools", []),
            input_schema=agent_data.get("input_schema", []),
            output_schema=agent_data.get("output_schema", []),
            temperature_gene=agent_data.get("temperature_gene", 0.5)
        ))
    
    # 后处理：确保 retriever/pattern_matcher 有搜索工具
    search_minds = {"retriever", "pattern_matcher"}
    for agent in agents:
        if agent.mind_model.value in search_minds:
            if "sql_query" not in agent.tools:
                agent.tools.append("sql_query")
                print(f"[Genesis] 自动为 {agent.id}({agent.mind_model.value}) 添加 sql_query 工具")
    
    topology = []
    for edge_data in topology_data:
        topology.append(TopologyEdge(
            from_node=edge_data["from"],
            to_node=edge_data["to"],
            trigger=edge_data.get("trigger", "always")
        ))
    
    species = Species(
        species_id=species_id,
        generation=1,
        fitness=0.0,
        user_goal=user_goal,
        agents=agents,
        topology=topology,
        history=[HistoryEntry(
            gen=1,
            fitness=0.0,
            bottleneck="初始创建，尚未执行"
        )],
        status="created"
    )
    
    return species
