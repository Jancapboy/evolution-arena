// 拓扑可视化 —— React Flow渲染的Agent神经网络
// 只读模式：用户不能拖动节点，只能观测系统自动生成的图

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface Agent {
  id: string;
  mind_model: string;
  prompt_gene: string;
  tools: string[];
  temperature_gene: number;
}

interface TopologyEdge {
  from: string;
  to: string;
  trigger: string;
}

interface TopologyViewerProps {
  agents: Agent[];
  topology: TopologyEdge[];
  weakPoint?: string; // 最弱环节高亮
  isEvolving?: boolean; // 是否显示进化动画效果
  onNodeClick?: (agent: Agent) => void; // 点击节点回调
}

// 认知模式配色 —— 赛博朋克风格
const MIND_MODEL_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  decomposer: { bg: "#1a1a2e", border: "#00f5ff", glow: "0 0 12px #00f5ff40" },
  retriever: { bg: "#1a1a2e", border: "#7b61ff", glow: "0 0 12px #7b61ff40" },
  generator: { bg: "#1a1a2e", border: "#ff6b35", glow: "0 0 12px #ff6b3540" },
  critic: { bg: "#1a1a2e", border: "#ff1744", glow: "0 0 12px #ff174440" },
  validator: { bg: "#1a1a2e", border: "#00e676", glow: "0 0 12px #00e67640" },
  optimizer: { bg: "#1a1a2e", border: "#ffd600", glow: "0 0 12px #ffd60040" },
  pattern_matcher: { bg: "#1a1a2e", border: "#e040fb", glow: "0 0 12px #e040fb40" },
  temporal_analyst: { bg: "#1a1a2e", border: "#18ffff", glow: "0 0 12px #18ffff40" },
  integrator: { bg: "#1a1a2e", border: "#69f0ae", glow: "0 0 12px #69f0ae40" },
};

const DEFAULT_COLOR = { bg: "#1a1a2e", border: "#555", glow: "0 0 8px #55540" };

function getColor(mindModel: string) {
  return MIND_MODEL_COLORS[mindModel] || DEFAULT_COLOR;
}

export default function TopologyViewer({
  agents,
  topology,
  weakPoint,
  isEvolving = false,
  onNodeClick,
}: TopologyViewerProps) {
  // 计算节点布局 —— 使用简单的分层布局
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, { level: number; order: number }>();

    // 计算层级（BFS）
    const levels = new Map<string, number>();
    const inDegree = new Map<string, number>();
    const adj = new Map<string, string[]>();

    // 初始化
    agents.forEach((a) => {
      levels.set(a.id, 0);
      inDegree.set(a.id, 0);
      adj.set(a.id, []);
    });

    // 建图（排除input_gate/output_gate）
    topology.forEach((e) => {
      if (e.from !== "input_gate" && e.to !== "output_gate") {
        adj.get(e.from)?.push(e.to);
        inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
      }
      if (e.from === "input_gate") {
        levels.set(e.to, 0);
      }
    });

    // BFS分层
    const queue = agents.filter((a) => (inDegree.get(a.id) || 0) === 0).map((a) => a.id);
    queue.forEach((id) => levels.set(id, 0));

    while (queue.length > 0) {
      const curr = queue.shift()!;
      const currLevel = levels.get(curr) || 0;
      adj.get(curr)?.forEach((next) => {
        const newLevel = Math.max(levels.get(next) || 0, currLevel + 1);
        levels.set(next, newLevel);
        queue.push(next);
      });
    }

    // 按层级分组，计算order
    const levelGroups = new Map<number, string[]>();
    agents.forEach((a) => {
      const lv = levels.get(a.id) || 0;
      if (!levelGroups.has(lv)) levelGroups.set(lv, []);
      levelGroups.get(lv)!.push(a.id);
    });

    levelGroups.forEach((ids) => ids.sort());

    const levelWidth = 300;
    const nodeHeight = 100;
    const levelHeight = 220;

    const flowNodes: Node[] = [];

    // Input Gate
    flowNodes.push({
      id: "input_gate",
      position: { x: -120, y: (levelGroups.get(0)?.length || 1) * 60 },
      data: { label: "INPUT" },
      style: {
        width: 80,
        height: 40,
        background: "#0a0a0f",
        border: "1px solid #00f5ff",
        color: "#00f5ff",
        fontSize: 11,
        fontWeight: 700,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 4,
        boxShadow: "0 0 8px #00f5ff40",
      },
    });

    // Agent Nodes
    agents.forEach((agent) => {
      const lv = levels.get(agent.id) || 0;
      const order = levelGroups.get(lv)?.indexOf(agent.id) || 0;
      const count = levelGroups.get(lv)?.length || 1;
      const x = 120 + lv * levelWidth;
      const totalWidth = (count - 1) * nodeHeight;
      const y = 50 + order * levelHeight - totalWidth / 2;
      const color = getColor(agent.mind_model);
      const isWeak = agent.id === weakPoint;

      flowNodes.push({
        id: agent.id,
        position: { x, y },
        data: { agent },
        style: {
          width: 180,
          height: 80,
          background: isWeak ? "#2a0a0a" : color.bg,
          border: `2px solid ${isWeak ? "#ff1744" : color.border}`,
          borderRadius: 8,
          color: "#e0e0e0",
          fontSize: 12,
          boxShadow: isWeak
            ? "0 0 20px #ff174480"
            : isEvolving
            ? color.glow + " animation: pulse 2s infinite"
            : color.glow,
          transition: "all 0.5s ease",
          cursor: onNodeClick ? "pointer" : "default",
        },
      });
    });

    // Output Gate
    const maxLevel = Math.max(...Array.from(levels.values()), 0);
    flowNodes.push({
      id: "output_gate",
      position: {
        x: 120 + (maxLevel + 1) * levelWidth,
        y: (levelGroups.get(maxLevel)?.length || 1) * 60,
      },
      data: { label: "OUTPUT" },
      style: {
        width: 80,
        height: 40,
        background: "#0a0a0f",
        border: "1px solid #00e676",
        color: "#00e676",
        fontSize: 11,
        fontWeight: 700,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 4,
        boxShadow: "0 0 8px #00e67640",
      },
    });

    // Edges
    const flowEdges: Edge[] = topology.map((e, idx) => {
      const isWeak = e.from === weakPoint || e.to === weakPoint;
      return {
        id: `e-${idx}`,
        source: e.from,
        target: e.to,
        animated: isEvolving || isWeak,
        style: {
          stroke: isWeak ? "#ff1744" : "#444",
          strokeWidth: isWeak ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isWeak ? "#ff1744" : "#555",
        },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [agents, topology, weakPoint, isEvolving]);

  // 自定义节点渲染
  const nodeTypes = useMemo(
    () => ({
      default: ({ data }: any) => {
        if (data.agent) {
          const a = data.agent;
          const color = getColor(a.mind_model);
          return (
            <div
              style={{
                padding: "8px 12px",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                gap: 3,
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: color.border,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                }}
              >
                {a.mind_model}
              </div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#fff",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {a.id}
              </div>
              <div
                style={{
                  fontSize: 9,
                  color: "#888",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {a.prompt_gene.substring(0, 30)}...
              </div>
              <div style={{ display: "flex", gap: 4, marginTop: 2 }}>
                {a.tools.map((t: string) => (
                  <span
                    key={t}
                    style={{
                      fontSize: 8,
                      padding: "1px 5px",
                      background: "#ffffff10",
                      borderRadius: 3,
                      color: "#aaa",
                    }}
                  >
                    {t}
                  </span>
                ))}
                <span
                  style={{
                    fontSize: 8,
                    padding: "1px 5px",
                    background: "#ffffff10",
                    borderRadius: 3,
                    color: "#888",
                    marginLeft: "auto",
                  }}
                >
                  T={a.temperature_gene}
                </span>
              </div>
            </div>
          );
        }
        return (
          <div style={{ padding: "4px 8px" }}>
            {data.label}
          </div>
        );
      },
    }),
    []
  );

  return (
    <div style={{ width: "100%", height: "100%", background: "#0a0a0f" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        style={{ background: "#0a0a0f" }}
        onNodeClick={(_, node) => {
          if (onNodeClick && node.data?.agent) {
            onNodeClick(node.data.agent as Agent);
          }
        }}
      >
        <Background color="#222" gap={20} size={1} />
        <Controls
          style={{
            background: "#1a1a2e",
            border: "1px solid #333",
          }}
        />
        <MiniMap
          style={{
            background: "#0a0a0f",
            border: "1px solid #333",
          }}
          nodeColor={(node) => {
            if (node.id === "input_gate") return "#00f5ff";
            if (node.id === "output_gate") return "#00e676";
            if (node.id === weakPoint) return "#ff1744";
            const agent = agents.find((a) => a.id === node.id);
            return agent ? getColor(agent.mind_model).border : "#555";
          }}
          maskColor="#0a0a0f80"
        />
      </ReactFlow>
    </div>
  );
}
