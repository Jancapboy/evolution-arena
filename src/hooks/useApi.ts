// API服务层 —— 与Python后端通信
const API_BASE = "/api";

export interface CreateSpeciesParams {
  goal: string;
  max_generations?: number;
  fitness_threshold?: number;
}

export interface SpeciesData {
  species_id: string;
  generation: number;
  fitness: number;
  status: string;
  user_goal: string;
  agents: Array<{
    id: string;
    mind_model: string;
    prompt_gene: string;
    tools: string[];
    temperature_gene: number;
  }>;
  topology: Array<{
    from: string;
    to: string;
    trigger: string;
  }>;
  history: Array<{
    gen: number;
    fitness: number;
    bottleneck: string;
  }>;
  latest_result?: string;
  latest_diagnosis?: string;
}

export async function createSpecies(params: CreateSpeciesParams): Promise<{
  species_id: string;
  generation: number;
  status: string;
  agents: Array<{ id: string; mind_model: string }>;
  topology: Array<{ from: string; to: string }>;
}> {
  const res = await fetch(`${API_BASE}/species/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function evolveSpecies(
  species_id: string,
  max_generations: number = 10,
  fitness_threshold: number = 90
): Promise<{ status: string; message: string; converged: boolean }> {
  const res = await fetch(`${API_BASE}/species/evolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ species_id, max_generations, fitness_threshold }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSpecies(species_id: string): Promise<SpeciesData> {
  const res = await fetch(`${API_BASE}/species/${species_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listSpecies(): Promise<
  Array<{
    species_id: string;
    generation: number;
    fitness: number;
    status: string;
    user_goal: string;
    history: Array<{ gen: number; fitness: number; bottleneck: string }>;
  }>
> {
  const res = await fetch(`${API_BASE}/species`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGenerationHistory(
  species_id: string
): Promise<Array<{ gen: number; fitness: number; bottleneck: string }>> {
  const res = await fetch(`${API_BASE}/species/${species_id}/generations`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteSpecies(species_id: string): Promise<{ deleted: boolean; species_id: string }> {
  const res = await fetch(`${API_BASE}/species/${species_id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportSpecies(species_id: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/species/${species_id}/export`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function importSpecies(data: Record<string, any>): Promise<{ imported: boolean; species_id: string }> {
  const res = await fetch(`${API_BASE}/species/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function checkHealth(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}
