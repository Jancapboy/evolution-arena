"""
评估引擎 (Evaluator) —— 元层面的评分机器
没有评估就没有进化。它是闭环的"牙齿"

ASI 改进：
1. 执行摘要包含每个agent的output摘要，评估器能看到retriever的搜索数据
2. 区分"有搜索数据"和"无搜索数据"的agent，针对性评估
3. 增加数据质量维度
"""
import os
import json
from models import Species
from deepseek_client import call_deepseek, EVALUATOR_SYSTEM_PROMPT
from executor import ExecutionContext


def _extract_output_summary(agent_id: str, output: dict, max_chars: int = 800) -> str:
    """从agent输出中提取关键摘要"""
    if not isinstance(output, dict):
        return str(output)[:max_chars]
    
    parts = []
    
    # 如果有search_results，提取摘要
    if "search_results" in output:
        sr = output["search_results"]
        if isinstance(sr, dict):
            cases = sr.get("cases", [])
            metrics = sr.get("key_metrics", {})
            sources = sr.get("sources", [])
            insights = sr.get("industry_insights", [])
            
            if cases:
                case_names = [c.get("company_or_source", "未知") for c in cases[:3]]
                parts.append(f"[搜索数据] 案例: {', '.join(case_names)}")
            if metrics:
                metric_preview = ", ".join([f"{k}={v}" for k, v in list(metrics.items())[:3]])
                parts.append(f"[搜索数据] 指标: {metric_preview}")
            if sources:
                parts.append(f"[搜索数据] 来源数: {len(sources)}")
            if insights:
                parts.append(f"[搜索数据] 洞察: {insights[0][:100]}...")
            if sr.get("_extract_error"):
                parts.append(f"[搜索数据] 提取错误: {sr['_extract_error'][:100]}")
    
    # 提取其他关键字段（排除搜索数据避免重复）
    for key, value in output.items():
        if key in ("search_results", "error", "agent_id", "message"):
            continue
        val_str = str(value)
        if len(val_str) > 20:
            parts.append(f"{key}: {val_str[:200]}...")
        else:
            parts.append(f"{key}: {val_str}")
    
    summary = " | ".join(parts)
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    return summary if summary else "(无有效输出)"


def _build_search_quality_note(execution_log: list[dict]) -> str:
    """分析哪些agent使用了搜索，搜索质量如何"""
    notes = []
    for log in execution_log:
        output = log.get("output", {})
        if isinstance(output, dict) and "search_results" in output:
            sr = output["search_results"]
            if isinstance(sr, dict):
                cases = len(sr.get("cases", []))
                metrics = len(sr.get("key_metrics", {}))
                sources = len(sr.get("sources", []))
                has_error = bool(sr.get("_extract_error"))
                
                status = "✅" if cases > 0 or metrics > 0 else "⚠️"
                if has_error:
                    status = "❌"
                
                notes.append(
                    f"{status} Agent {log['agent_id']}({log['mind_model']}): "
                    f"{cases}案例,{metrics}指标,{sources}来源"
                )
    
    if notes:
        return "搜索数据质量:\n" + "\n".join(notes)
    return "无agent使用搜索工具"


async def evaluate(species: Species, context) -> Species:
    """评估一代的执行结果"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        from mock_mode import mock_evaluate
        return mock_evaluate(species)
    
    result_text = species.latest_result or "无结果"
    
    # 构建执行摘要（包含每个agent的输出摘要）
    execution_summary = []
    for log in context.execution_log:
        summary = f"Agent {log['agent_id']} ({log['mind_model']}): {log['status']}"
        if log.get("error_detail"):
            summary += f" - 错误: {log['error_detail']}"
        
        # 添加output摘要
        output_summary = _extract_output_summary(
            log['agent_id'],
            log.get("output", {}),
            max_chars=600
        )
        summary += f"\n  输出: {output_summary}"
        execution_summary.append(summary)
    
    execution_text = "\n\n".join(execution_summary)
    
    # 搜索数据质量分析
    search_quality = _build_search_quality_note(context.execution_log)
    
    # 构建评估prompt
    prompt = f"""
用户目标：{species.user_goal}

执行摘要（包含各Agent输出摘要）：
{execution_text}

搜索数据质量分析：
{search_quality}

最终结果（最后一个Agent的输出）：
{result_text[:4000]}

Agent拓扑：
{json.dumps([{"id": a.id, "mind_model": a.mind_model.value, "tools": a.tools} for a in species.agents], ensure_ascii=False)}

评估指南（重要）：
1. 准确性（accuracy）: 结果是否正确、逻辑是否严密。特别关注retriever/search类agent是否基于真实数据（search_results）作答，而非编造。
2. 完整性（completeness）: 是否覆盖用户目标的所有方面。
3. 可执行性（executability）: 方案能否落地。
4. 数据质量（data_quality）: retriever/pattern_matcher是否有效利用了search_results中的案例和指标？搜索数据是否被正确引用到最终输出中？

诊断规则：
- 如果retriever的search_results为空或很少 → 诊断"搜索数据不足，需扩大搜索范围或调整查询"
- 如果retriever有搜索数据但输出未引用 → 诊断"有数据但未有效利用，需调整prompt要求引用search_results"
- 如果generator输出与搜索数据矛盾 → 诊断"生成器未遵循搜索数据，需增强数据约束"
- 如果pattern_matcher仅给出模式名称而无AI增强细节 → 诊断"模式分析不够深入，需对比传统vs AI增强差异"

返回严格JSON：
{{
  "fitness": 评分,
  "weak_point": "最弱agent id",
  "diagnosis": "具体诊断，包含为什么弱和怎么改进",
  "dimension_scores": {{
    "accuracy": 0-100,
    "completeness": 0-100,
    "executability": 0-100,
    "data_quality": 0-100
  }}
}}
"""
    
    try:
        result = await call_deepseek(
            prompt=prompt,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            temperature=0.3,
            response_format="json_object"
        )
        
        fitness = result.get("fitness", 0.0)
        fitness = max(0.0, min(100.0, float(fitness)))
        
        species.fitness = fitness
        species.latest_diagnosis = json.dumps({
            "weak_point": result.get("weak_point", "unknown"),
            "diagnosis": result.get("diagnosis", "无诊断"),
            "dimension_scores": result.get("dimension_scores", {})
        }, ensure_ascii=False)
        
    except Exception as e:
        species.fitness = 10.0
        species.latest_diagnosis = json.dumps({
            "weak_point": "evaluator",
            "diagnosis": f"评估过程出错: {str(e)}",
            "dimension_scores": {"accuracy": 0, "completeness": 0, "executability": 0, "data_quality": 0}
        }, ensure_ascii=False)
    
    return species
