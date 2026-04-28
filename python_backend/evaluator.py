"""
评估引擎 (Evaluator) —— 元层面的评分机器
没有评估就没有进化。它是闭环的"牙齿"
"""
import os
import json
from models import Species
from deepseek_client import call_deepseek, EVALUATOR_SYSTEM_PROMPT
from executor import ExecutionContext


async def evaluate(species: Species, context) -> Species:
    """
    评估一代的执行结果
    如果API Key未设置，使用模拟评估
    """
    # 模拟模式
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import mock_evaluate
        return mock_evaluate(species)
    
    # 构建评估材料
    result_text = species.latest_result or "无结果"
    
    # 构建执行摘要
    execution_summary = []
    for log in context.execution_log:
        summary = f"Agent {log['agent_id']} ({log['mind_model']}): {log['status']}"
        if log.get("error_detail"):
            summary += f" - 错误: {log['error_detail']}"
        execution_summary.append(summary)
    
    execution_text = "\n".join(execution_summary)
    
    prompt = f"""
    用户目标：{species.user_goal}
    
    执行摘要：
    {execution_text}
    
    最终结果：
    {result_text[:3000]}  # 截断避免过长
    
    Agent拓扑：
    {json.dumps([{"id": a.id, "mind_model": a.mind_model.value, "prompt": a.prompt_gene[:100]} for a in species.agents], ensure_ascii=False)}
    
    请从以下维度评估：
    1. 准确性：结果是否正确、逻辑是否严密
    2. 完整性：是否覆盖用户目标的所有方面  
    3. 可执行性：如果是代码，能否直接运行；如果是方案，能否落地
    
    同时指出：
    - 最弱的环节是哪个Agent（weak_point）
    - 具体诊断（diagnosis）：为什么弱，怎么改进
    """
    
    try:
        result = await call_deepseek(
            prompt=prompt,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            temperature=0.3,  # 评估要冷静客观
            response_format="json_object"
        )
        
        # 解析评估结果
        fitness = result.get("fitness", 0.0)
        weak_point = result.get("weak_point", "unknown")
        diagnosis = result.get("diagnosis", "无诊断")
        dimension_scores = result.get("dimension_scores", {})
        
        # 确保fitness在合理范围
        fitness = max(0.0, min(100.0, float(fitness)))
        
        species.fitness = fitness
        species.latest_diagnosis = json.dumps({
            "weak_point": weak_point,
            "diagnosis": diagnosis,
            "dimension_scores": dimension_scores
        }, ensure_ascii=False)
        
    except Exception as e:
        # 评估失败，给一个低分但继续
        species.fitness = 10.0
        species.latest_diagnosis = json.dumps({
            "weak_point": "evaluator",
            "diagnosis": f"评估过程出错: {str(e)}",
            "dimension_scores": {"accuracy": 0, "completeness": 0, "executability": 0}
        }, ensure_ascii=False)
    
    return species
