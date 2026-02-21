const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "" : "http://localhost:8000");

async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function getOverview() {
  return fetchAPI<{
    stats: OverviewStats;
    personas: PersonaStats[];
  }>("/api/pipeline/overview");
}

export async function getRuns() {
  return fetchAPI<PipelineRun[]>("/api/logs/runs");
}

export async function getSpend() {
  return fetchAPI<DailySpend[]>("/api/logs/spend");
}

export async function getReels(params?: { persona?: string; video_type?: string }) {
  const q = new URLSearchParams();
  if (params?.persona) q.set("persona", params.persona);
  if (params?.video_type) q.set("video_type", params.video_type);
  const qs = q.toString();
  return fetchAPI<PipelineRun[]>(`/api/content/reels${qs ? `?${qs}` : ""}`);
}

export function videoUrl(filename: string) {
  return `${API_BASE}/api/content/video/${filename}`;
}

export function videoByPathUrl(path: string) {
  return `${API_BASE}/api/content/video-by-path?path=${encodeURIComponent(path)}`;
}

export function assetUrl(path: string) {
  return `${API_BASE}/api/assets/file/${path}`;
}

export async function getKnowledgeTree() {
  return fetchAPI<{ skills: FileNode[]; memory: FileNode[] }>("/api/knowledge/tree");
}

export async function getKnowledgeFile(section: string, path: string) {
  return fetchAPI<{ path: string; content: string }>(
    `/api/knowledge/file?section=${section}&path=${encodeURIComponent(path)}`
  );
}

export async function saveKnowledgeFile(section: string, path: string, content: string) {
  return fetchAPI<{ ok: boolean }>(
    `/api/knowledge/file?section=${section}&path=${encodeURIComponent(path)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }
  );
}

export async function getReferenceImages() {
  return fetchAPI<AssetInfo[]>("/api/assets/reference-images");
}

export async function getClips() {
  return fetchAPI<AssetInfo[]>("/api/assets/clips");
}

export async function getAssetUsage() {
  return fetchAPI<AssetUsageRow[]>("/api/assets/usage");
}

export async function getContextFiles() {
  return fetchAPI<{ skills: string[]; memory: string[] }>("/api/chat/context-files");
}

export async function triggerPipelineRun(req: PipelineRunRequest) {
  return fetchAPI<PipelineRunStatus>("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getPipelineRunStatus(runId: string) {
  return fetchAPI<PipelineRunStatus>(`/api/pipeline/run/${runId}`);
}

export async function getActiveRuns() {
  return fetchAPI<PipelineRunStatus[]>("/api/pipeline/runs/active");
}

/**
 * Stream a chat message via SSE (Server-Sent Events).
 * Falls back to WebSocket for local development.
 */
export async function streamChat(
  message: string,
  history: { role: string; content: string }[],
  skillFiles: string[],
  memoryFiles: string[],
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history,
      skill_files: skillFiles,
      memory_files: memoryFiles,
    }),
  });

  if (!res.ok) {
    onError(`API error: ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(data);
          if (parsed.type === "chunk") onChunk(parsed.content);
          else if (parsed.type === "error") onError(parsed.content);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  onDone();
}

// Types
export interface OverviewStats {
  today_runs: number;
  today_cost: number;
  daily_cap: number;
  total_reels: number;
  total_spend: number;
}

export interface PersonaStats {
  persona: string;
  color: string;
  last_run: string | null;
  total_runs: number;
  hook_clips: number;
  reaction_clips: number;
}

export interface PipelineRun {
  timestamp: string;
  persona: string;
  video_type?: string;
  hook_text: string;
  reaction_text: string;
  caption: string;
  content_angle: string;
  reel_path: string | null;
  cost_usd: number | null;
}

export interface DailySpend {
  date: string;
  amount: number;
}

export interface FileNode {
  path: string;
  name: string;
  is_dir: boolean;
  children?: FileNode[];
}

export interface AssetInfo {
  name: string;
  path: string;
  persona: string | null;
  type?: string;
}

export interface AssetUsageRow {
  date: string;
  persona: string;
  reference_image: string;
  screen_recording: string;
  app: string;
  video_type: string;
}

export interface PipelineRunRequest {
  persona: string;
  video_type?: string;
  dry_run?: boolean;
  no_upload?: boolean;
  skip_gen?: boolean;
}

export interface PipelineRunStatus {
  id: string;
  status: string;
  persona: string;
  started_at: string;
  output: string;
}

// --- X Research types ---

export interface XPost {
  handle: string;
  text: string;
  likes: number;
  retweets: number;
  replies: number;
  url: string;
  created_at: string;
}

export interface XTrend {
  name: string;
  tweet_count: string;
}

export interface ResearchResult {
  posts: XPost[];
  trends: XTrend[];
  raw_output: string;
  error: string;
}

// --- X Research API functions ---

export async function getResearchStatus() {
  return fetchAPI<{ available: boolean; version: string }>("/api/research/status");
}

export async function searchPosts(query: string, count: number = 10) {
  return fetchAPI<ResearchResult>("/api/research/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, count }),
  });
}

export async function getUserTweets(handle: string, count: number = 10) {
  return fetchAPI<ResearchResult>("/api/research/user-tweets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ handle, count }),
  });
}

export async function getTrending() {
  return fetchAPI<ResearchResult>("/api/research/trending");
}

export interface SaveInsightRequest {
  section: "saved_posts" | "trending_formats" | "copy_patterns" | "engagement_targets";
  handle?: string;
  text?: string;
  likes?: number;
  retweets?: number;
  note?: string;
}

export async function saveInsight(req: SaveInsightRequest) {
  return fetchAPI<{ ok: boolean; error?: string }>("/api/research/save-insight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}
