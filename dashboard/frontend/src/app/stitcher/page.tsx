"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  X,
  ArrowUp,
  ArrowDown,
  Play,
  Loader2,
  Download,
} from "lucide-react";
import {
  submitStitch,
  getStitchJobStatus,
  stitchDownloadUrl,
  type StitchJobStatus,
} from "@/lib/api";
import PromptGenerator from "@/components/prompt-generator";

interface Scene {
  id: number;
  file: File | null;
  text: string;
  speed: string;
}

let nextId = 1;
function makeScene(): Scene {
  return { id: nextId++, file: null, text: "", speed: "" };
}

export default function StitcherPage() {
  const [scenes, setScenes] = useState<Scene[]>([makeScene()]);
  const [launching, setLaunching] = useState(false);
  const [job, setJob] = useState<StitchJobStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logRef = useRef<HTMLPreElement>(null);

  const canStitch = scenes.some((s) => s.file) && !launching;

  const addScene = () => setScenes((prev) => [...prev, makeScene()]);

  const addSceneWithText = (text: string) => {
    const scene = makeScene();
    scene.text = text;
    setScenes((prev) => [...prev, scene]);
  };

  const removeScene = (id: number) =>
    setScenes((prev) => prev.filter((s) => s.id !== id));

  const moveScene = (idx: number, dir: -1 | 1) => {
    setScenes((prev) => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  };

  const updateScene = (id: number, patch: Partial<Scene>) =>
    setScenes((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)));

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [job?.output]);

  // Poll job status
  const pollJob = useCallback((jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await getStitchJobStatus(jobId);
        setJob(status);
        if (status.status === "completed" || status.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // ignore poll errors
      }
    }, 2000);
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleStitch = async () => {
    const validScenes = scenes.filter((s) => s.file);
    if (validScenes.length === 0) return;

    setLaunching(true);
    setJob(null);

    const formData = new FormData();
    const sceneMeta: { text: string; speed: number | null }[] = [];

    for (const scene of validScenes) {
      formData.append("files", scene.file!);
      sceneMeta.push({
        text: scene.text,
        speed: scene.speed ? parseFloat(scene.speed) : null,
      });
    }
    formData.append("scenes_json", JSON.stringify(sceneMeta));

    try {
      const result = await submitStitch(formData);
      setJob({ id: result.job_id, status: result.status, output: "", result_filename: null });
      pollJob(result.job_id);
    } catch (err) {
      setJob({
        id: "",
        status: "failed",
        output: `Error: ${err instanceof Error ? err.message : String(err)}`,
        result_filename: null,
      });
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Video Stitcher</h2>

      {/* Prompt Generator */}
      <PromptGenerator onUseAsScene={addSceneWithText} />

      {/* Scene cards */}
      <div className="space-y-3">
        {scenes.map((scene, idx) => (
          <Card key={scene.id}>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start gap-4">
                {/* Scene number + reorder */}
                <div className="flex flex-col items-center gap-1 pt-1">
                  <Badge variant="outline" className="text-xs tabular-nums">
                    {idx + 1}
                  </Badge>
                  <button
                    onClick={() => moveScene(idx, -1)}
                    disabled={idx === 0}
                    className="p-0.5 text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => moveScene(idx, 1)}
                    disabled={idx === scenes.length - 1}
                    className="p-0.5 text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Main content */}
                <div className="flex-1 space-y-3">
                  {/* File input */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Video clip
                    </label>
                    {scene.file ? (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="truncate max-w-xs">{scene.file.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({(scene.file.size / 1024 / 1024).toFixed(1)} MB)
                        </span>
                        <button
                          onClick={() => updateScene(scene.id, { file: null })}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex items-center justify-center w-full h-20 border-2 border-dashed rounded-md cursor-pointer hover:border-foreground/30 transition-colors">
                        <span className="text-sm text-muted-foreground">
                          Click to select video
                        </span>
                        <input
                          type="file"
                          accept="video/*"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0] ?? null;
                            if (file) updateScene(scene.id, { file });
                          }}
                        />
                      </label>
                    )}
                  </div>

                  {/* Text + speed */}
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <textarea
                        value={scene.text}
                        onChange={(e) =>
                          updateScene(scene.id, { text: e.target.value })
                        }
                        placeholder="Text overlay (optional)"
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none"
                        rows={2}
                      />
                    </div>
                    <div className="w-28">
                      <input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="10"
                        value={scene.speed}
                        onChange={(e) =>
                          updateScene(scene.id, { speed: e.target.value })
                        }
                        placeholder="Speed"
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50"
                      />
                      <span className="text-[10px] text-muted-foreground mt-0.5 block">
                        1.0 = normal
                      </span>
                    </div>
                  </div>
                </div>

                {/* Remove */}
                <button
                  onClick={() => removeScene(scene.id)}
                  disabled={scenes.length <= 1}
                  className="p-1 text-muted-foreground hover:text-destructive disabled:opacity-30 mt-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Add scene + stitch */}
      <div className="flex items-center gap-3">
        <button
          onClick={addScene}
          disabled={scenes.length >= 10}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md border text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          Add Scene
        </button>

        <button
          onClick={handleStitch}
          disabled={!canStitch}
          className="inline-flex items-center gap-2 px-6 py-2 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
        >
          {launching ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {launching ? "Uploading..." : "Stitch"}
        </button>
      </div>

      {/* Job status */}
      {job && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-3">
              Job {job.id}
              <Badge
                variant={
                  job.status === "completed"
                    ? "default"
                    : job.status === "failed"
                    ? "destructive"
                    : "secondary"
                }
              >
                {(job.status === "running" || job.status === "queued") && (
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                )}
                {job.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <pre
              ref={logRef}
              className="text-xs whitespace-pre-wrap max-h-64 overflow-auto font-mono text-muted-foreground bg-muted/30 rounded-md p-3"
            >
              {job.output || "Waiting for output..."}
            </pre>

            {job.status === "completed" && job.result_filename && (
              <div className="space-y-3">
                <video
                  src={stitchDownloadUrl(job.result_filename)}
                  controls
                  className="w-full max-w-md rounded-md"
                />
                <a
                  href={stitchDownloadUrl(job.result_filename)}
                  download
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md border text-sm hover:bg-accent transition-colors"
                >
                  <Download className="h-4 w-4" />
                  Download
                </a>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
