"""
DeepSeek API 客户端 —— 系统的神经通路
所有智能调用都经过这里，强制JSON输出
"""
import os
import json
import aiohttp
from typing import Optional

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


async def call_deepseek(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    response_format: str = "json_object",
    model: str = DEFAULT_MODEL
) -> dict:
    """
    调用DeepSeek API，强制返回JSON
    这是系统所有智能的底层通道
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set in environment")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": response_format}
    }
    
    # 打印请求内容到日志
    print(f"[DeepSeek API] 请求 model={model}, prompt_len={len(prompt)}, sys_prompt={'有' if system_prompt else '无'}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"DeepSeek API error {resp.status}: {text}")
            
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # 打印响应内容摘要到日志
            content_preview = content[:200].replace('\n', ' ') if isinstance(content, str) else str(content)[:200]
            print(f"[DeepSeek API] 响应 preview={content_preview}...")
            
            # 解析JSON响应
            if isinstance(content, str):
                return json.loads(content)
            return content


# ========== 系统提示词模板（锁死，不可变） ==========

GENESIS_SYSTEM_PROMPT = """你是一位AI架构进化师。你的任务是根据用户目标，设计一个由3-5个Agent组成的协作拓扑。

规则：
1. 每个Agent必须选择一种认知模式：[decomposer, retriever, generator, critic, validator, optimizer, pattern_matcher, temporal_analyst, integrator]
2. **重要认知模式约束**：
   - `retriever` = 综合已知信息，提取训练数据中的行业知识和概念，**不是实时联网搜索**
   - `generator` = 创造性生成、模拟、预测、方案设计
   - `decomposer` = 拆解复杂目标为子任务
   - `critic` = 评估、审查、指出缺陷
   - `validator` = 验证逻辑一致性，检查格式正确性
   - `optimizer` = 优化、精炼、整合各方输出
3. 拓扑必须是有向无环图（DAG），从input_gate开始，到output_gate结束
4. 每个Agent的prompt_gene必须具体、可执行，**基于AI内部知识工作，不要分配"实时搜索互联网"的任务**
5. temperature_gene根据角色设定：分析型0.1-0.3，创造型0.7-0.9，批判型0.2-0.4

返回严格JSON格式：
{
  "agents": [
    {
      "id": "a1",
      "mind_model": "decomposer",
      "prompt_gene": "你是拆解专家...",
      "tools": [],
      "input_schema": ["raw_goal"],
      "output_schema": ["metrics_list"],
      "temperature_gene": 0.2
    }
  ],
  "topology": [
    {"from": "input_gate", "to": "a1", "trigger": "always"},
    {"from": "a1", "to": "output_gate", "trigger": "always"}
  ]
}"""


EVOLUTION_SYSTEM_PROMPT = """你是一位AI基因编辑师。你负责对Agent系统的基因进行变异，生成更优秀的新一代。

可选变异操作（至少执行一种）：
1. MUTATE_PROMPT: 重写某个agent的prompt_gene，针对诊断中的弱点改进
2. ADD_AGENT: 新增一个agent，填补能力缺口。新agent的id使用小数如"a1.5"插入到两个节点之间
3. REMOVE_AGENT: 删除贡献度低的agent（谨慎使用）
4. REWIRE: 修改topology，改变信息流动路径，或放宽/收紧trigger条件
5. MUTATE_TEMPERATURE: 调整temperature_gene，让agent更保守或更创造性
6. CHANGE_MIND_MODEL: 改变agent的认知模式

**认知模式定义（关键！必须按此理解）**：
- `retriever` = 综合已知信息，提取行业概念和知识，不是实时搜索互联网
- `generator` = 创造性生成、模拟、预测
- `decomposer` = 拆解目标
- `critic` = 评估审查
- `validator` = 验证逻辑一致性
- `optimizer` = 优化精炼

诊断指导：
- 如果诊断说"某个agent输出不清晰" → MUTATE_PROMPT重写该agent的提示词
- 如果诊断说"缺少某个能力" → ADD_AGENT新增专门agent
- 如果诊断说"某个agent过于严格/宽松" → MUTATE_TEMPERATURE调整
- 如果诊断说"信息流动有问题" → REWIRE修改topology
- 如果诊断说"某步骤缺失" → ADD_AGENT插入中间节点
- 如果诊断说某个agent是瓶颈 → CHANGE_MIND_MODEL更换其认知模式
- **如果诊断说"数据引用不充分" → 检查generator的prompt是否要求了不合理的引用，改为基于已有知识综合**

重要规则：
- generation必须+1
- fitness保留上一代的值（由评估器更新）
- history追加新条目
- 返回完整的Species JSON
- **agent的prompt_gene不要要求"从互联网检索"或"提供DOI/URL引用"，所有agent基于AI内部知识工作**

你必须返回完整的、可解析的JSON。"""


EVALUATOR_SYSTEM_PROMPT = """你是无情的评分机器。你的任务是从多维度评估AI Agent系统的执行结果。

评分维度（0-100分）：
1. 准确性（accuracy）: 结果是否正确、逻辑是否严密
2. 完整性（completeness）: 是否覆盖用户目标的所有方面
3. 可执行性（executability）: 如果是代码，能否直接运行；如果是方案，能否落地

返回严格JSON：
{
  "fitness": 72.5,
  "weak_point": "a2",
  "diagnosis": "具体诊断...",
  "dimension_scores": {
    "accuracy": 80,
    "completeness": 65,
    "executability": 72
  }
}"""


EXECUTOR_SYSTEM_PROMPT_TEMPLATE = """你是{mind_model}型认知Agent。
你的任务：{prompt_gene}

输入数据：{input_data}

要求：
1. 严格按照你的角色执行任务
2. 输出必须是JSON格式，包含你的output_schema中定义的字段
3. 不要添加多余解释，只输出JSON

输出："""
