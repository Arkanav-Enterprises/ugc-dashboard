"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, Play, Loader2 } from "lucide-react";
import {
  triggerPipelineRun,
  triggerLifestyleRun,
  triggerAutoJournalRun,
  getPipelineRunStatus,
  type PipelineRunStatus,
} from "@/lib/api";

interface TrackedRun extends PipelineRunStatus {
  accountName?: string;
}

const ACCOUNTS = [
  "aliyah.manifests",
  "aliyah.journals",
  "riley.manifests",
  "riley.journals",
  "sanyahealing",
  "sophie.unplugs",
  "emillywilks",
];

const ACCOUNT_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
  emillywilks: "#f59e0b",
};

function accountColor(account: string): string {
  const persona = account.split(".")[0];
  return ACCOUNT_COLORS[persona] || ACCOUNT_COLORS[account] || "#6b7280";
}

type PipelineMode = "content" | "lifestyle" | "autojournal";

const AUTOJOURNAL_STYLES = ["dark", "cream", "terracotta", "journal", "dark_accent"] as const;
const AUTOJOURNAL_CATEGORIES = ["A", "B", "C", "D"] as const;

export default function GenerateContentPage() {
  const [mode, setMode] = useState<PipelineMode>("content");
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(
    new Set(["aliyah.manifests"])
  );
  const [dryRun, setDryRun] = useState(false);
  const [noUpload, setNoUpload] = useState(false);
  const [noReaction, setNoReaction] = useState(false);
  const [ideaOnly, setIdeaOnly] = useState(false);
  const [hookText, setHookText] = useState("");
  const [reactionText, setReactionText] = useState("");
  const [launching, setLaunching] = useState(false);
  const [runs, setRuns] = useState<TrackedRun[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Lifestyle reel state
  const [lifestyleDryRun, setLifestyleDryRun] = useState(false);
  const [lifestyleNoUpload, setLifestyleNoUpload] = useState(false);

  // AutoJournal reel state
  const [ajDryRun, setAjDryRun] = useState(false);
  const [ajNoUpload, setAjNoUpload] = useState(false);
  const [ajStyle, setAjStyle] = useState<string>("");
  const [ajCategory, setAjCategory] = useState<string>("");

  const toggleAccount = (account: string) => {
    setSelectedAccounts((prev) => {
      const next = new Set(prev);
      if (next.has(account)) next.delete(account);
      else next.add(account);
      return next;
    });
  };

  // Poll active runs
  const pollRuns = useCallback(() => {
    setRuns((prev) => {
      const active = prev.filter((r) => r.status === "running" || r.status === "queued");
      if (active.length === 0) {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        return prev;
      }
      active.forEach((r) => {
        getPipelineRunStatus(r.id).then((updated) => {
          setRuns((curr) =>
            curr.map((x) =>
              x.id === updated.id ? { ...x, ...updated } : x
            )
          );
        });
      });
      return prev;
    });
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(pollRuns, 3000);
  }, [pollRuns]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleGenerate = async () => {
    if (selectedAccounts.size === 0) return;
    setLaunching(true);

    const promises = Array.from(selectedAccounts).map((account) =>
      triggerPipelineRun({
        account,
        dry_run: dryRun,
        no_upload: noUpload,
        no_reaction: noReaction,
        idea_only: ideaOnly,
        hook_text: hookText.trim() || undefined,
        reaction_text: reactionText.trim() || undefined,
      }).then(
        (status): TrackedRun => ({
          ...status,
          accountName: account,
        })
      )
    );

    const results = await Promise.allSettled(promises);
    const newRuns: TrackedRun[] = [];
    for (const r of results) {
      if (r.status === "fulfilled") newRuns.push(r.value);
    }

    setRuns((prev) => [...newRuns, ...prev]);
    setLaunching(false);
    if (newRuns.some((r) => r.status === "running" || r.status === "queued")) startPolling();
  };

  const handleLifestyleGenerate = async () => {
    setLaunching(true);
    try {
      const status = await triggerLifestyleRun({
        dry_run: lifestyleDryRun,
        no_upload: lifestyleNoUpload,
      });
      const run: TrackedRun = { ...status, accountName: "lifestyle" };
      setRuns((prev) => [run, ...prev]);
      if (run.status === "running" || run.status === "queued") startPolling();
    } catch {
      // ignore
    }
    setLaunching(false);
  };

  const handleAutoJournalGenerate = async () => {
    setLaunching(true);
    try {
      const status = await triggerAutoJournalRun({
        dry_run: ajDryRun,
        no_upload: ajNoUpload,
        style: ajStyle || undefined,
        category: ajCategory || undefined,
      });
      const run: TrackedRun = { ...status, accountName: "autojournal" };
      setRuns((prev) => [run, ...prev]);
      if (run.status === "running" || run.status === "queued") startPolling();
    } catch {
      // ignore
    }
    setLaunching(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Generate Content</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setMode("content")}
            className={`px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
              mode === "content"
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            Content Pipeline
          </button>
          <button
            onClick={() => setMode("lifestyle")}
            className={`px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
              mode === "lifestyle"
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            Lifestyle Reel
          </button>
          <button
            onClick={() => setMode("autojournal")}
            className={`px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
              mode === "autojournal"
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            AutoJournal Reel
          </button>
        </div>
      </div>

      {mode === "autojournal" ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                AutoJournal Reel
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                2-scene reel: styled text hook → screen recording payoff.
                Uses Claude for text gen, ffmpeg for assembly. ~$0.01 per reel.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Style</label>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => setAjStyle("")}
                      className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                        !ajStyle
                          ? "bg-primary text-primary-foreground border-primary"
                          : "text-muted-foreground hover:bg-accent"
                      }`}
                    >
                      Auto
                    </button>
                    {AUTOJOURNAL_STYLES.map((s) => (
                      <button
                        key={s}
                        onClick={() => setAjStyle(ajStyle === s ? "" : s)}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          ajStyle === s
                            ? "bg-primary text-primary-foreground border-primary"
                            : "text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Category</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setAjCategory("")}
                      className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                        !ajCategory
                          ? "bg-primary text-primary-foreground border-primary"
                          : "text-muted-foreground hover:bg-accent"
                      }`}
                    >
                      Auto
                    </button>
                    {AUTOJOURNAL_CATEGORIES.map((c) => (
                      <button
                        key={c}
                        onClick={() => setAjCategory(ajCategory === c ? "" : c)}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          ajCategory === c
                            ? "bg-primary text-primary-foreground border-primary"
                            : "text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  {[
                    { label: "Dry Run", value: ajDryRun, set: setAjDryRun },
                    { label: "No Upload", value: ajNoUpload, set: setAjNoUpload },
                  ].map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => opt.set(!opt.value)}
                      className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                        opt.value
                          ? "bg-primary text-primary-foreground border-primary"
                          : "text-muted-foreground hover:bg-accent"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
          <button
            onClick={handleAutoJournalGenerate}
            disabled={launching}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {launching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {launching ? "Launching..." : "Generate AutoJournal Reel"}
          </button>
        </>
      ) : mode === "lifestyle" ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Lifestyle Reel — Journal Lock
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                3-scene reel: lifestyle image + hook → lifestyle image + response → screen recording + payoff.
                Uses Claude for text gen, ffmpeg for assembly. ~$0.01 per reel.
              </p>
              <div className="flex gap-2">
                {[
                  { label: "Dry Run", value: lifestyleDryRun, set: setLifestyleDryRun },
                  { label: "No Upload", value: lifestyleNoUpload, set: setLifestyleNoUpload },
                ].map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => opt.set(!opt.value)}
                    className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                      opt.value
                        ? "bg-primary text-primary-foreground border-primary"
                        : "text-muted-foreground hover:bg-accent"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
          <button
            onClick={handleLifestyleGenerate}
            disabled={launching}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {launching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {launching ? "Launching..." : "Generate Lifestyle Reel"}
          </button>
        </>
      ) : (
        <>
      {/* Account selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Select Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {ACCOUNTS.map((account) => {
              const color = accountColor(account);
              const isSelected = selectedAccounts.has(account);
              return (
                <button
                  key={account}
                  onClick={() => toggleAccount(account)}
                  className="px-3 py-1.5 rounded-md text-sm font-medium border transition-colors"
                  style={
                    isSelected
                      ? { backgroundColor: color, color: "#fff", borderColor: color }
                      : { borderColor: color, color }
                  }
                >
                  {account}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Options */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Options</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {[
              { label: "Dry Run", value: dryRun, set: setDryRun },
              { label: "No Upload", value: noUpload, set: setNoUpload },
              { label: "No Reaction", value: noReaction, set: setNoReaction },
              { label: "Idea Only", value: ideaOnly, set: setIdeaOnly },
            ].map((opt) => (
              <button
                key={opt.label}
                onClick={() => opt.set(!opt.value)}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  opt.value
                    ? "bg-primary text-primary-foreground border-primary"
                    : "text-muted-foreground hover:bg-accent"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            ~$0.01 per reel (Claude API only — no video generation costs)
          </p>
        </CardContent>
      </Card>

      {/* Text overrides */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Text Override
            <span className="ml-2 font-normal text-xs text-muted-foreground">Optional — skips Claude generation when filled</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Hook Text (Part 1 overlay)</label>
            <textarea
              value={hookText}
              onChange={(e) => setHookText(e.target.value)}
              placeholder='e.g. "POV: you deleted Instagram and this happened"'
              className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none"
              rows={2}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Reaction Text (Part 3 overlay)</label>
            <textarea
              value={reactionText}
              onChange={(e) => setReactionText(e.target.value)}
              placeholder='e.g. "I feel so much calmer now"'
              className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none"
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={selectedAccounts.size === 0 || launching}
        className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
      >
        {launching ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {launching
          ? "Launching..."
          : `Generate ${selectedAccounts.size} run${selectedAccounts.size !== 1 ? "s" : ""}`}
      </button>
        </>
      )}

      {/* Active runs */}
      {runs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Runs ({runs.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {runs.map((run) => {
              const color = accountColor(run.accountName || run.persona);
              const isExpanded = expanded === run.id;
              return (
                <div key={run.id} className="border rounded-md">
                  <div
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50"
                    onClick={() => setExpanded(isExpanded ? null : run.id)}
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                      <Badge
                        variant="outline"
                        style={{ borderColor: color, color }}
                      >
                        {run.persona}
                      </Badge>
                      {run.app && (
                        <Badge variant="secondary" className="text-xs">
                          {run.app}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          run.status === "completed"
                            ? "default"
                            : run.status === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {(run.status === "running" || run.status === "queued") && (
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        )}
                        {run.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {run.id}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-10 pb-3 border-t bg-muted/30">
                      <pre className="pt-3 text-xs whitespace-pre-wrap max-h-64 overflow-auto font-mono text-muted-foreground">
                        {run.output || "Waiting for output..."}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
