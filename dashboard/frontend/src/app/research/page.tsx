"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  scanYTChannel,
  streamYTAnalysis,
  listYTResearch,
  getYTResearch,
  YTVideoInfo,
  YTVideoSummary,
  YTResearchListItem,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Search,
  Loader2,
  Play,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronRight,
  Clock,
  Eye,
} from "lucide-react";

type Phase = "input" | "selecting" | "analyzing" | "results";

function formatDuration(seconds: number | null) {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "";
  if (dateStr.length === 8) {
    // yt-dlp format: YYYYMMDD
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
  }
  return new Date(dateStr).toLocaleDateString();
}

function formatViews(n: number | null) {
  if (!n) return "";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K views`;
  return `${n} views`;
}

export default function ResearchPage() {
  const [phase, setPhase] = useState<Phase>("input");
  const [channelUrl, setChannelUrl] = useState("");
  const [maxVideos, setMaxVideos] = useState(10);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");

  // Channel scan results
  const [channelName, setChannelName] = useState("");
  const [videos, setVideos] = useState<YTVideoInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [progress, setProgress] = useState(0);
  const [totalProgress, setTotalProgress] = useState(0);
  const [summaries, setSummaries] = useState<YTVideoSummary[]>([]);
  const [crossAnalysis, setCrossAnalysis] = useState("");
  const [resultId, setResultId] = useState("");

  // Past results
  const [pastResults, setPastResults] = useState<YTResearchListItem[]>([]);
  const [showPast, setShowPast] = useState(false);

  // Results tab
  const [activeTab, setActiveTab] = useState<"summaries" | "analysis">("summaries");

  useEffect(() => {
    listYTResearch().then(setPastResults).catch(() => {});
  }, []);

  const handleScan = async () => {
    if (!channelUrl.trim()) return;
    setScanning(true);
    setScanError("");
    try {
      const result = await scanYTChannel(channelUrl.trim(), maxVideos);
      setChannelName(result.channel_name);
      setVideos(result.videos);
      setSelected(new Set(result.videos.map((v) => v.video_id)));
      setPhase("selecting");
    } catch (e) {
      setScanError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  };

  const toggleVideo = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(videos.map((v) => v.video_id)));
  const deselectAll = () => setSelected(new Set());

  const handleAnalyze = async () => {
    if (selected.size === 0) return;
    setPhase("analyzing");
    setAnalyzing(true);
    setSummaries([]);
    setCrossAnalysis("");
    setStatusMsg("Starting analysis...");
    setProgress(0);
    setTotalProgress(selected.size);

    const videoTitles: Record<string, string> = {};
    videos.forEach((v) => {
      videoTitles[v.video_id] = v.title;
    });

    await streamYTAnalysis(
      channelName,
      channelUrl,
      Array.from(selected),
      videoTitles,
      (event) => {
        switch (event.type) {
          case "status":
            setStatusMsg(event.content as string);
            if (event.progress !== undefined) setProgress(event.progress as number);
            if (event.total !== undefined) setTotalProgress(event.total as number);
            break;
          case "video_summary":
            setSummaries((prev) => [...prev, event.data as YTVideoSummary]);
            break;
          case "transcript_error":
            setSummaries((prev) => [
              ...prev,
              {
                video_id: event.video_id as string,
                title: event.title as string,
                has_transcript: false,
                summary: null,
                key_points: [],
                error: "No transcript available",
              },
            ]);
            break;
          case "cross_analysis_chunk":
            setCrossAnalysis((prev) => prev + (event.content as string));
            break;
          case "complete":
            setResultId(event.id as string);
            break;
        }
      },
      () => {
        setAnalyzing(false);
        setPhase("results");
        listYTResearch().then(setPastResults).catch(() => {});
      },
      (err) => {
        setStatusMsg(`Error: ${err}`);
        setAnalyzing(false);
        if (summaries.length > 0 || crossAnalysis) {
          setPhase("results");
        }
      }
    );
  };

  const loadPastResult = async (id: string) => {
    try {
      const result = await getYTResearch(id);
      setChannelName(result.channel_name);
      setChannelUrl(result.channel_url);
      setSummaries(result.video_summaries);
      setCrossAnalysis(result.cross_analysis);
      setResultId(result.id);
      setPhase("results");
    } catch {
      // ignore
    }
  };

  const reset = () => {
    setPhase("input");
    setChannelUrl("");
    setChannelName("");
    setVideos([]);
    setSelected(new Set());
    setSummaries([]);
    setCrossAnalysis("");
    setResultId("");
    setScanError("");
    setStatusMsg("");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Trend Research</h2>
          <p className="text-sm text-muted-foreground">
            Analyze YouTube channels to find trending themes and content patterns
          </p>
        </div>
        {phase !== "input" && (
          <Button variant="outline" size="sm" onClick={reset}>
            New Research
          </Button>
        )}
      </div>

      {/* Past Results */}
      {pastResults.length > 0 && phase === "input" && (
        <Card>
          <CardHeader
            className="pb-2 cursor-pointer"
            onClick={() => setShowPast(!showPast)}
          >
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {showPast ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              Past Research ({pastResults.length})
            </CardTitle>
          </CardHeader>
          {showPast && (
            <CardContent className="space-y-2">
              {pastResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => loadPastResult(r.id)}
                  className="w-full text-left px-3 py-2 rounded-md hover:bg-accent text-sm flex items-center justify-between"
                >
                  <span className="font-medium">{r.channel_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {r.video_count} videos &middot; {formatDate(r.created_at)}
                  </span>
                </button>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* Phase: Input */}
      {phase === "input" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Scan YouTube Channel</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="https://www.youtube.com/@channelname"
                value={channelUrl}
                onChange={(e) => setChannelUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleScan()}
                className="flex-1"
              />
              <select
                value={maxVideos}
                onChange={(e) => setMaxVideos(Number(e.target.value))}
                className="rounded-md border bg-background px-3 py-2 text-sm"
              >
                {[5, 10, 15, 20, 30, 50].map((n) => (
                  <option key={n} value={n}>
                    {n} videos
                  </option>
                ))}
              </select>
              <Button onClick={handleScan} disabled={scanning || !channelUrl.trim()}>
                {scanning ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                Scan
              </Button>
            </div>
            {scanError && (
              <p className="text-sm text-destructive">{scanError}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Phase: Selecting */}
      {phase === "selecting" && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">
                {channelName} &mdash; {videos.length} videos found
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={selectAll}>
                  Select All
                </Button>
                <Button variant="ghost" size="sm" onClick={deselectAll}>
                  Deselect All
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[calc(100vh-16rem)]">
              <div className="space-y-2">
                {videos.map((v) => (
                  <div
                    key={v.video_id}
                    className="flex items-center gap-3 p-2 rounded-md hover:bg-accent cursor-pointer"
                    onClick={() => toggleVideo(v.video_id)}
                  >
                    <button className="shrink-0">
                      {selected.has(v.video_id) ? (
                        <CheckSquare className="h-5 w-5 text-primary" />
                      ) : (
                        <Square className="h-5 w-5 text-muted-foreground" />
                      )}
                    </button>
                    {v.thumbnail && (
                      <img
                        src={v.thumbnail}
                        alt=""
                        className="w-24 h-14 object-cover rounded shrink-0"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{v.title}</p>
                      <div className="flex gap-3 text-xs text-muted-foreground">
                        {v.duration && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDuration(v.duration)}
                          </span>
                        )}
                        {v.view_count && (
                          <span className="flex items-center gap-1">
                            <Eye className="h-3 w-3" />
                            {formatViews(v.view_count)}
                          </span>
                        )}
                        {v.upload_date && <span>{formatDate(v.upload_date)}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
            <div className="mt-4 flex items-center justify-between border-t pt-4">
              <span className="text-sm text-muted-foreground">
                {selected.size} of {videos.length} selected
              </span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={reset}>
                  Back
                </Button>
                <Button onClick={handleAnalyze} disabled={selected.size === 0}>
                  <Play className="h-4 w-4 mr-2" />
                  Analyze {selected.size} Video{selected.size !== 1 ? "s" : ""}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Phase: Analyzing */}
      {phase === "analyzing" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{statusMsg}</span>
                  <span className="font-medium">
                    {progress}/{totalProgress}
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300 rounded-full"
                    style={{
                      width: totalProgress > 0 ? `${(progress / totalProgress) * 100}%` : "0%",
                    }}
                  />
                </div>
                {analyzing && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Processing...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Summaries appearing live */}
          {summaries.length > 0 && (
            <div className="space-y-3">
              {summaries.map((s) => (
                <SummaryCard key={s.video_id} summary={s} />
              ))}
            </div>
          )}

          {/* Cross-analysis streaming */}
          {crossAnalysis && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Cross-Video Analysis</CardTitle>
              </CardHeader>
              <CardContent className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {crossAnalysis}
                </ReactMarkdown>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Phase: Results */}
      {phase === "results" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h3 className="font-medium">{channelName}</h3>
            {resultId && (
              <Badge variant="secondary" className="text-xs">
                Saved: {resultId}
              </Badge>
            )}
          </div>

          {/* Tab switcher */}
          <div className="flex gap-1 border-b">
            <button
              onClick={() => setActiveTab("summaries")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "summaries"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Video Summaries ({summaries.length})
            </button>
            <button
              onClick={() => setActiveTab("analysis")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "analysis"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Cross-Analysis
            </button>
          </div>

          {activeTab === "summaries" && (
            <div className="space-y-3">
              {summaries.map((s) => (
                <SummaryCard key={s.video_id} summary={s} />
              ))}
            </div>
          )}

          {activeTab === "analysis" && crossAnalysis && (
            <Card>
              <CardContent className="pt-6 prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {crossAnalysis}
                </ReactMarkdown>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ summary }: { summary: YTVideoSummary }) {
  return (
    <Card className={!summary.has_transcript ? "opacity-60" : ""}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-medium">{summary.title}</h4>
          {!summary.has_transcript && (
            <Badge variant="outline" className="shrink-0 text-xs">
              No transcript
            </Badge>
          )}
        </div>
        {summary.summary && (
          <p className="text-sm text-muted-foreground mt-2">{summary.summary}</p>
        )}
        {summary.key_points.length > 0 && (
          <ul className="mt-2 space-y-1">
            {summary.key_points.map((point, i) => (
              <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                <span className="text-primary mt-0.5">&#8226;</span>
                {point}
              </li>
            ))}
          </ul>
        )}
        {summary.error && !summary.summary && (
          <p className="text-xs text-destructive mt-2">{summary.error}</p>
        )}
      </CardContent>
    </Card>
  );
}
