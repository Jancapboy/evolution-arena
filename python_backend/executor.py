"""
执行引擎 (Executor) —— 按DAG拓扑顺序运行一代Agent

ASI 核心改进：
1. 搜索查询构建：基于上游agent输出提取关键词，而非原始user_goal
2. 搜索后结构化：Tavily原始文本 → DeepSeek提取结构化数据 → 传给下游
3. 认知模式映射：retriever做数据检索，pattern_matcher做模式分析，generator做生成
"""
import os
import json
import asyncio
from typing import Any
from models import Species, Agent, TopologyEdge
from deepseek_client import call_deepseek, EXECUTOR_SYSTEM_PROMPT_TEMPLATE

# Tavily搜索（可选依赖）
try:
    from tavily_search import search_and_format
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class ExecutionContext:
    """执行上下文 —— 保存每个Agent的输出，供下游使用"""
    def __init__(self):
        self.data_store: dict[str, Any] = {}
        self.execution_log: list[dict] = []
    
    def set_output(self, agent_id: str, output: dict):
        self.data_store[agent_id] = output
    
    def get_input_for_agent(self, agent: Agent, topology: list[TopologyEdge]) -> dict:
        """根据拓扑，找到所有指向该agent的边，收集上游输出"""
        inputs = {}
        for edge in topology:
            if edge.to_node == agent.id:
                if edge.from_node == "input_gate":
                    inputs["raw_goal"] = self.data_store.get("__user_goal__", "")
                else:
                    upstream_output = self.data_store.get(edge.from_node, {})
                    if isinstance(upstream_output, dict):
                        inputs.update(upstream_output)
                    else:
                        inputs[edge.from_node] = upstream_output
        return inputs


def _build_search_query(user_goal: str, input_data: dict, agent: Agent) -> str:
    """
    构建精准搜索查询。
    策略：从上游agent输出中提取关键词，而非直接用user_goal。
    """
    # 如果上游agent输出了具体指标/维度，用它们构建搜索词
    keywords = []
    
    if isinstance(input_data, dict):
        # 提取JSON中的文本值
        for key, value in input_data.items():
            if isinstance(value, str) and len(value) < 100:
                keywords.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and len(item) < 50:
                        keywords.append(item)
                    elif isinstance(item, dict) and "name" in item:
                        keywords.append(str(item["name"]))
                    elif isinstance(item, dict) and "dimension" in item:
                        keywords.append(str(item["dimension"]))
    
    # 根据认知模式调整搜索意图
    mind = agent.mind_model.value
    intent_map = {
        "retriever": "具体案例 效果数据 量化指标",
        "pattern_matcher": "行业模式 最佳实践 技术方案",
        "generator": "技术架构 实施方案 路线图",
        "critic": "风险 局限性 挑战 成熟度",
        "validator": "验证方法 评估标准 基准数据",
        "optimizer": "优化策略 效率提升 成本降低"
    }
    intent = intent_map.get(mind, "案例 数据")
    
    # 构建搜索查询：用户目标 + 关键词 + 意图
    query_parts = [user_goal]
    if keywords:
        # 取前3个关键词，避免过长
        query_parts.append(" ".join(keywords[:3]))
    query_parts.append(intent)
    
    return " ".join(query_parts)


async def _structure_search_results(raw_text: str, user_goal: str) -> dict:
    """
    将Tavily原始文本结构化为下游agent可用的数据。
    使用DeepSeek从搜索结果中提取结构化信息。
    """
    system_prompt = """你是一位数据提取专家。从搜索结果中提取结构化信息。
必须返回严格JSON格式，包含以下字段：
{
  "cases": [
    {
      "company_or_source": "公司名称或报告来源",
      "description": "简要描述",
      "metrics": {"指标名": "数值"},
      "year": "年份（如有）"
    }
  ],
  "key_metrics": {"指标1": "数值或范围", "指标2": "数值"},
  "industry_insights": ["洞察1", "洞察2"],
  "sources": ["来源1", "来源2"]
}
如果没有具体数据，cases和key_metrics可以为空数组/对象，但sources必须列出。"""

    prompt = f"""
用户目标：{user_goal}

搜索结果：
{raw_text[:3000]}

请从上述搜索结果中提取结构化数据。"""

    try:
        result = await call_deepseek(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            response_format="json_object"
        )
        return result
    except Exception as e:
        print(f"[结构提取失败] {e}")
        return {
            "cases": [],
            "key_metrics": {},
            "industry_insights": [],
            "sources": [],
            "_extract_error": str(e)
        }


async def execute_agent(agent: Agent, input_data: dict, user_goal: str = "") -> dict:
    """执行单个Agent，调用DeepSeek API。如果agent配置了web_search/sql_query工具，先通过Tavily获取真实数据。"""
    
    # 检查是否需要Tavily搜索
    tools = agent.tools or []
    needs_search = any(t in tools for t in ["web_search", "tavily", "search", "sql_query"])
    
    structured_data = None
    search_raw = ""
    
    if needs_search and TAVILY_AVAILABLE and os.environ.get("TAVILY_API_KEY"):
        # 1. 构建精准搜索查询
        search_query = _build_search_query(user_goal, input_data, agent)
        
        try:
            print(f"[Tavily] Agent {agent.id}({agent.mind_model.value}) 搜索: {search_query[:120]}...")
            search_raw = await search_and_format(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_answer=True
            )
            print(f"[Tavily] 获取 {len(search_raw)} 字符")
            
            # 2. 将原始搜索结果结构化为JSON
            print(f"[Structuring] Agent {agent.id} 正在提取结构化数据...")
            structured_data = await _structure_search_results(search_raw, user_goal)
            case_count = len(structured_data.get("cases", []))
            metric_count = len(structured_data.get("key_metrics", {}))
            print(f"[Structured] 提取 {case_count} 个案例, {metric_count} 个指标")
            
        except Exception as e:
            print(f"[Tavily] 搜索或结构化失败: {e}")
            structured_data = {"_error": str(e), "cases": [], "key_metrics": {}}
    
    # 构建执行提示词
    input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
    
    # 3. 如果有结构化搜索数据，注入到input_data中作为独立字段
    if structured_data:
        # 把结构化数据作为"search_results"字段注入input_data
        # 这样agent的prompt里可以直接引用
        injected_input = dict(input_data) if isinstance(input_data, dict) else {"_raw_input": input_data}
        injected_input["search_results"] = structured_data
        input_json = json.dumps(injected_input, ensure_ascii=False, indent=2)
        
        # 在prompt_gene后面追加指令，让agent知道有搜索数据可用
        enhanced_prompt = agent.prompt_gene + """

[系统注入 —— 搜索数据]
以下是通过Tavily互联网搜索获取的真实数据，已结构化为JSON。
请基于这些数据作答，不要编造。如果搜索数据不足以回答某部分，如实说明"搜索结果未提供"。

搜索数据字段说明：
- search_results.cases: 具体案例列表
- search_results.key_metrics: 关键量化指标
- search_results.industry_insights: 行业洞察
- search_results.sources: 数据来源
"""
    else:
        enhanced_prompt = agent.prompt_gene
    
    prompt = EXECUTOR_SYSTEM_PROMPT_TEMPLATE.format(
        mind_model=agent.mind_model.value,
        prompt_gene=enhanced_prompt,
        input_data=input_json
    )
    
    try:
        result = await call_deepseek(
            prompt=prompt,
            temperature=agent.temperature_gene,
            response_format="json_object"
        )
        return result
    except Exception as e:
        return {
            "error": True,
            "agent_id": agent.id,
            "message": str(e),
            "output": {}
        }


def topological_sort(agents: list[Agent], topology: list[TopologyEdge]) -> list[Agent]:
    """拓扑排序 —— 确保按DAG顺序执行"""
    agent_map = {a.id: a for a in agents}
    in_degree = {a.id: 0 for a in agents}
    adj = {a.id: [] for a in agents}
    
    for edge in topology:
        if edge.from_node != "input_gate" and edge.to_node != "output_gate":
            if edge.from_node in agent_map and edge.to_node in agent_map:
                adj[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1
    
    queue = [aid for aid, deg in in_degree.items() if deg == 0]
    sorted_ids = []
    
    while queue:
        queue.sort()
        current = queue.pop(0)
        sorted_ids.append(current)
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(sorted_ids) != len(agents):
        return agents
    
    return [agent_map[aid] for aid in sorted_ids]


async def execute_generation(species: Species) -> tuple[Species, ExecutionContext]:
    """执行一代 —— 按拓扑顺序运行所有Agent"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import mock_evolve
        species = mock_evolve(species)
        species.status = "evaluating"
        return species, ExecutionContext()
    
    species.status = "running"
    context = ExecutionContext()
    context.data_store["__user_goal__"] = species.user_goal
    
    execution_order = topological_sort(species.agents, species.topology)
    execution_log = []
    final_output = None
    
    for agent in execution_order:
        input_data = context.get_input_for_agent(agent, species.topology)
        output = await execute_agent(agent, input_data, species.user_goal)
        
        context.set_output(agent.id, output)
        
        is_error = isinstance(output, dict) and output.get("error")
        error_msg = output.get("message", "Unknown error") if isinstance(output, dict) else "Non-dict output"
        
        log_entry = {
            "agent_id": agent.id,
            "mind_model": agent.mind_model.value,
            "input": input_data,
            "output": output,
            "status": "error" if is_error else "success"
        }
        if is_error:
            log_entry["error_detail"] = error_msg
        
        execution_log.append(log_entry)
        final_output = output
    
    if final_output:
        species.latest_result = json.dumps(final_output, ensure_ascii=False, indent=2)
    else:
        species.latest_result = json.dumps({"error": "No agents executed"}, ensure_ascii=False)
    
    species.status = "evaluating"
    context.execution_log = execution_log
    
    return species, context
