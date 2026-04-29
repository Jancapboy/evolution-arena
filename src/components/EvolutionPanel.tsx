// 进化控制面板 —— 观测台的操控界面
// 包含：创世表单、时间轴、播放控制、状态显示

import { useState, useEffect, useCallback } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Zap,
  Dna,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Activity,
  ChevronRight,
  Download,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { SpeciesData } from "@/hooks/useApi";
import { exportSpecies } from "@/hooks/useApi";

interface EvolutionPanelProps {
  species: SpeciesData | null;
  onCreate: (goal: string) => Promise<void>;
  onEvolve: (speciesId: string) => Promise<void>;
  isLoading: boolean;
  liveLog?: { time: number; message: string }[];
  backendStatus?: "connected" | "disconnected" | "checking";
  allSpecies?: Array<{ species_id: string; user_goal: string; status: string }>;
  onSwitchSpecies?: (speciesId: string) => void;
}

export default function EvolutionPanel({
  species,
  onCreate,
  onEvolve,
  isLoading,
  liveLog = [],
  backendStatus = "checking",
  allSpecies = [],
  onSwitchSpecies,
}: EvolutionPanelProps) {
  const [goal, setGoal] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedGen, setSelectedGen] = useState<number | null>(null);

  // 自动刷新状态
  useEffect(() => {
    if (!species || species.status !== "evolving") {
      setIsPlaying(false);
    }
  }, [species]);

  const handleCreate = async () => {
    if (!goal.trim()) return;
    await onCreate(goal);
    setSelectedGen(1);
  };

  const handleEvolve = async () => {
    if (!species) return;
    setIsPlaying(true);
    await onEvolve(species.species_id);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "converged":
        return "#00e676";
      case "evolving":
        return "#ffd600";
      case "failed":
        return "#ff1744";
      default:
        return "#00f5ff";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "converged":
        return <CheckCircle size={14} />;
      case "evolving":
        return <Activity size={14} className="animate-pulse" />;
      case "failed":
        return <AlertTriangle size={14} />;
      default:
        return <Zap size={14} />;
    }
  };

  const getFitnessColor = (fitness: number) => {
    if (fitness >= 80) return "#00e676";
    if (fitness >= 50) return "#ffd600";
    return "#ff6b35";
  };

  return (
    <div
      style={{
        width: 380,
        minWidth: 380,
        height: "100vh",
        background: "#0d0d14",
        borderRight: "1px solid #1a1a2e",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* 头部 */}
      <div
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid #1a1a2e",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 4,
          }}
        >
          <Dna size={20} color="#00f5ff" />
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "#fff",
              letterSpacing: 1,
            }}
          >
            EVOLUTION ARENA
          </span>
          <StatusDot status={backendStatus} />
        </div>
        <div style={{ fontSize: 11, color: "#555", marginLeft: 30, display: "flex", alignItems: "center", gap: 8 }}>
          <span>闭环自进化Agent系统</span>
          <span style={{ color: "#2a2a3e" }}>|</span>
          <a
            href="/"
            style={{
              color: "#00f5ff",
              textDecoration: "none",
              fontSize: 10,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            ← 物种库
          </a>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        {/* 创世表单 */}
        <div style={{ marginBottom: 28 }}>
          <div
            style={{
              fontSize: 10,
              color: "#666",
              textTransform: "uppercase",
              letterSpacing: 2,
              marginBottom: 10,
              fontWeight: 600,
            }}
          >
            Genesis / 创世
          </div>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="输入你的目标，例如：分析Q4销售数据并预测下季度..."
            style={{
              width: "100%",
              minHeight: 80,
              background: "#14141f",
              border: "1px solid #2a2a3e",
              borderRadius: 8,
              padding: "12px 14px",
              color: "#e0e0e0",
              fontSize: 13,
              resize: "vertical",
              outline: "none",
              fontFamily: "inherit",
              lineHeight: 1.5,
            }}
          />
          <button
            onClick={handleCreate}
            disabled={isLoading || !goal.trim()}
            style={{
              width: "100%",
              marginTop: 10,
              padding: "10px",
              background: isLoading || !goal.trim() ? "#1a1a2e" : "#00f5ff15",
              border: `1px solid ${isLoading || !goal.trim() ? "#2a2a3e" : "#00f5ff50"}`,
              borderRadius: 8,
              color: isLoading || !goal.trim() ? "#555" : "#00f5ff",
              fontSize: 12,
              fontWeight: 700,
              cursor: isLoading || !goal.trim() ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              transition: "all 0.2s",
            }}
          >
            <Zap size={14} />
            生成初始Agent图
          </button>
        </div>

        {/* 物种信息 */}
        {species && (
          <div style={{ marginBottom: 28 }}>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 12,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>Species / 物种</span>
              {allSpecies.length > 1 && onSwitchSpecies && (
                <select
                  value={species.species_id}
                  onChange={(e) => onSwitchSpecies(e.target.value)}
                  style={{
                    background: "#14141f",
                    border: "1px solid #2a2a3e",
                    borderRadius: 6,
                    padding: "4px 8px",
                    fontSize: 10,
                    color: "#888",
                    outline: "none",
                    cursor: "pointer",
                    maxWidth: 140,
                  }}
                >
                  {allSpecies.map((s) => (
                    <option key={s.species_id} value={s.species_id}>
                      {s.user_goal.substring(0, 20)}
                      {s.user_goal.length > 20 ? "..." : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div
              style={{
                background: "#14141f",
                border: "1px solid #1a1a2e",
                borderRadius: 10,
                padding: "16px",
              }}
            >
              {/* ID和状态 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 14,
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    color: "#888",
                    fontFamily: "monospace",
                  }}
                >
                  {species.species_id}
                </span>
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    fontSize: 11,
                    color: getStatusColor(species.status),
                    fontWeight: 600,
                  }}
                >
                  {getStatusIcon(species.status)}
                  {species.status.toUpperCase()}
                </span>
              </div>

              {/* Fitness */}
              <div style={{ marginBottom: 14 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontSize: 11, color: "#666" }}>
                    适应度 FITNESS
                  </span>
                  <span
                    style={{
                      fontSize: 18,
                      fontWeight: 700,
                      color: getFitnessColor(species.fitness),
                    }}
                  >
                    {species.fitness.toFixed(1)}
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: 4,
                    background: "#1a1a2e",
                    borderRadius: 2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(species.fitness, 100)}%`,
                      height: "100%",
                      background: getFitnessColor(species.fitness),
                      borderRadius: 2,
                      transition: "width 0.5s ease",
                    }}
                  />
                </div>
              </div>

              {/* 统计 */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 10,
                }}
              >
                <StatBox
                  icon={<Dna size={12} />}
                  label="AGENTS"
                  value={species.agents.length}
                />
                <StatBox
                  icon={<TrendingUp size={12} />}
                  label="GENERATION"
                  value={species.generation}
                />
              </div>
            </div>
          </div>
        )}

        {/* 进化控制 */}
        {species && (
          <div style={{ marginBottom: 28 }}>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 12,
                fontWeight: 600,
              }}
            >
              Control / 控制
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleEvolve}
                disabled={isLoading || species.status === "evolving"}
                style={{
                  flex: 1,
                  padding: "10px",
                  background:
                    isLoading || species.status === "evolving"
                      ? "#1a1a2e"
                      : "#00e67615",
                  border: `1px solid ${
                    isLoading || species.status === "evolving"
                      ? "#2a2a3e"
                      : "#00e67650"
                  }`,
                  borderRadius: 8,
                  color:
                    isLoading || species.status === "evolving"
                      ? "#555"
                      : "#00e676",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor:
                    isLoading || species.status === "evolving"
                      ? "not-allowed"
                      : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                {species.status === "evolving" ? (
                  <>
                    <Pause size={14} />
                    进化中...
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    启动进化
                  </>
                )}
              </button>
              <button
                onClick={async () => {
                  try {
                    const data = await exportSpecies(species.species_id);
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `${species.species_id}_export.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch (err: any) {
                    alert("导出失败: " + err.message);
                  }
                }}
                title="导出基因JSON"
                style={{
                  padding: "10px 14px",
                  background: "#14141f",
                  border: "1px solid #2a2a3e",
                  borderRadius: 8,
                  color: "#888",
                  fontSize: 12,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#00f5ff50";
                  e.currentTarget.style.color = "#00f5ff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#2a2a3e";
                  e.currentTarget.style.color = "#888";
                }}
              >
                <Download size={14} />
              </button>
            </div>
          </div>
        )}

        {/* 实时日志流 */}
        {liveLog.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 12,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Activity size={12} className="animate-pulse" />
              Live Log / 实时日志
            </div>
            <div
              style={{
                background: "#14141f",
                border: "1px solid #1a1a2e",
                borderRadius: 10,
                padding: "10px 12px",
                maxHeight: 160,
                overflow: "auto",
                fontFamily: "monospace",
                fontSize: 10,
                lineHeight: 1.6,
              }}
            >
              {liveLog.map((entry, idx) => {
                const isLast = idx === liveLog.length - 1;
                return (
                  <div
                    key={idx}
                    ref={isLast ? (el) => {
                      if (el) el.scrollIntoView({ behavior: "smooth", block: "end" });
                    } : undefined}
                    style={{
                      color: isLast ? "#00f5ff" : "#777",
                      padding: "2px 0",
                      borderBottom: isLast ? "none" : "1px solid #1a1a2e",
                    }}
                  >
                    <span style={{ color: "#444", marginRight: 6 }}>
                      {new Date(entry.time).toLocaleTimeString("zh-CN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                    {entry.message}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Fitness 进化曲线 */}
        {species && species.history.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 12,
                fontWeight: 600,
              }}
            >
              Fitness Curve / 适应度曲线
            </div>
            <div
              style={{
                background: "#14141f",
                border: "1px solid #1a1a2e",
                borderRadius: 10,
                padding: "12px 8px 8px",
                height: 200,
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={species.history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                  <XAxis
                    dataKey="gen"
                    stroke="#444"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: "#2a2a3e" }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    stroke="#444"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: "#2a2a3e" }}
                    tickFormatter={(v) => `${v}`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0d0d14",
                      border: "1px solid #2a2a3e",
                      borderRadius: 6,
                      fontSize: 11,
                      color: "#e0e0e0",
                    }}
                    itemStyle={{ color: "#00f5ff" }}
                    formatter={(value: number) => [value.toFixed(1), "Fitness"]}
                    labelFormatter={(label) => `GEN ${label}`}
                  />
                  <ReferenceLine
                    y={90}
                    stroke="#00e676"
                    strokeDasharray="3 3"
                    strokeOpacity={0.3}
                  />
                  <Line
                    type="monotone"
                    dataKey="fitness"
                    stroke="#00f5ff"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#00f5ff", strokeWidth: 0 }}
                    activeDot={{
                      r: 5,
                      fill: "#fff",
                      stroke: "#00f5ff",
                      strokeWidth: 2,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 时间轴 */}
        {species && species.history.length > 0 && (
          <div>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 12,
                fontWeight: 600,
              }}
            >
              Timeline / 进化历史
            </div>
            <div
              style={{
                background: "#14141f",
                border: "1px solid #1a1a2e",
                borderRadius: 10,
                padding: "12px",
                maxHeight: 300,
                overflow: "auto",
              }}
            >
              {species.history.map((h, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedGen(h.gen)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 10px",
                    borderRadius: 6,
                    cursor: "pointer",
                    background:
                      selectedGen === h.gen ? "#1a1a2e" : "transparent",
                    borderLeft:
                      selectedGen === h.gen
                        ? "2px solid #00f5ff"
                        : "2px solid transparent",
                    transition: "all 0.2s",
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      color: "#555",
                      fontFamily: "monospace",
                      minWidth: 40,
                    }}
                  >
                    GEN {h.gen}
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: getFitnessColor(h.fitness),
                      minWidth: 45,
                    }}
                  >
                    {h.fitness.toFixed(0)}%
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: "#777",
                      flex: 1,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h.bottleneck}
                  </span>
                  {selectedGen === h.gen && (
                    <ChevronRight size={12} color="#00f5ff" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 诊断 */}
        {species?.latest_diagnosis && (
          <div style={{ marginTop: 20 }}>
            <div
              style={{
                fontSize: 10,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 10,
                fontWeight: 600,
              }}
            >
              Diagnosis / 诊断
            </div>
            <div
              style={{
                background: "#14141f",
                border: "1px solid #2a1a1a",
                borderRadius: 8,
                padding: "12px",
                fontSize: 11,
                color: "#999",
                lineHeight: 1.6,
                maxHeight: 150,
                overflow: "auto",
              }}
            >
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {(() => {
                  try {
                    const d = JSON.parse(species.latest_diagnosis);
                    return JSON.stringify(d, null, 2);
                  } catch {
                    return species.latest_diagnosis;
                  }
                })()}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* 底部 */}
      <div
        style={{
          padding: "12px 24px",
          borderTop: "1px solid #1a1a2e",
          fontSize: 10,
          color: "#444",
          textAlign: "center",
        }}
      >
        闭环自进化系统 v1.0
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: "connected" | "disconnected" | "checking" }) {
  const color =
    status === "connected"
      ? "#00e676"
      : status === "disconnected"
      ? "#ff1744"
      : "#ffd600";
  const label =
    status === "connected"
      ? "后端在线"
      : status === "disconnected"
      ? "后端离线"
      : "检测中";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        marginLeft: "auto",
        padding: "2px 8px",
        background: `${color}15`,
        border: `1px solid ${color}40`,
        borderRadius: 12,
      }}
      title={label}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: color,
          boxShadow: `0 0 6px ${color}`,
          animation: status === "checking" ? "pulse 1.5s infinite" : undefined,
        }}
      />
      <span style={{ fontSize: 9, color, fontWeight: 600, letterSpacing: 0.5 }}>
        {label}
      </span>
    </div>
  );
}

function StatBox({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div
      style={{
        background: "#0d0d14",
        borderRadius: 6,
        padding: "10px",
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span style={{ color: "#666" }}>{icon}</span>
      <div>
        <div style={{ fontSize: 9, color: "#555", letterSpacing: 1 }}>{label}</div>
        <div
          style={{ fontSize: 16, fontWeight: 700, color: "#fff", lineHeight: 1.2 }}
        >
          {value}
        </div>
      </div>
    </div>
  );
}
