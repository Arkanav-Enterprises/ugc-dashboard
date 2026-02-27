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

export async function getPersonaConfigs() {
  return fetchAPI<PersonaConfig[]>("/api/pipeline/personas");
}

export interface LifestyleReelRequest {
  dry_run?: boolean;
  no_upload?: boolean;
  scene_1_text?: string;
  scene_2_text?: string;
  scene_3_text?: string;
  scene_1_image?: string;
  scene_2_image?: string;
}

export async function triggerLifestyleRun(req: LifestyleReelRequest) {
  return fetchAPI<PipelineRunStatus>("/api/pipeline/lifestyle-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export interface AutoJournalReelRequest {
  dry_run?: boolean;
  no_upload?: boolean;
  style?: string;
  category?: string;
  hook_text?: string;
  payoff_text?: string;
}

export async function triggerAutoJournalRun(req: AutoJournalReelRequest) {
  return fetchAPI<PipelineRunStatus>("/api/pipeline/autojournal-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
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
  onError: (err: string) => void,
  includeAnalytics: boolean = false
) {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history,
      skill_files: skillFiles,
      memory_files: memoryFiles,
      include_analytics: includeAnalytics,
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

// ─── Schedule ─────────────────────────────────────────

export async function getSchedule() {
  return fetchAPI<ScheduleState>("/api/schedule");
}

export async function updateSchedule(data: ScheduleUpdateRequest) {
  return fetchAPI<ScheduleState>("/api/schedule", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
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
  account: string;
  hook_clip: string;
  reaction_clip: string;
  screen_recording: string;
}

export interface PersonaAppInfo {
  name: string;
  slug: string;
}

export interface PersonaConfig {
  persona: string;
  color: string;
  apps: PersonaAppInfo[];
  video_types: string[];
}

export interface PipelineRunRequest {
  account: string;
  dry_run?: boolean;
  no_upload?: boolean;
  no_reaction?: boolean;
  idea_only?: boolean;
}

export interface PipelineRunStatus {
  id: string;
  status: string;
  persona: string;
  app?: string;
  started_at: string;
  output: string;
}

export interface ScheduleSlot {
  account: string;
  time_utc: string;
  time_ist: string;
  enabled: boolean;
  last_run: string | null;
  last_status: string | null;
}

export interface CronHistoryEntry {
  timestamp: string;
  status: "ok" | "failed" | "running";
  message: string;
}

export interface ScheduleState {
  frequency: string;
  days_of_week: number[];
  slots: ScheduleSlot[];
  cron_history: CronHistoryEntry[];
}

export interface ScheduleUpdateRequest {
  frequency?: string;
  days_of_week?: number[];
  accounts?: Record<string, { enabled?: boolean; time_utc?: string }>;
}

// ─── YouTube Research ────────────────────────────────

export interface YTVideoInfo {
  video_id: string;
  title: string;
  duration: number | null;
  thumbnail: string | null;
  view_count: number | null;
  upload_date: string | null;
}

export interface YTChannelScanResult {
  channel_name: string;
  channel_url: string;
  videos: YTVideoInfo[];
}

export interface YTVideoSummary {
  video_id: string;
  title: string;
  has_transcript: boolean;
  summary: string | null;
  key_points: string[];
  error: string | null;
}

export interface YTResearchResult {
  id: string;
  channel_name: string;
  channel_url: string;
  created_at: string;
  video_summaries: YTVideoSummary[];
  cross_analysis: string;
}

export interface YTResearchListItem {
  id: string;
  channel_name: string;
  created_at: string;
  video_count: number;
  source?: string;
}

export async function scanYTChannel(channelUrl: string, maxVideos: number = 20) {
  return fetchAPI<YTChannelScanResult>("/api/research/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel_url: channelUrl, max_videos: maxVideos }),
  });
}

export async function streamYTAnalysis(
  channelName: string,
  channelUrl: string,
  videoIds: string[],
  videoTitles: Record<string, string>,
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/research/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      channel_name: channelName,
      channel_url: channelUrl,
      video_ids: videoIds,
      video_titles: videoTitles,
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
          if (parsed.type === "error") onError(parsed.content);
          else onEvent(parsed);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  onDone();
}

export async function listYTResearch() {
  return fetchAPI<YTResearchListItem[]>("/api/research/results");
}

export async function getYTResearch(id: string) {
  return fetchAPI<YTResearchResult>(`/api/research/results/${id}`);
}

// ─── Opportunity Scout ──────────────────────────────

export interface ScoutApp {
  track_id: number;
  name: string;
  developer: string;
  rating: number | null;
  review_count: number | null;
  genre: string;
  icon_url: string;
}

export interface ScoutResultListItem {
  id: string;
  seeds: string[];
  app_count: number;
  created_at: string;
}

export interface ScoutResult {
  id: string;
  seeds: string[];
  keywords: string[];
  apps: ScoutApp[];
  reviews: Record<string, { author: string; rating: number; title: string; content: string }[]>;
  reddit: Record<string, { thread_id: string; title: string; subreddit: string; score: number; selftext_preview: string }[]>;
  analysis: string;
  created_at: string;
}

export async function expandSeeds(seeds: string[]): Promise<{ keywords: string[] }> {
  return fetchAPI<{ keywords: string[] }>("/api/scout/expand-seeds", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seeds }),
  });
}

export async function streamScout(
  seeds: string[],
  skipReviews: boolean,
  skipReddit: boolean,
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/scout/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      seeds,
      skip_reviews: skipReviews,
      skip_reddit: skipReddit,
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
          if (parsed.type === "error") onError(parsed.content);
          else onEvent(parsed);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  onDone();
}

export async function listScoutResults(): Promise<ScoutResultListItem[]> {
  return fetchAPI<ScoutResultListItem[]>("/api/scout/results");
}

export async function getScoutResult(id: string): Promise<ScoutResult> {
  return fetchAPI<ScoutResult>(`/api/scout/results/${id}`);
}

// ─── Reddit Research ─────────────────────────────────

export interface RedditThread {
  thread_id: string;
  title: string;
  subreddit: string;
  score: number;
  num_comments: number;
  permalink: string;
  created_utc: number;
  selftext_preview: string;
  url: string;
}

export interface RedditSearchResult {
  query: string;
  threads: RedditThread[];
}

export interface RedditThreadSummary {
  thread_id: string;
  title: string;
  subreddit: string;
  summary: string | null;
  key_points: string[];
  sentiment: string | null;
  error: string | null;
}

export async function searchReddit(
  query: string,
  subreddits: string[] = [],
  timeFilter: string = "week",
  limit: number = 25
) {
  return fetchAPI<RedditSearchResult>("/api/research/reddit/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      subreddits,
      time_filter: timeFilter,
      limit,
    }),
  });
}

// ─── Mass Outreach ──────────────────────────────────

export interface OutreachAccount {
  label: string;
  email: string;
}

export interface OutreachEmail {
  index: number;
  to: string;
  subject: string;
  body: string;
  skip: boolean;
  skip_reason: string | null;
}

export interface OutreachBatchListItem {
  id: string;
  account: string;
  created_at: string;
  sent: number;
  failed: number;
  total: number;
}

export interface OutreachBatchResult {
  id: string;
  account: string;
  created_at: string;
  results: (OutreachEmail & { status: string; error?: string })[];
  sent: number;
  failed: number;
}

export async function getOutreachAccounts() {
  return fetchAPI<OutreachAccount[]>("/api/outreach/accounts");
}

export async function parseOutreachMarkdown(markdown: string) {
  return fetchAPI<{ emails: OutreachEmail[] }>("/api/outreach/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown }),
  });
}

export async function streamOutreachSend(
  emails: OutreachEmail[],
  accountLabel: string,
  delaySeconds: number,
  fromName: string | null,
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/outreach/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      emails,
      account_label: accountLabel,
      delay_seconds: delaySeconds,
      from_name: fromName || null,
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
          if (parsed.type === "error") onError(parsed.content);
          else onEvent(parsed);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  onDone();
}

export async function getOutreachHistory() {
  return fetchAPI<OutreachBatchListItem[]>("/api/outreach/history");
}

export async function getOutreachBatch(id: string) {
  return fetchAPI<OutreachBatchResult>(`/api/outreach/history/${id}`);
}

// ─── Analytics (PostHog) ─────────────────────────────

export interface FunnelStep {
  name: string;
  count: number;
  conversion_rate: number;
  drop_off_rate: number;
}

export interface FunnelResult {
  steps: FunnelStep[];
  overall_conversion: number;
  error?: string;
}

export interface TrendSeries {
  event: string;
  labels: string[];
  data: number[];
  count: number;
}

export interface AnalyticsSummary {
  app: string;
  funnel: FunnelResult;
  trends: TrendSeries[];
}

export interface CombinedAnalytics {
  manifest_lock: AnalyticsSummary;
  journal_lock: AnalyticsSummary;
}

export async function getAnalyticsFunnel(app: string, dateFrom: string = "-30d", steps?: string[]) {
  const q = new URLSearchParams({ app, date_from: dateFrom });
  if (steps) q.set("steps", steps.join(","));
  return fetchAPI<FunnelResult>(`/api/analytics/funnel?${q}`);
}

export async function getAnalyticsTrends(app: string, dateFrom: string = "-30d", interval: string = "day", events?: string[]) {
  const q = new URLSearchParams({ app, date_from: dateFrom, interval });
  if (events) q.set("events", events.join(","));
  return fetchAPI<TrendSeries[]>(`/api/analytics/trends?${q}`);
}

export async function getAnalyticsSummary() {
  return fetchAPI<CombinedAnalytics>("/api/analytics/summary");
}

export async function streamAnalyticsAsk(
  message: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/analytics/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
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

// ─── Revenue (RevenueCat) ───────────────────────────

export interface RevenueMetrics {
  mrr: number;
  revenue: number;
  new_customers: number;
  active_users: number;
  active_subscriptions: number;
  active_trials: number;
}

export interface RevenueSnapshot {
  timestamp: string;
  projects: Record<string, RevenueMetrics>;
}

export interface RevenueCurrentResponse {
  current: RevenueSnapshot;
  previous: RevenueSnapshot | null;
}

export async function getRevenueCurrent() {
  return fetchAPI<RevenueCurrentResponse>("/api/revenue/current");
}

export async function getRevenueHistory() {
  return fetchAPI<RevenueSnapshot[]>("/api/revenue/history");
}

export async function streamRedditAnalysis(
  query: string,
  threads: RedditThread[],
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const res = await fetch(`${API_BASE}/api/research/reddit/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, threads }),
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
          if (parsed.type === "error") onError(parsed.content);
          else onEvent(parsed);
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  onDone();
}