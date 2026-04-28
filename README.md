# Evolution Arena —— 闭环自进化Agent系统

这不是Dify那种开环管道。这是一个**能自己长脑子的闭环生命体**。

## 核心差别

| Dify | Evolution Arena |
|------|----------------|
| 工作流跑完就结束 | 输出反过来修改系统结构 |
| 节点固定不变 | 节点自动生成、增删、重连 |
| 提示词人工编写 | 提示词作为基因自动进化 |
| 一次执行 | 多代循环直到收敛 |

## 架构：四步闭环

```
用户目标 → [创世] → 初始Agent图 → [执行] → 结果 → [评估] → 得分 → [进化] → 新Agent图 → ...
                ↑___________________________________________________________↓
```

1. **创世(Genesis)**: DeepSeek根据用户目标生成3-5个Agent的协作拓扑
2. **执行(Execute)**: 按DAG拓扑串行运行所有Agent
3. **评估(Evaluate)**: 元层面评分，指出最薄弱环节
4. **进化(Evolve)**: DeepSeek充当基因编辑师，修改Agent的提示词、角色、连接关系

## 基因库数据结构

```json
{
  "species_id": "sales_predictor_v3",
  "generation": 3,
  "fitness": 87.5,
  "agents": [
    {
      "id": "a1",
      "mind_model": "decomposer",
      "prompt_gene": "你是拆解专家...",
      "tools": ["sql_query"],
      "temperature_gene": 0.2
    }
  ],
  "topology": [
    {"from": "input_gate", "to": "a1", "trigger": "always"}
  ]
}
```

## 快速开始

### 1. 设置API Key

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 2. 启动系统

```bash
./start.sh
```

访问 http://localhost:3000

### 3. 使用流程

1. 在左侧面板输入目标（如："分析Q4销售数据并预测下季度"）
2. 点击「生成初始Agent图」—— 系统自动创建第1代拓扑
3. 点击「启动进化」—— 系统开始多代进化循环
4. 观察右侧拓扑图的变化：节点变色、增删、连线重绘

## 技术栈

**前端**: React 19 + TypeScript + Vite + React Flow + Tailwind CSS
**后端**: Python + FastAPI + Pydantic + SQLite
**AI引擎**: DeepSeek API（强制JSON输出）

## 项目结构

```
├── src/
│   ├── pages/Arena.tsx          # 主竞技场页面
│   ├── components/
│   │   ├── TopologyViewer.tsx   # React Flow拓扑渲染
│   │   └── EvolutionPanel.tsx   # 控制面板
│   └── hooks/useApi.ts          # API服务层
├── python_backend/
│   ├── main.py                  # FastAPI入口
│   ├── models.py                # Pydantic基因库模型
│   ├── genesis.py               # 创世引擎
│   ├── executor.py              # 执行引擎
│   ├── evaluator.py             # 评估引擎
│   ├── evolver.py               # 进化引擎（闭环心脏）
│   ├── evolution_loop.py        # 循环控制器
│   └── deepseek_client.py       # DeepSeek API客户端
└── start.sh                     # 启动脚本
```

## 进化算子

系统支持6种变异操作：

1. **MUTATE_PROMPT**: 重写Agent的提示词基因
2. **ADD_AGENT**: 新增Agent（id使用小数如a1.5）
3. **REMOVE_AGENT**: 删除低贡献Agent
4. **REWIRE**: 修改拓扑连接关系
5. **MUTATE_TEMPERATURE**: 调整创造性参数
6. **CHANGE_MIND_MODEL**: 改变认知模式

## 停止条件

- fitness > 90 连续3代
- 达到最大代数（默认20代）
- fitness连续5代无提升（触发强制大变异）

## 认知模式

decomposer, retriever, generator, critic, validator, optimizer, pattern_matcher, temporal_analyst, integrator
