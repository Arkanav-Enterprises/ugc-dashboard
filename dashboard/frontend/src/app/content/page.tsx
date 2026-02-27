"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getReels, videoByPathUrl, type PipelineRun } from "@/lib/api";
import { Copy, Play } from "lucide-react";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  sophie: "#3b82f6",
};

const PERSONAS = ["all", "aliyah", "riley", "sanya", "sophie"];

export default function ContentGalleryPage() {
  const [reels, setReels] = useState<PipelineRun[]>([]);
  const [personaFilter, setPersonaFilter] = useState("all");
  const [selected, setSelected] = useState<PipelineRun | null>(null);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (personaFilter !== "all") params.persona = personaFilter;
    getReels(params).then(setReels);
  }, [personaFilter]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Content Gallery</h2>

      <div className="flex gap-1 flex-wrap">
        {PERSONAS.map((p) => (
          <Button
            key={p}
            variant={personaFilter === p ? "default" : "outline"}
            size="sm"
            onClick={() => setPersonaFilter(p)}
            className="capitalize"
          >
            {p}
          </Button>
        ))}
      </div>

      {reels.length === 0 ? (
        <p className="text-muted-foreground">No reels found with current filters</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {reels.map((reel, i) => (
            <Card
              key={i}
              className="cursor-pointer hover:ring-2 ring-primary/50 transition-shadow"
              onClick={() => setSelected(reel)}
            >
              <CardContent className="pt-4 space-y-2">
                <div className="aspect-[9/16] bg-muted rounded-md flex items-center justify-center relative overflow-hidden">
                  {reel.reel_path ? (
                    <>
                      <video
                        src={videoByPathUrl(reel.reel_path)}
                        className="w-full h-full object-cover rounded-md"
                        muted
                        preload="metadata"
                      />
                      <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                        <Play className="h-8 w-8 text-white" />
                      </div>
                    </>
                  ) : (
                    <span className="text-xs text-muted-foreground">No video</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    style={{
                      borderColor: PERSONA_COLORS[reel.persona],
                      color: PERSONA_COLORS[reel.persona],
                    }}
                  >
                    {reel.persona}
                  </Badge>
                  {reel.video_type && (
                    <Badge variant="secondary" className="text-xs">
                      {reel.video_type}
                    </Badge>
                  )}
                </div>
                <p className="text-sm font-medium line-clamp-2">{reel.hook_text}</p>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    {new Date(reel.timestamp).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <span>
                    {reel.cost_usd != null ? `$${reel.cost_usd.toFixed(2)}` : "—"}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Video player modal */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Badge
                variant="outline"
                style={{
                  borderColor: selected
                    ? PERSONA_COLORS[selected.persona]
                    : undefined,
                  color: selected ? PERSONA_COLORS[selected.persona] : undefined,
                }}
              >
                {selected?.persona}
              </Badge>
              {selected?.hook_text}
            </DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              {selected.reel_path && (
                <video
                  src={videoByPathUrl(selected.reel_path)}
                  controls
                  autoPlay
                  className="w-full max-h-[60vh] rounded-md bg-black"
                />
              )}
              <div className="space-y-2 text-sm">
                <p>
                  <span className="font-medium">Reaction:</span>{" "}
                  {selected.reaction_text}
                </p>
                <p>
                  <span className="font-medium">Angle:</span>{" "}
                  {selected.content_angle}
                </p>
                <div className="relative">
                  <p className="font-medium mb-1">Caption:</p>
                  <div className="bg-muted p-3 rounded-md text-sm whitespace-pre-wrap">
                    {selected.caption}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-0 right-0"
                    onClick={() =>
                      navigator.clipboard.writeText(selected.caption)
                    }
                  >
                    <Copy className="h-3 w-3 mr-1" /> Copy
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
