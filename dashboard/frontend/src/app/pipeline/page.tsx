"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { getRuns, getSpend, type PipelineRun, type DailySpend } from "@/lib/api";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { ChevronDown, ChevronRight } from "lucide-react";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
};

export default function PipelineMonitorPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [spend, setSpend] = useState<DailySpend[]>([]);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    getRuns().then((r) => setRuns([...r].reverse()));
    getSpend().then(setSpend);
  }, []);

  const filtered = runs.filter(
    (r) =>
      r.hook_text.toLowerCase().includes(search.toLowerCase()) ||
      r.persona.toLowerCase().includes(search.toLowerCase()) ||
      r.caption.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Pipeline Monitor</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Cost Trend (daily cap: $0.50)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {spend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={spend}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, "Spend"]} />
                <ReferenceLine
                  y={0.5}
                  stroke="#ef4444"
                  strokeDasharray="5 5"
                  label={{ value: "Cap $0.50", position: "right", fontSize: 11 }}
                />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#8b5cf6"
                  fill="#8b5cf620"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground">No spend data</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium">
            Run History ({filtered.length})
          </CardTitle>
          <Input
            placeholder="Search runs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {filtered.map((run, i) => (
              <div key={i} className="border rounded-md">
                <div
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50"
                  onClick={() => setExpanded(expanded === i ? null : i)}
                >
                  <div className="flex items-center gap-3">
                    {expanded === i ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                    <Badge
                      variant="outline"
                      style={{
                        borderColor: PERSONA_COLORS[run.persona],
                        color: PERSONA_COLORS[run.persona],
                      }}
                    >
                      {run.persona}
                    </Badge>
                    <span className="text-sm">{run.hook_text}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {run.video_type && <Badge variant="secondary">{run.video_type}</Badge>}
                    {run.reel_path ? (
                      <Badge variant="secondary">video</Badge>
                    ) : (
                      <Badge variant="outline">text only</Badge>
                    )}
                    <span>
                      {run.cost_usd != null ? `$${run.cost_usd.toFixed(2)}` : "—"}
                    </span>
                    <span className="w-36 text-right">
                      {new Date(run.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>

                {expanded === i && (
                  <div className="px-10 pb-3 space-y-2 text-sm border-t bg-muted/30">
                    <div className="pt-3 grid grid-cols-2 gap-4">
                      <div>
                        <p className="font-medium text-xs text-muted-foreground mb-1">
                          Reaction
                        </p>
                        <p>{run.reaction_text}</p>
                      </div>
                      <div>
                        <p className="font-medium text-xs text-muted-foreground mb-1">
                          Angle
                        </p>
                        <p>{run.content_angle || "—"}</p>
                      </div>
                    </div>
                    {run.caption && (
                      <div>
                        <p className="font-medium text-xs text-muted-foreground mb-1">
                          Caption
                        </p>
                        <p className="whitespace-pre-wrap text-muted-foreground">
                          {run.caption}
                        </p>
                      </div>
                    )}
                    {run.reel_path && (
                      <div>
                        <p className="font-medium text-xs text-muted-foreground mb-1">
                          Reel Path
                        </p>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {run.reel_path}
                        </code>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
