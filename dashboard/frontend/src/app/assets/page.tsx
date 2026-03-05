"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { Trash2, Upload, Loader2, Play } from "lucide-react";
import {
  getReferenceImages,
  getClips,
  getAssetUsage,
  assetUrl,
  thumbnailUrl,
  uploadClip,
  uploadReaction,
  deleteClip,
  type AssetInfo,
  type AssetUsageRow,
} from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
};

const PERSONAS = ["aliyah", "riley", "sanya", "emilly"];

type UploadStep = "persona" | "hook" | "reaction" | "uploading";

export default function AssetManagerPage() {
  const [images, setImages] = useState<AssetInfo[]>([]);
  const [clips, setClips] = useState<AssetInfo[]>([]);
  const [usage, setUsage] = useState<AssetUsageRow[]>([]);

  // Upload state
  const [showUpload, setShowUpload] = useState(false);
  const [uploadStep, setUploadStep] = useState<UploadStep>("persona");
  const [selectedPersona, setSelectedPersona] = useState("");
  const [hookFile, setHookFile] = useState<File | null>(null);
  const [clipName, setClipName] = useState("");
  const [reactionMode, setReactionMode] = useState<"upload" | "auto" | null>(null);
  const [reactionFile, setReactionFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState("");

  // Filter + preview state
  const [personaFilter, setPersonaFilter] = useState("all");
  const [previewClip, setPreviewClip] = useState<AssetInfo | null>(null);

  // Delete state
  const [deleting, setDeleting] = useState<string | null>(null);

  const refreshClips = useCallback(() => {
    getClips().then(setClips);
  }, []);

  useEffect(() => {
    getReferenceImages().then(setImages);
    refreshClips();
    getAssetUsage().then(setUsage);
  }, [refreshClips]);

  const resetUpload = () => {
    setShowUpload(false);
    setUploadStep("persona");
    setSelectedPersona("");
    setHookFile(null);
    setClipName("");
    setReactionMode(null);
    setReactionFile(null);
    setUploadError("");
  };

  const handleUploadSubmit = async () => {
    if (!hookFile || !selectedPersona || !clipName) return;
    setUploadStep("uploading");
    setUploadError("");

    try {
      // Upload hook clip
      const hookForm = new FormData();
      hookForm.append("file", hookFile);
      hookForm.append("persona", selectedPersona);
      hookForm.append("clip_name", clipName);
      await uploadClip(hookForm);

      // Upload or auto-generate reaction
      const reactionForm = new FormData();
      reactionForm.append("persona", selectedPersona);
      reactionForm.append("clip_name", clipName);
      if (reactionMode === "upload" && reactionFile) {
        reactionForm.append("file", reactionFile);
      } else {
        reactionForm.append("auto_generate", "true");
      }
      await uploadReaction(reactionForm);

      resetUpload();
      refreshClips();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
      setUploadStep("reaction");
    }
  };

  const handleDelete = async (clip: AssetInfo) => {
    if (!clip.persona || !clip.type) return;
    const ok = window.confirm(
      `Delete ${clip.name}? This will also delete the paired ${clip.type === "hook" ? "reaction" : "hook"} clip if it exists.`
    );
    if (!ok) return;

    setDeleting(clip.path);
    try {
      await deleteClip(clip.persona, clip.type, clip.name);
      refreshClips();
    } catch {
      // ignore
    }
    setDeleting(null);
  };

  // Build a set of paired clips for indicators
  const pairedSet = new Set<string>();
  for (const c of clips) {
    if (c.persona && c.type) {
      const otherType = c.type === "hook" ? "reaction" : "hook";
      const pairPath = `${c.persona}/${otherType}/${c.name}`;
      if (clips.some((x) => x.path === pairPath)) {
        pairedSet.add(c.path);
      }
    }
  }

  const filteredClips = personaFilter === "all"
    ? clips
    : clips.filter((c) => c.persona === personaFilter);

  const canSubmitUpload =
    hookFile && selectedPersona && clipName && (reactionMode === "auto" || (reactionMode === "upload" && reactionFile));

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Asset Manager</h2>

      <Tabs defaultValue="images">
        <TabsList>
          <TabsTrigger value="images">
            Reference Images ({images.length})
          </TabsTrigger>
          <TabsTrigger value="clips">
            Generated Clips ({clips.length})
          </TabsTrigger>
          <TabsTrigger value="usage">
            Usage History ({usage.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="images" className="mt-4">
          <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {images.map((img) => (
              <Card key={img.name}>
                <CardContent className="pt-3 space-y-2">
                  <div className="aspect-[9/16] bg-muted rounded-md overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={assetUrl(img.path)}
                      alt={img.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    {img.persona && (
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          borderColor: PERSONA_COLORS[img.persona],
                          color: PERSONA_COLORS[img.persona],
                        }}
                      >
                        {img.persona}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {img.name}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="clips" className="mt-4 space-y-4">
          {/* Toolbar: filter + upload */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex gap-1 flex-wrap">
              {["all", ...PERSONAS].map((p) => (
                <Button
                  key={p}
                  variant={personaFilter === p ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPersonaFilter(p)}
                  className="capitalize"
                >
                  {p}{p !== "all" ? ` (${clips.filter((c) => c.persona === p).length})` : ""}
                </Button>
              ))}
            </div>
            {!showUpload && (
              <Button onClick={() => setShowUpload(true)} size="sm" className="gap-2">
                <Upload className="h-4 w-4" /> Upload Clip
              </Button>
            )}
          </div>

          {/* Upload form */}
          {showUpload && (
            <Card>
              <CardContent className="pt-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Upload New Clip</p>
                  <Button variant="ghost" size="sm" onClick={resetUpload}>Cancel</Button>
                </div>

                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Persona</label>
                  <div className="flex gap-2">
                    {PERSONAS.map((p) => (
                      <button
                        key={p}
                        onClick={() => {
                          setSelectedPersona(p);
                          if (uploadStep === "persona") setUploadStep("hook");
                        }}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors capitalize ${
                          selectedPersona === p
                            ? "bg-primary text-primary-foreground border-primary"
                            : "text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                {selectedPersona && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">Hook Video</label>
                    <input
                      type="file"
                      accept="video/mp4,video/quicktime,.mp4,.mov"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) {
                          setHookFile(f);
                          setClipName(f.name);
                          setUploadStep("reaction");
                        }
                      }}
                      className="text-sm"
                    />
                    {hookFile && (
                      <div className="mt-2">
                        <label className="text-xs font-medium text-muted-foreground mb-1 block">Filename</label>
                        <input
                          type="text"
                          value={clipName}
                          onChange={(e) => setClipName(e.target.value)}
                          className="w-full rounded-md border bg-background px-3 py-1.5 text-sm"
                        />
                      </div>
                    )}
                  </div>
                )}

                {hookFile && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">Reaction Clip</label>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setReactionMode("auto")}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          reactionMode === "auto"
                            ? "bg-primary text-primary-foreground border-primary"
                            : "text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        Auto-generate from hook (last 2.5s)
                      </button>
                      <button
                        onClick={() => setReactionMode("upload")}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          reactionMode === "upload"
                            ? "bg-primary text-primary-foreground border-primary"
                            : "text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        Upload Reaction
                      </button>
                    </div>
                    {reactionMode === "upload" && (
                      <input
                        type="file"
                        accept="video/mp4,video/quicktime,.mp4,.mov"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) setReactionFile(f);
                        }}
                        className="mt-2 text-sm"
                      />
                    )}
                  </div>
                )}

                {uploadError && (
                  <p className="text-sm text-destructive">{uploadError}</p>
                )}

                <Button
                  onClick={handleUploadSubmit}
                  disabled={!canSubmitUpload || uploadStep === "uploading"}
                  size="sm"
                  className="gap-2"
                >
                  {uploadStep === "uploading" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  {uploadStep === "uploading" ? "Uploading..." : "Upload"}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Clip grid — thumbnails, not video elements */}
          <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {filteredClips.map((clip) => (
              <Card key={clip.path} className="relative group">
                <CardContent className="pt-2 pb-2 px-2 space-y-1.5">
                  <div
                    className="aspect-[9/16] bg-muted rounded-md overflow-hidden relative cursor-pointer"
                    onClick={() => setPreviewClip(clip)}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={thumbnailUrl(clip.path)}
                      alt={clip.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Play className="h-6 w-6 text-white" />
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-wrap">
                    {clip.type && (
                      <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                        {clip.type}
                      </Badge>
                    )}
                    {clip.type && (
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 ${pairedSet.has(clip.path) ? "text-emerald-500 border-emerald-500" : "text-amber-500 border-amber-500"}`}
                      >
                        {pairedSet.has(clip.path) ? "paired" : "unpaired"}
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">
                    {clip.name}
                  </p>
                </CardContent>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(clip); }}
                  disabled={deleting === clip.path}
                  className="absolute top-1 right-1 p-1 rounded bg-background/80 border opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
                  title="Delete clip"
                >
                  {deleting === clip.path ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                </button>
              </Card>
            ))}
          </div>

          {/* Video preview dialog */}
          <Dialog open={!!previewClip} onOpenChange={() => setPreviewClip(null)}>
            <DialogContent className="max-w-md p-2">
              {previewClip && (
                <div className="space-y-2">
                  <video
                    src={assetUrl(previewClip.path)}
                    controls
                    autoPlay
                    className="w-full rounded-md bg-black"
                  />
                  <div className="flex items-center gap-2 px-1">
                    {previewClip.persona && (
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          borderColor: PERSONA_COLORS[previewClip.persona],
                          color: PERSONA_COLORS[previewClip.persona],
                        }}
                      >
                        {previewClip.persona}
                      </Badge>
                    )}
                    {previewClip.type && (
                      <Badge variant="secondary" className="text-xs">
                        {previewClip.type}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">{previewClip.name}</span>
                  </div>
                </div>
              )}
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="usage" className="mt-4">
          <Card>
            <CardContent className="pt-4">
              {usage.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No usage history yet
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 pr-4 font-medium">Date</th>
                        <th className="pb-2 pr-4 font-medium">Account</th>
                        <th className="pb-2 pr-4 font-medium">Hook Clip</th>
                        <th className="pb-2 pr-4 font-medium">Reaction Clip</th>
                        <th className="pb-2 font-medium">Screen Rec</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usage.map((row, i) => {
                        const persona = row.account.split(".")[0];
                        return (
                          <tr key={i} className="border-b last:border-0">
                            <td className="py-2 pr-4">{row.date}</td>
                            <td className="py-2 pr-4">
                              <Badge
                                variant="outline"
                                style={{
                                  borderColor: PERSONA_COLORS[persona],
                                  color: PERSONA_COLORS[persona],
                                }}
                              >
                                {row.account}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {row.hook_clip}
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {row.reaction_clip}
                            </td>
                            <td className="py-2 text-muted-foreground">
                              {row.screen_recording}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
