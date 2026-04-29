// 物种列表页 —— 进化竞技场的入口
// 展示所有历史物种，支持搜索、筛选、排序

import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  Dna,
  Search,
  TrendingUp,
  Zap,
  Activity,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Plus,
  Trash2,
  Download,
} from "lucide-react";
import { listSpecies, deleteSpecies, exportSpecies, importSpecies, type SpeciesData } from "@/hooks/useApi";

export default function SpeciesList() {
  const navigate = useNavigate();
  const [species, setSpecies] = useState<SpeciesData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"fitness" | "generation" | "recent">("recent");

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const data = await listSpecies();
      setSpecies(data as SpeciesData[]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    let result = [...species];

    // 搜索
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.species_id.toLowerCase().includes(q) ||
          s.user_goal.toLowerCase().includes(q)
      );
    }

    // 状态筛选
    if (statusFilter !== "all") {
      result = result.filter((s) => s.status === statusFilter);
    }

    // 排序
    result.sort((a, b) => {
      if (sortBy === "fitness") return b.fitness - a.fitness;
      if (sortBy === "generation") return b.generation - a.generation;
      return 0; // recent: 服务端已按updated_at排序
    });

    return result;
  }, [species, search, statusFilter, sortBy]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "converged":
        return { color: "#00e676", bg: "#00e67615", icon: <CheckCircle size={12} /> };
      case "evolving":
        return { color: "#ffd600", bg: "#ffd60015", icon: <Activity size={12} className="animate-pulse" /> };
      case "failed":
        return { color: "#ff1744", bg: "#ff174415", icon: <AlertTriangle size={12} /> };
      default:
        return { color: "#00f5ff", bg: "#00f5ff15", icon: <Zap size={12} /> };
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm(`确定删除物种 ${id}？此操作不可恢复。`)) return;
    try {
      await deleteSpecies(id);
      setSpecies((prev) => prev.filter((s) => s.species_id !== id));
    } catch (err: any) {
      alert("删除失败: " + err.message);
    }
  };

  const handleExport = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      const data = await exportSpecies(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}_export.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("导出失败: " + err.message);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      // 支持导出格式 { data: {...} } 或直接的物种对象
      const speciesData = json.data || json;
      await importSpecies(speciesData);
      alert(`导入成功: ${speciesData.species_id}`);
      load();
    } catch (err: any) {
      alert("导入失败: " + err.message);
    } finally {
      e.target.value = "";
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
        width: "100vw",
        height: "100vh",
        background: "#0a0a0f",
        overflow: "auto",
        color: "#e0e0e0",
      }}
    >
      {/* 顶部栏 */}
      <div
        style={{
          position: "sticky",
          top: 0,
          background: "#0a0a0fcc",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid #1a1a2e",
          zIndex: 100,
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "20px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Dna size={22} color="#00f5ff" />
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#fff", letterSpacing: 1 }}>
                EVOLUTION ARENA
              </div>
              <div style={{ fontSize: 10, color: "#555" }}>
                物种库 · {species.length} 个生命体
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="file"
              id="import-json"
              accept=".json"
              onChange={handleImport}
              style={{ display: "none" }}
            />
            <button
              onClick={() => document.getElementById("import-json")?.click()}
              style={{
                padding: "10px 18px",
                background: "#14141f",
                border: "1px solid #2a2a3e",
                borderRadius: 8,
                color: "#888",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
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
              导入JSON
            </button>
            <button
              onClick={() => navigate("/arena")}
              style={{
                padding: "10px 18px",
                background: "#00f5ff15",
                border: "1px solid #00f5ff50",
                borderRadius: 8,
                color: "#00f5ff",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s",
              }}
            >
              <Plus size={14} />
              创建新物种
            </button>
          </div>
        </div>

        {/* 统计概览 */}
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "0 24px 16px",
          }}
        >
          <StatsBar species={species} />
        </div>

        {/* 筛选栏 */}
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "0 24px 16px",
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {/* 搜索 */}
          <div
            style={{
              flex: 1,
              minWidth: 240,
              position: "relative",
            }}
          >
            <Search
              size={14}
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                color: "#555",
              }}
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索 species ID 或目标描述..."
              style={{
                width: "100%",
                padding: "10px 14px 10px 36px",
                background: "#14141f",
                border: "1px solid #2a2a3e",
                borderRadius: 8,
                color: "#e0e0e0",
                fontSize: 13,
                outline: "none",
                fontFamily: "inherit",
              }}
            />
          </div>

          {/* 状态筛选 */}
          <div style={{ display: "flex", gap: 6 }}>
            {[
              { key: "all", label: "全部" },
              { key: "evolving", label: "进化中" },
              { key: "converged", label: "已收敛" },
              { key: "failed", label: "失败" },
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setStatusFilter(f.key)}
                style={{
                  padding: "8px 14px",
                  borderRadius: 6,
                  border: "1px solid",
                  borderColor: statusFilter === f.key ? "#00f5ff50" : "#2a2a3e",
                  background: statusFilter === f.key ? "#00f5ff15" : "#14141f",
                  color: statusFilter === f.key ? "#00f5ff" : "#666",
                  fontSize: 12,
                  cursor: "pointer",
                  fontWeight: statusFilter === f.key ? 700 : 400,
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* 排序 */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            style={{
              padding: "9px 12px",
              background: "#14141f",
              border: "1px solid #2a2a3e",
              borderRadius: 6,
              color: "#888",
              fontSize: 12,
              cursor: "pointer",
              outline: "none",
            }}
          >
            <option value="recent">最近更新</option>
            <option value="fitness">适应度</option>
            <option value="generation">世代数</option>
          </select>
        </div>
      </div>

      {/* 内容区 */}
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: 80, color: "#555" }}>
            <Activity size={32} className="animate-pulse" style={{ marginBottom: 16 }} />
            <div style={{ fontSize: 13 }}>正在加载物种数据...</div>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: 40,
              textAlign: "center",
              background: "#2a0a0a",
              border: "1px solid #ff174450",
              borderRadius: 10,
              color: "#ff6b6b",
              fontSize: 13,
            }}
          >
            <AlertTriangle size={24} style={{ marginBottom: 8 }} />
            <div>加载失败: {error}</div>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: 80, color: "#444" }}>
            <Dna size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
            <div style={{ fontSize: 14, marginBottom: 8 }}>暂无物种</div>
            <div style={{ fontSize: 12, color: "#333" }}>
              点击右上角“创建新物种”开始你的第一个进化实验
            </div>
          </div>
        )}

        {!loading && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
              gap: 16,
            }}
          >
            {filtered.map((s) => {
              const st = getStatusColor(s.status);
              return (
                <div
                  key={s.species_id}
                  onClick={() => navigate(`/arena?id=${s.species_id}`)}
                  style={{
                    background: "#14141f",
                    border: "1px solid #1a1a2e",
                    borderRadius: 10,
                    padding: "18px 20px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "#2a2a3e";
                    e.currentTarget.style.transform = "translateY(-2px)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "#1a1a2e";
                    e.currentTarget.style.transform = "translateY(0)";
                  }}
                >
                  {/* 头部 */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 12,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        color: "#888",
                        fontFamily: "monospace",
                      }}
                    >
                      {s.species_id}
                    </span>
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 5,
                        fontSize: 11,
                        color: st.color,
                        fontWeight: 600,
                        padding: "3px 8px",
                        background: st.bg,
                        borderRadius: 4,
                      }}
                    >
                      {st.icon}
                      {s.status.toUpperCase()}
                    </span>
                  </div>

                  {/* 目标 */}
                  <div
                    style={{
                      fontSize: 13,
                      color: "#ccc",
                      lineHeight: 1.5,
                      marginBottom: 14,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                    }}
                  >
                    {s.user_goal}
                  </div>

                  {/* 迷你趋势 */}
                  {s.history.length > 1 && (
                    <MiniSparkline
                      history={s.history}
                      color={getFitnessColor(s.fitness)}
                    />
                  )}

                  {/* 底部数据 */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 16,
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: 4,
                          fontSize: 10,
                          color: "#555",
                        }}
                      >
                        <span>适应度</span>
                        <span style={{ color: getFitnessColor(s.fitness), fontWeight: 700 }}>
                          {s.fitness.toFixed(1)}
                        </span>
                      </div>
                      <div
                        style={{
                          width: "100%",
                          height: 3,
                          background: "#1a1a2e",
                          borderRadius: 2,
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(s.fitness, 100)}%`,
                            height: "100%",
                            background: getFitnessColor(s.fitness),
                            borderRadius: 2,
                            transition: "width 0.5s ease",
                          }}
                        />
                      </div>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        fontSize: 11,
                        color: "#666",
                      }}
                    >
                      <TrendingUp size={12} />
                      GEN {s.generation}
                    </div>

                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <button
                        onClick={(e) => handleExport(e, s.species_id)}
                        title="导出JSON"
                        style={{
                          padding: "4px 6px",
                          background: "transparent",
                          border: "1px solid #2a2a3e",
                          borderRadius: 4,
                          color: "#666",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          transition: "all 0.2s",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#00f5ff50";
                          e.currentTarget.style.color = "#00f5ff";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "#2a2a3e";
                          e.currentTarget.style.color = "#666";
                        }}
                      >
                        <Download size={12} />
                      </button>
                      <button
                        onClick={(e) => handleDelete(e, s.species_id)}
                        title="删除"
                        style={{
                          padding: "4px 6px",
                          background: "transparent",
                          border: "1px solid #2a2a3e",
                          borderRadius: 4,
                          color: "#666",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          transition: "all 0.2s",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#ff174450";
                          e.currentTarget.style.color = "#ff1744";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "#2a2a3e";
                          e.currentTarget.style.color = "#666";
                        }}
                      >
                        <Trash2 size={12} />
                      </button>
                      <ArrowRight size={14} color="#444" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniSparkline({
  history,
  color,
}: {
  history: Array<{ gen: number; fitness: number }>;
  color: string;
}) {
  const points = history;
  if (points.length < 2) return null;

  const width = 280;
  const height = 32;
  const padding = 2;

  const minF = Math.min(...points.map((p) => p.fitness), 0);
  const maxF = Math.max(...points.map((p) => p.fitness), 100);
  const range = maxF - minF || 1;

  const getX = (i: number) =>
    padding + (i / (points.length - 1)) * (width - padding * 2);
  const getY = (v: number) =>
    height - padding - ((v - minF) / range) * (height - padding * 2);

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(p.fitness)}`)
    .join(" ");

  const areaD =
    pathD +
    ` L ${getX(points.length - 1)} ${height} L ${getX(0)} ${height} Z`;

  return (
    <div style={{ marginBottom: 10, marginTop: -4 }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ overflow: "visible" }}
      >
        <defs>
          <linearGradient id={`grad-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill={`url(#grad-${color.replace("#", "")})`} stroke="none" />
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function StatsBar({ species }: { species: SpeciesData[] }) {
  const total = species.length;
  const avgFitness = total > 0
    ? species.reduce((s, x) => s + x.fitness, 0) / total
    : 0;
  const converged = species.filter((s) => s.status === "converged").length;
  const evolving = species.filter((s) => s.status === "evolving").length;
  const failed = species.filter((s) => s.status === "failed").length;

  const items = [
    { label: "总物种", value: total, color: "#fff" },
    { label: "平均适应度", value: avgFitness.toFixed(1), color: avgFitness >= 80 ? "#00e676" : avgFitness >= 50 ? "#ffd600" : "#ff6b35" },
    { label: "已收敛", value: converged, color: "#00e676" },
    { label: "进化中", value: evolving, color: "#ffd600" },
    { label: "失败", value: failed, color: "#ff1744" },
  ];

  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
      }}
    >
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            background: "#14141f",
            border: "1px solid #1a1a2e",
            borderRadius: 8,
            padding: "10px 16px",
            display: "flex",
            alignItems: "baseline",
            gap: 8,
            minWidth: 80,
          }}
        >
          <span style={{ fontSize: 16, fontWeight: 700, color: item.color }}>
            {item.value}
          </span>
          <span style={{ fontSize: 10, color: "#555", textTransform: "uppercase", letterSpacing: 1 }}>
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
