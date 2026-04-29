// 进化竞技场主页面 —— 闭环自进化系统的观测台
// 左侧面板：控制和时间轴
// 右侧画布：React Flow拓扑可视化

import { useState, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import TopologyViewer from "@/components/TopologyViewer";
import EvolutionPanel from "@/components/EvolutionPanel";
import {
  createSpecies,
  evolveSpecies,
  getSpecies,
  type SpeciesData,
} from "@/hooks/useApi";
import { X, AlertTriangle, Cpu, Thermometer, Wrench, FileText } from "lucide-react";

export default function Arena() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [species, setSpecies] = useState<SpeciesData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveLog, setLiveLog] = useState<{ time: number; message: string }[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<{
    id: string;
    mind_model: string;
    prompt_gene: string;
    tools: string[];
    temperature_gene: number;
  } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  const speciesId = searchParams.get("id");

  // SSE + 轮询双重保险：SSE推送实时进度，轮询保证完整数据刷新
  useEffect(() => {
    if (!speciesId) {
      setSpecies(null);
      return;
    }

    const fetchSpecies = async () => {
      try {
        const data = await getSpecies(speciesId);
        setSpecies(data);
        setError(null);

        // 如果进化完成或失败，停止轮询
        if (data.status === "converged" || data.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      } catch (e: any) {
        setError(e.message);
      }
    };

    fetchSpecies();
    setLiveLog([]);
    setSelectedAgent(null);

    // 启动SSE实时推送
    const sse = new EventSource(`/api/species/${speciesId}/events`);
    sseRef.current = sse;

    sse.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        // 局部更新：只更新能确定的字段，保留完整数据结构
        setSpecies((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            generation: payload.generation ?? prev.generation,
            fitness: payload.fitness ?? prev.fitness,
            status: payload.status ?? prev.status,
          };
        });

        // 收集实时日志
        if (payload.message) {
          setLiveLog((prev) => {
            const next = [...prev, { time: Date.now(), message: payload.message }];
            return next.slice(-20); // 保留最近20条
          });
        }

        // 如果进化结束，停止SSE并刷新完整数据
        if (payload.status === "converged" || payload.status === "failed") {
          sse.close();
          sseRef.current = null;
          fetchSpecies();
        }
      } catch {
        // 忽略解析失败的消息
      }
    };

    sse.onerror = () => {
      // SSE连接失败时自动重连由浏览器处理，这里什么都不做
    };

    // 较低频率的轮询作为完整数据刷新备胎（5秒）
    pollRef.current = setInterval(fetchSpecies, 5000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [speciesId]);

  // 创世 —— 用户输入目标，系统生成第1代
  const handleCreate = useCallback(async (goal: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await createSpecies({ goal, max_generations: 10 });
      setSearchParams({ id: result.species_id });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, [setSearchParams]);

  // 启动进化
  const handleEvolve = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await evolveSpecies(id, 10, 90);
      // 轮询会自动更新状态
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 提取薄弱环节
  const weakPoint = (() => {
    if (!species?.latest_diagnosis) return undefined;
    try {
      const d = JSON.parse(species.latest_diagnosis);
      return d.weak_point;
    } catch {
      return undefined;
    }
  })();

  return (
    <div
      style={{
        display: "flex",
        width: "100vw",
        height: "100vh",
        background: "#0a0a0f",
        overflow: "hidden",
      }}
    >
      {/* 左侧面板 */}
      <EvolutionPanel
        species={species}
        onCreate={handleCreate}
        onEvolve={handleEvolve}
        isLoading={isLoading}
        liveLog={liveLog}
      />

      {/* 右侧拓扑画布 */}
      <div style={{ flex: 1, position: "relative" }}>
        {species ? (
          <TopologyViewer
            agents={species.agents}
            topology={species.topology}
            weakPoint={weakPoint}
            isEvolving={species.status === "evolving"}
            onNodeClick={(agent) => setSelectedAgent(agent)}
          />
        ) : (
          <EmptyState />
        )}

        {/* 错误提示 */}
        {error && (
          <div
            style={{
              position: "absolute",
              top: 20,
              left: "50%",
              transform: "translateX(-50%)",
              background: "#2a0a0a",
              border: "1px solid #ff174450",
              borderRadius: 8,
              padding: "12px 20px",
              color: "#ff6b6b",
              fontSize: 12,
              zIndex: 100,
              maxWidth: 500,
            }}
          >
            {error}
          </div>
        )}

        {/* 浮动信息 */}
        {species && (
          <div
            style={{
              position: "absolute",
              bottom: 20,
              left: 20,
              background: "#0d0d14cc",
              border: "1px solid #1a1a2e",
              borderRadius: 8,
              padding: "10px 14px",
              fontSize: 11,
              color: "#666",
              backdropFilter: "blur(10px)",
              zIndex: 50,
            }}
          >
            <div style={{ color: "#888", marginBottom: 4 }}>当前目标</div>
            <div style={{ color: "#ccc", maxWidth: 400, lineHeight: 1.4 }}>
              {species.user_goal}
            </div>
          </div>
        )}
        {/* Agent 详情面板 */}
        {selectedAgent && (
          <AgentDetailPanel
            agent={selectedAgent}
            isWeak={selectedAgent.id === weakPoint}
            onClose={() => setSelectedAgent(null)}
          />
        )}
      </div>
    </div>
  );
}

function AgentDetailPanel({
  agent,
  isWeak,
  onClose,
}: {
  agent: NonNullable<typeof selectedAgent>;
  isWeak: boolean;
  onClose: () => void;
}) {
  const getColor = (mindModel: string) => {
    const map: Record<string, string> = {
      decomposer: "#00f5ff",
      retriever: "#7b61ff",
      generator: "#ff6b35",
      critic: "#ff1744",
      validator: "#00e676",
      optimizer: "#ffd600",
      pattern_matcher: "#e040fb",
      temporal_analyst: "#18ffff",
      integrator: "#69f0ae",
    };
    return map[mindModel] || "#888";
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 20,
        right: 20,
        width: 320,
        maxHeight: "calc(100vh - 40px)",
        background: "#0d0d14ee",
        border: `1px solid ${isWeak ? "#ff174460" : "#1a1a2e"}`,
        borderRadius: 12,
        padding: "16px 18px",
        backdropFilter: "blur(16px)",
        zIndex: 60,
        overflow: "auto",
        boxShadow: isWeak ? "0 0 24px #ff174430" : "0 8px 32px #00000060",
      }}
    >
      {/* 头部 */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 14,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 10,
              color: getColor(agent.mind_model),
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: 1,
              marginBottom: 4,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Cpu size={12} />
            {agent.mind_model}
          </div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#fff",
              fontFamily: "monospace",
              wordBreak: "break-all",
            }}
          >
            {agent.id}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#555",
            cursor: "pointer",
            padding: 4,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* 弱环节警告 */}
      {isWeak && (
        <div
          style={{
            background: "#2a0a0a",
            border: "1px solid #ff174440",
            borderRadius: 8,
            padding: "8px 10px",
            marginBottom: 14,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 11,
            color: "#ff6b6b",
          }}
        >
          <AlertTriangle size={14} />
          当前识别为最弱环节，建议优化此 Agent 的 Prompt 或工具集
        </div>
      )}

      {/* Prompt Gene */}
      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            fontSize: 10,
            color: "#666",
            textTransform: "uppercase",
            letterSpacing: 1.5,
            marginBottom: 6,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <FileText size={11} />
          Prompt Gene / 提示基因
        </div>
        <div
          style={{
            background: "#14141f",
            border: "1px solid #1a1a2e",
            borderRadius: 8,
            padding: "10px 12px",
            fontSize: 11,
            color: "#bbb",
            lineHeight: 1.6,
            maxHeight: 200,
            overflow: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {agent.prompt_gene}
        </div>
      </div>

      {/* Tools */}
      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            fontSize: 10,
            color: "#666",
            textTransform: "uppercase",
            letterSpacing: 1.5,
            marginBottom: 6,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Wrench size={11} />
          Tools / 工具集
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {agent.tools.length > 0 ? (
            agent.tools.map((t) => (
              <span
                key={t}
                style={{
                  fontSize: 10,
                  padding: "3px 8px",
                  background: "#ffffff10",
                  borderRadius: 4,
                  color: "#aaa",
                  border: "1px solid #2a2a3e",
                }}
              >
                {t}
              </span>
            ))
          ) : (
            <span style={{ fontSize: 11, color: "#555" }}>无工具</span>
          )}
        </div>
      </div>

      {/* Temperature */}
      <div>
        <div
          style={{
            fontSize: 10,
            color: "#666",
            textTransform: "uppercase",
            letterSpacing: 1.5,
            marginBottom: 6,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Thermometer size={11} />
          Temperature / 温度基因
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              flex: 1,
              height: 6,
              background: "#1a1a2e",
              borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.min(agent.temperature_gene * 100, 100)}%`,
                height: "100%",
                background:
                  agent.temperature_gene > 0.7
                    ? "#ff6b35"
                    : agent.temperature_gene > 0.4
                    ? "#ffd600"
                    : "#00e676",
                borderRadius: 3,
                transition: "width 0.3s ease",
              }}
            />
          </div>
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "#fff",
              fontFamily: "monospace",
              minWidth: 40,
              textAlign: "right",
            }}
          >
            {agent.temperature_gene.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a0a0f",
        color: "#333",
      }}
    >
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: "50%",
          border: "1px solid #1a1a2e",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 24,
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#1a1a2e"
          strokeWidth="1"
        >
          <circle cx="12" cy="12" r="3" />
          <circle cx="5" cy="5" r="2" />
          <circle cx="19" cy="5" r="2" />
          <circle cx="5" cy="19" r="2" />
          <circle cx="19" cy="19" r="2" />
          <line x1="12" y1="9" x2="5" y2="7" />
          <line x1="12" y1="9" x2="19" y2="7" />
          <line x1="12" y1="15" x2="5" y2="17" />
          <line x1="12" y1="15" x2="19" y2="17" />
        </svg>
      </div>
      <div style={{ fontSize: 14, color: "#444", marginBottom: 8 }}>
        等待创世指令
      </div>
      <div style={{ fontSize: 12, color: "#333", textAlign: "center", maxWidth: 300 }}>
        在左侧面板输入目标，系统将自动生成初始Agent拓扑并开始进化
      </div>
    </div>
  );
}
