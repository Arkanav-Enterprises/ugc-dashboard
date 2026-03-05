"use client";

import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Copy,
  Check,
  Sparkles,
  Upload,
  X,
  PlusCircle,
} from "lucide-react";
import {
  generatePrompt,
  type PromptRequest,
  type PromptResponse,
} from "@/lib/api";

const PERSONAS: Record<string, { color: string; label: string }> = {
  aliyah: { color: "#8b5cf6", label: "Aliyah" },
  riley: { color: "#10b981", label: "Riley" },
  sanya: { color: "#ef4444", label: "Sanya" },
  emilly: { color: "#3b82f6", label: "Emilly" },
};

const MODES = [
  { value: "existing_character", label: "Existing Character" },
  { value: "new_character", label: "New Character" },
  { value: "mood_reference", label: "Mood Reference" },
] as const;

interface PromptGeneratorProps {
  onUseAsScene?: (text: string) => void;
}

export default function PromptGenerator({ onUseAsScene }: PromptGeneratorProps) {
  const [expanded, setExpanded] = useState(false);
  const [persona, setPersona] = useState("aliyah");
  const [promptType, setPromptType] = useState<"image" | "video">("image");
  const [mode, setMode] = useState<PromptRequest["mode"]>("existing_character");
  const [sceneDesc, setSceneDesc] = useState("");
  const [refImage, setRefImage] = useState<string | null>(null);
  const [refImageName, setRefImageName] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<PromptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const showRefUpload = mode === "existing_character" || mode === "mood_reference";

  const handleRefImage = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      // Strip the data:image/...;base64, prefix
      const base64 = dataUrl.split(",")[1];
      setRefImage(base64);
      setRefImageName(file.name);
    };
    reader.readAsDataURL(file);
  };

  const handleGenerate = async () => {
    if (!sceneDesc.trim()) return;
    setGenerating(true);
    setError(null);
    setResult(null);

    try {
      const resp = await generatePrompt({
        persona,
        scene_description: sceneDesc.trim(),
        prompt_type: promptType,
        mode,
        reference_image_base64: refImage || undefined,
      });
      setResult(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const fullPrompt = result?.prompt_json?.full_prompt_string as string | undefined;
  const videoPrompt = result?.prompt_json?.video_prompt as string | undefined;

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <Sparkles className="h-4 w-4" />
          Prompt Generator
          {!expanded && persona && (
            <Badge variant="outline" className="ml-2 text-xs" style={{ borderColor: PERSONAS[persona]?.color, color: PERSONAS[persona]?.color }}>
              {PERSONAS[persona]?.label}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-4 pt-0">
          {/* Persona selector */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
              Persona
            </label>
            <div className="flex gap-2">
              {Object.entries(PERSONAS).map(([key, { color, label }]) => (
                <button
                  key={key}
                  onClick={() => setPersona(key)}
                  className="px-3 py-1.5 rounded-md text-sm font-medium border transition-colors"
                  style={
                    persona === key
                      ? { backgroundColor: color, color: "#fff", borderColor: color }
                      : { borderColor: color, color }
                  }
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt type + Mode */}
          <div className="flex gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Type
              </label>
              <div className="flex gap-1 border rounded-md p-0.5">
                {(["image", "video"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setPromptType(t)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      promptType === t
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Mode
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as PromptRequest["mode"])}
                className="h-8 rounded-md border bg-background px-2 text-xs"
              >
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Reference image upload */}
          {showRefUpload && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Reference Image {mode === "existing_character" ? "(character)" : "(mood)"}
              </label>
              {refImage ? (
                <div className="flex items-center gap-2 text-sm">
                  <span className="truncate max-w-xs">{refImageName}</span>
                  <button
                    onClick={() => { setRefImage(null); setRefImageName(null); }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <label className="flex items-center justify-center w-full h-16 border-2 border-dashed rounded-md cursor-pointer hover:border-foreground/30 transition-colors">
                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Upload className="h-3.5 w-3.5" />
                    Click to upload reference
                  </span>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleRefImage(f);
                    }}
                  />
                </label>
              )}
            </div>
          )}

          {/* Scene description */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
              Scene Description
            </label>
            <textarea
              value={sceneDesc}
              onChange={(e) => setSceneDesc(e.target.value)}
              placeholder={
                promptType === "image"
                  ? "In bed at night, looking at phone with worried expression, blue phone glow on face"
                  : "Worried expression looking at phone, then slowly smiles and puts phone down"
              }
              className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none"
              rows={3}
            />
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={!sceneDesc.trim() || generating}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-md bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {generating ? "Generating..." : "Generate Prompt"}
          </button>

          {/* Error */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {/* Result */}
          {result && (
            <div className="space-y-3">
              <pre className="text-xs whitespace-pre-wrap max-h-80 overflow-auto font-mono text-muted-foreground bg-muted/30 rounded-md p-3">
                {JSON.stringify(result.prompt_json, null, 2)}
              </pre>

              <div className="flex flex-wrap gap-2">
                {fullPrompt && (
                  <button
                    onClick={() => copyToClipboard(fullPrompt, "prompt")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs hover:bg-accent transition-colors"
                  >
                    {copied === "prompt" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied === "prompt" ? "Copied!" : "Copy Full Prompt"}
                  </button>
                )}

                <button
                  onClick={() => copyToClipboard(JSON.stringify(result.prompt_json, null, 2), "json")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs hover:bg-accent transition-colors"
                >
                  {copied === "json" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied === "json" ? "Copied!" : "Copy JSON"}
                </button>

                {videoPrompt && (
                  <button
                    onClick={() => copyToClipboard(videoPrompt, "video")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs hover:bg-accent transition-colors"
                  >
                    {copied === "video" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied === "video" ? "Copied!" : "Copy Video Prompt"}
                  </button>
                )}

                {fullPrompt && onUseAsScene && (
                  <button
                    onClick={() => onUseAsScene(fullPrompt)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs hover:bg-accent transition-colors"
                  >
                    <PlusCircle className="h-3.5 w-3.5" />
                    Use as Scene
                  </button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
