"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  streamScout,
  listScoutResults,
  getScoutResult,
  ScoutApp,
  ScoutResultListItem,
  ScoutResult,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Search,
  Loader2,
  Play,
  ChevronDown,
  ChevronRight,
  Check,
  Star,
  MessageSquare,
} from "lucide-react";

type Phase = "input" | "running" | "results";

type Step = "expanding" | "searching" | "reviews" | "reddit" | "analyzing";

const STEPS: { key: Step; label: string }[] = [
  { key: "expanding", label: "Expanding Seeds" },
  { key: "searching", label: "Searching Apps" },
  { key: "reviews", label: "Fetching Reviews" },
  { key: "reddit", label: "Reddit Pain Points" },
  { key: "analyzing", label: "Analyzing" },
];

export default function ScoutPage() {
  const [phase, setPhase] = useState<Phase>("input");

  // Input state
  const [seedText, setSeedText] = useState("");
  const [skipReviews, setSkipReviews] = useState(false);
  const [skipReddit, setSkipReddit] = useState(false);

  // Running state
  const [currentStep, setCurrentStep] = useState<Step>("expanding");
  const [statusMsg, setStatusMsg] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [apps, setApps] = useState<ScoutApp[]>([]);
  const [reviewCounts, setReviewCounts] = useState<Record<number, number>>({});
  const [redditCounts, setRedditCounts] = useState<Record<number, number>>({});
  const [analysis, setAnalysis] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  // Results state
  const [resultId, setResultId] = useState("");
  const [fullResult, setFullResult] = useState<ScoutResult | null>(null);
  const [activeTab, setActiveTab] = useState<"apps" | "analysis">("analysis");
  const [expandedApp, setExpandedApp] = useState<number | null>(null);

  // Past results
  const [pastResults, setPastResults] = useState<ScoutResultListItem[]>([]);
  const [showPast, setShowPast] = useState(false);

  useEffect(() => {
    listScoutResults().then(setPastResults).catch(() => {});
  }, []);

  const parseSeeds = (): string[] =>
    seedText
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean);

  const handleRun = async () => {
    const seeds = parseSeeds();
    if (seeds.length === 0) return;

    setPhase("running");
    setRunning(true);
    setError("");
    setCurrentStep("expanding");
    setStatusMsg("Starting...");
    setKeywords([]);
    setApps([]);
    setReviewCounts({});
    setRedditCounts({});
    setAnalysis("");
    setResultId("");
    setFullResult(null);

    await streamScout(
      seeds,
      skipReviews,
      skipReddit,
      (event) => {
        switch (event.type) {
          case "status":
            if (event.step) setCurrentStep(event.step as Step);
            if (event.message) setStatusMsg(event.message as string);
            break;
          case "seeds_expanded":
            setKeywords(event.keywords as string[]);
            break;
          case "apps_found":
            setApps(event.apps as ScoutApp[]);
            break;
          case "app_reviews":
            setReviewCounts((prev) => ({
              ...prev,
              [event.app_id as number]: event.count as number,
            }));
            break;
          case "app_reddit":
            setRedditCounts((prev) => ({
              ...prev,
              [event.app_id as number]: event.count as number,
            }));
            break;
          case "analysis_chunk":
            setAnalysis((prev) => prev + (event.content as string));
            break;
          case "complete":
            setResultId(event.id as string);
            break;
        }
      },
      () => {
        setRunning(false);
        setPhase("results");
        listScoutResults().then(setPastResults).catch(() => {});
      },
      (err) => {
        setError(err);
        setRunning(false);
        if (analysis || apps.length > 0) {
          setPhase("results");
        }
      }
    );
  };

  const loadPastResult = async (id: string) => {
    try {
      const result = await getScoutResult(id);
      setFullResult(result);
      setApps(result.apps || []);
      setKeywords(result.keywords || []);
      setAnalysis(result.analysis || "");
      setResultId(result.id);
      setSeedText((result.seeds || []).join(", "));
      setPhase("results");
    } catch {
      // ignore
    }
  };

  const reset = () => {
    setPhase("input");
    setSeedText("");
    setKeywords([]);
    setApps([]);
    setReviewCounts({});
    setRedditCounts({});
    setAnalysis("");
    setResultId("");
    setFullResult(null);
    setError("");
    setStatusMsg("");
    setExpandedApp(null);
  };

  const stepIndex = STEPS.findIndex((s) => s.key === currentStep);
  const totalReviews = Object.values(reviewCounts).reduce((a, b) => a + b, 0);
  const totalThreads = Object.values(redditCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Opportunity Scout</h2>
          <p className="text-sm text-muted-foreground">
            Find content opportunities from App Store reviews and Reddit pain points
          </p>
        </div>
        {phase !== "input" && (
          <Button variant="outline" size="sm" onClick={reset}>
            New Scout
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
              {showPast ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Past Scouts ({pastResults.length})
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
                  <span className="font-medium">
                    {r.seeds.join(", ")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {r.app_count} apps &middot;{" "}
                    {new Date(r.created_at).toLocaleDateString()}
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
            <CardTitle className="text-sm font-medium">
              Seed Keywords
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              placeholder="Enter seed keywords (comma or newline separated)&#10;e.g. journaling app, habit tracker, mood diary"
              value={seedText}
              onChange={(e) => setSeedText(e.target.value)}
              className="w-full min-h-[100px] rounded-md border bg-background px-3 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={skipReviews}
                  onChange={(e) => setSkipReviews(e.target.checked)}
                  className="rounded"
                />
                Skip App Store reviews
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={skipReddit}
                  onChange={(e) => setSkipReddit(e.target.checked)}
                  className="rounded"
                />
                Skip Reddit pain points
              </label>
            </div>
            <Button
              onClick={handleRun}
              disabled={parseSeeds().length === 0}
              className="w-full"
            >
              <Search className="h-4 w-4 mr-2" />
              Scout ({parseSeeds().length} seed
              {parseSeeds().length !== 1 ? "s" : ""})
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Phase: Running */}
      {phase === "running" && (
        <div className="space-y-4">
          {/* Step progress */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-4">
                {STEPS.map((step, i) => {
                  const isActive = step.key === currentStep;
                  const isDone = i < stepIndex;
                  const isSkipped =
                    (step.key === "reviews" && skipReviews) ||
                    (step.key === "reddit" && skipReddit);

                  return (
                    <div key={step.key} className="flex items-center gap-2 flex-1">
                      <div
                        className={`flex items-center justify-center h-7 w-7 rounded-full text-xs font-medium shrink-0 ${
                          isDone
                            ? "bg-primary text-primary-foreground"
                            : isActive
                            ? "bg-primary/20 text-primary border-2 border-primary"
                            : isSkipped
                            ? "bg-muted text-muted-foreground line-through"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {isDone ? <Check className="h-3.5 w-3.5" /> : i + 1}
                      </div>
                      <span
                        className={`text-xs hidden sm:inline ${
                          isActive
                            ? "text-foreground font-medium"
                            : "text-muted-foreground"
                        }`}
                      >
                        {step.label}
                      </span>
                      {i < STEPS.length - 1 && (
                        <div
                          className={`flex-1 h-px ${
                            isDone ? "bg-primary" : "bg-muted"
                          }`}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                <span>{statusMsg}</span>
              </div>
            </CardContent>
          </Card>

          {/* Live stats */}
          {(keywords.length > 0 || apps.length > 0) && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Keywords" value={keywords.length} />
              <StatCard label="Apps Found" value={apps.length} />
              <StatCard label="Reviews" value={totalReviews} />
              <StatCard label="Reddit Threads" value={totalThreads} />
            </div>
          )}

          {/* Apps appearing live */}
          {apps.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Apps Discovered ({apps.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                  {apps.map((app) => (
                    <AppMiniCard
                      key={app.track_id}
                      app={app}
                      reviewCount={reviewCounts[app.track_id]}
                      redditCount={redditCounts[app.track_id]}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Analysis streaming */}
          {analysis && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Opportunity Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysis}
                </ReactMarkdown>
              </CardContent>
            </Card>
          )}

          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Phase: Results */}
      {phase === "results" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h3 className="font-medium">
              {parseSeeds().join(", ") || "Scout Results"}
            </h3>
            {resultId && (
              <Badge variant="secondary" className="text-xs">
                Saved: {resultId}
              </Badge>
            )}
          </div>

          {/* Stats bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Keywords" value={keywords.length} />
            <StatCard label="Apps" value={apps.length} />
            <StatCard
              label="Reviews"
              value={
                fullResult
                  ? Object.values(fullResult.reviews).reduce(
                      (a, b) => a + b.length,
                      0
                    )
                  : totalReviews
              }
            />
            <StatCard
              label="Reddit Threads"
              value={
                fullResult
                  ? Object.values(fullResult.reddit).reduce(
                      (a, b) => a + b.length,
                      0
                    )
                  : totalThreads
              }
            />
          </div>

          {/* Tab switcher */}
          <div className="flex gap-1 border-b">
            <button
              onClick={() => setActiveTab("analysis")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "analysis"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Analysis
            </button>
            <button
              onClick={() => setActiveTab("apps")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "apps"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Apps ({apps.length})
            </button>
          </div>

          {activeTab === "analysis" && analysis && (
            <Card>
              <CardContent className="pt-6 prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysis}
                </ReactMarkdown>
              </CardContent>
            </Card>
          )}

          {activeTab === "apps" && (
            <div className="space-y-2">
              {apps.map((app) => {
                const isExpanded = expandedApp === app.track_id;
                const reviews = fullResult?.reviews?.[String(app.track_id)] || [];
                const threads = fullResult?.reddit?.[String(app.track_id)] || [];

                return (
                  <Card key={app.track_id}>
                    <CardContent className="pt-4">
                      <div
                        className="flex items-center gap-3 cursor-pointer"
                        onClick={() =>
                          setExpandedApp(isExpanded ? null : app.track_id)
                        }
                      >
                        {app.icon_url && (
                          <img
                            src={app.icon_url}
                            alt=""
                            className="w-10 h-10 rounded-lg shrink-0"
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium truncate">
                              {app.name}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              by {app.developer}
                            </span>
                          </div>
                          <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
                            {app.rating && (
                              <span className="flex items-center gap-1">
                                <Star className="h-3 w-3" />
                                {app.rating.toFixed(1)}
                              </span>
                            )}
                            {app.review_count && (
                              <span>
                                {app.review_count.toLocaleString()} ratings
                              </span>
                            )}
                            {app.genre && <span>{app.genre}</span>}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {(reviews.length > 0 ||
                            reviewCounts[app.track_id]) && (
                            <Badge variant="outline" className="text-xs">
                              {reviews.length || reviewCounts[app.track_id]}{" "}
                              reviews
                            </Badge>
                          )}
                          {(threads.length > 0 ||
                            redditCounts[app.track_id]) && (
                            <Badge variant="outline" className="text-xs">
                              {threads.length || redditCounts[app.track_id]}{" "}
                              threads
                            </Badge>
                          )}
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="mt-4 space-y-3 border-t pt-3">
                          {reviews.length > 0 && (
                            <div>
                              <h5 className="text-xs font-medium mb-2">
                                App Store Reviews
                              </h5>
                              <div className="space-y-2">
                                {reviews.slice(0, 10).map((r, i) => (
                                  <div
                                    key={i}
                                    className="text-xs p-2 bg-muted/50 rounded"
                                  >
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="flex items-center gap-0.5">
                                        <Star className="h-3 w-3 text-yellow-500" />
                                        {r.rating}/5
                                      </span>
                                      <span className="font-medium">
                                        {r.title}
                                      </span>
                                    </div>
                                    <p className="text-muted-foreground line-clamp-3">
                                      {r.content}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {threads.length > 0 && (
                            <div>
                              <h5 className="text-xs font-medium mb-2">
                                Reddit Pain Points
                              </h5>
                              <div className="space-y-2">
                                {threads.slice(0, 5).map((t) => (
                                  <div
                                    key={t.thread_id}
                                    className="text-xs p-2 bg-muted/50 rounded"
                                  >
                                    <div className="flex items-center gap-2 mb-1">
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] px-1.5 py-0"
                                      >
                                        r/{t.subreddit}
                                      </Badge>
                                      <span className="font-medium truncate">
                                        {t.title}
                                      </span>
                                      <span className="text-muted-foreground shrink-0">
                                        score: {t.score}
                                      </span>
                                    </div>
                                    {t.selftext_preview && (
                                      <p className="text-muted-foreground line-clamp-2">
                                        {t.selftext_preview}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {reviews.length === 0 && threads.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                              No detailed data available. Run a new scout to
                              collect reviews and Reddit threads.
                            </p>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-2xl font-semibold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

function AppMiniCard({
  app,
  reviewCount,
  redditCount,
}: {
  app: ScoutApp;
  reviewCount?: number;
  redditCount?: number;
}) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
      {app.icon_url && (
        <img src={app.icon_url} alt="" className="w-8 h-8 rounded-lg shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium truncate">{app.name}</p>
        <div className="flex gap-2 text-[10px] text-muted-foreground">
          {app.rating && (
            <span className="flex items-center gap-0.5">
              <Star className="h-2.5 w-2.5" />
              {app.rating.toFixed(1)}
            </span>
          )}
          {reviewCount !== undefined && <span>{reviewCount} rev</span>}
          {redditCount !== undefined && (
            <span className="flex items-center gap-0.5">
              <MessageSquare className="h-2.5 w-2.5" />
              {redditCount}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
