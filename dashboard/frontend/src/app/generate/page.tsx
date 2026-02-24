"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, Play, Loader2 } from "lucide-react";
import {
  getPersonaConfigs,
  triggerPipelineRun,
  getPipelineRunStatus,
  type PersonaConfig,
  type PipelineRunStatus,
} from "@/lib/api";

interface TrackedRun extends PipelineRunStatus {
  videoType?: string;
}

export default function GenerateVideosPage() {
  const [configs, setConfigs] = useState<PersonaConfig[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [checkedApps, setCheckedApps] = useState<Set<string>>(new Set());
  const [videoType, setVideoType] = useState<string>("auto");
  const [dryRun, setDryRun] = useState(false);
  const [noUpload, setNoUpload] = useState(false);
  const [skipGen, setSkipGen] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [runs, setRuns] = useState<TrackedRun[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getPersonaConfigs().then((c) => {
      setConfigs(c);
      if (c.length > 0) {
        setSelected(c[0].persona);
        setCheckedApps(new Set(c[0].apps.map((a) => a.slug)));
      }
    });
  }, []);

  const currentConfig = configs.find((c) => c.persona === selected);

  const selectPersona = (persona: string) => {
    const cfg = configs.find((c) => c.persona === persona);
    if (!cfg) return;
    setSelected(persona);
    setCheckedApps(new Set(cfg.apps.map((a) => a.slug)));
    setVideoType(cfg.video_types.length === 1 ? cfg.video_types[0] : "auto");
  };

  const toggleApp = (slug: string) => {
    setCheckedApps((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  // Poll active runs
  const pollRuns = useCallback(() => {
    setRuns((prev) => {
      const active = prev.filter((r) => r.status === "running");
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
    if (!currentConfig || checkedApps.size === 0) return;
    setLaunching(true);

    const appsToRun = currentConfig.apps.filter((a) => checkedApps.has(a.slug));
    const vt = videoType === "auto" ? undefined : videoType;

    const promises = appsToRun.map((app) =>
      triggerPipelineRun({
        persona: selected,
        video_type: vt,
        app: currentConfig.apps.length > 1 ? app.slug : undefined,
        dry_run: dryRun,
        no_upload: noUpload,
        skip_gen: skipGen,
      }).then(
        (status): TrackedRun => ({
          ...status,
          videoType: vt || "auto",
          app: app.slug,
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
    if (newRuns.some((r) => r.status === "running")) startPolling();
  };

  const isOlivia = selected === "olivia";

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Generate Videos</h2>

      {/* Persona selector */}
      <div className="flex gap-2">
        {configs.map((cfg) => (
          <button
            key={cfg.persona}
            onClick={() => selectPersona(cfg.persona)}
            className="px-4 py-2 rounded-md text-sm font-medium border transition-colors"
            style={
              selected === cfg.persona
                ? { backgroundColor: cfg.color, color: "#fff", borderColor: cfg.color }
                : { borderColor: cfg.color, color: cfg.color }
            }
          >
            {cfg.persona}
          </button>
        ))}
      </div>

      {currentConfig && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Apps card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Apps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {currentConfig.apps.map((app) => (
                <label
                  key={app.slug}
                  className="flex items-center gap-3 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={checkedApps.has(app.slug)}
                    onChange={() => toggleApp(app.slug)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <span className="text-sm">{app.name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {app.slug}
                  </Badge>
                </label>
              ))}
            </CardContent>
          </Card>

          {/* Video type + options card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Video type */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1">
                  Video Type
                </label>
                {isOlivia ? (
                  <Badge variant="secondary">olivia_default</Badge>
                ) : (
                  <select
                    value={videoType}
                    onChange={(e) => setVideoType(e.target.value)}
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  >
                    <option value="auto">auto (daily rotation)</option>
                    {currentConfig.video_types.map((vt) => (
                      <option key={vt} value={vt}>
                        {vt}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Option toggles */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-2">
                  Options
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: "Dry Run", value: dryRun, set: setDryRun },
                    { label: "No Upload", value: noUpload, set: setNoUpload },
                    { label: "Skip Gen", value: skipGen, set: setSkipGen },
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
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={!currentConfig || checkedApps.size === 0 || launching}
        className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
      >
        {launching ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {launching
          ? "Launching..."
          : `Generate ${checkedApps.size} run${checkedApps.size !== 1 ? "s" : ""}`}
      </button>

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
              const cfg = configs.find((c) => c.persona === run.persona);
              const color = cfg?.color || "#888";
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
                        {run.status === "running" && (
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
