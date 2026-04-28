"""
执行引擎 (Executor) —— 按DAG拓扑顺序运行一代Agent
注意：必须串行执行，因为下游依赖上游输出
"""
import os
import json
import asyncio
from typing import Any
from models import Species, Agent, TopologyEdge
from deepseek_client import call_deepseek, EXECUTOR_SYSTEM_PROMPT_TEMPLATE


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


async def execute_agent(agent: Agent, input_data: dict) -> dict:
    """执行单个Agent，调用DeepSeek API"""
    # 构建执行提示词
    input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
    
    prompt = EXECUTOR_SYSTEM_PROMPT_TEMPLATE.format(
        mind_model=agent.mind_model.value,
        prompt_gene=agent.prompt_gene,
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
    """
    拓扑排序 —— 确保按DAG顺序执行
    返回按执行顺序排列的Agent列表
    """
    # 构建邻接表和入度表
    agent_map = {a.id: a for a in agents}
    in_degree = {a.id: 0 for a in agents}
    adj = {a.id: [] for a in agents}
    
    for edge in topology:
        if edge.from_node != "input_gate" and edge.to_node != "output_gate":
            if edge.from_node in agent_map and edge.to_node in agent_map:
                adj[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1
    
    # Kahn算法
    queue = [aid for aid, deg in in_degree.items() if deg == 0]
    sorted_ids = []
    
    while queue:
        # 按字母顺序稳定排序，确保确定性
        queue.sort()
        current = queue.pop(0)
        sorted_ids.append(current)
        
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(sorted_ids) != len(agents):
        # 有环或孤立节点，回退到原始顺序
        return agents
    
    return [agent_map[aid] for aid in sorted_ids]


async def execute_generation(species: Species) -> Species:
    """
    执行一代 —— 按拓扑顺序运行所有Agent
    如果API Key未设置，使用模拟数据
    """
    # 模拟模式
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import mock_evolve
        species = mock_evolve(species)
        species.status = "evaluating"
        return species, ExecutionContext()
    
    species.status = "running"
    context = ExecutionContext()
    context.data_store["__user_goal__"] = species.user_goal
    
    # 拓扑排序确定执行顺序
    execution_order = topological_sort(species.agents, species.topology)
    
    execution_log = []
    final_output = None
    
    for agent in execution_order:
        # 收集输入
        input_data = context.get_input_for_agent(agent, species.topology)
        
        # 执行Agent
        output = await execute_agent(agent, input_data)
        
        # 存储输出
        context.set_output(agent.id, output)
        
        # 处理输出可能是list或dict的情况
        is_error = isinstance(output, dict) and output.get("error")
        error_msg = output.get("message", "Unknown error") if isinstance(output, dict) else "Non-dict output"
        
        log_entry = {
            "agent_id": agent.id,
            "mind_model": agent.mind_model.value,
            "input": input_data,
            "output": output,
            "status": "error" if is_error else "success"
        }
        execution_log.append(log_entry)
        final_output = output
        
        # 如果有错误，标记但继续执行（让评估器判断影响）
        if is_error:
            execution_log[-1]["error_detail"] = error_msg
    
    # 汇总最终结果
    if final_output:
        species.latest_result = json.dumps(final_output, ensure_ascii=False, indent=2)
    else:
        species.latest_result = json.dumps({"error": "No agents executed"}, ensure_ascii=False)
    
    species.status = "evaluating"
    
    # 将执行日志存入上下文（评估器会使用）
    context.execution_log = execution_log
    
    return species, context
