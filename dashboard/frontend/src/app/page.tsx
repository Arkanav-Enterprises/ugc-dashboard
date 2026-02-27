"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getOverview,
  getSpend,
  getRuns,
  type OverviewStats,
  type PersonaStats,
  type DailySpend,
  type PipelineRun,
} from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity, DollarSign, Film, TrendingUp } from "lucide-react";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  sophie: "#3b82f6",
};

export default function OverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [personas, setPersonas] = useState<PersonaStats[]>([]);
  const [spend, setSpend] = useState<DailySpend[]>([]);
  const [recentRuns, setRecentRuns] = useState<PipelineRun[]>([]);

  const load = () => {
    getOverview().then((d) => {
      setStats(d.stats);
      setPersonas(d.personas);
    });
    getSpend().then(setSpend);
    getRuns().then((runs) => setRecentRuns(runs.slice(-10).reverse()));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div className="text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Overview</h2>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Today's Runs"
          value={stats.today_runs}
          icon={<Activity className="h-4 w-4" />}
        />
        <StatCard
          title="Today's Cost"
          value={`$${stats.today_cost.toFixed(2)} / $${stats.daily_cap.toFixed(2)}`}
          icon={<DollarSign className="h-4 w-4" />}
        />
        <StatCard
          title="Total Reels"
          value={stats.total_reels}
          icon={<Film className="h-4 w-4" />}
        />
        <StatCard
          title="Total Spend"
          value={`$${stats.total_spend.toFixed(2)}`}
          icon={<TrendingUp className="h-4 w-4" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Daily Cost</CardTitle>
        </CardHeader>
        <CardContent>
          {spend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={spend}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, "Cost"]} />
                <Line
                  type="monotone"
                  dataKey="amount"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground">No spend data yet</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Recent Runs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recentRuns.map((run, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm border-b pb-2 last:border-0"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Badge
                        variant="outline"
                        style={{
                          borderColor: PERSONA_COLORS[run.persona],
                          color: PERSONA_COLORS[run.persona],
                        }}
                      >
                        {run.persona}
                      </Badge>
                      <span className="truncate text-muted-foreground">
                        {run.hook_text}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-2">
                      {run.reel_path && (
                        <Badge variant="secondary" className="text-xs">
                          video
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {run.cost_usd != null ? `$${run.cost_usd.toFixed(2)}` : "—"}
                      </span>
                      <span className="text-xs text-muted-foreground w-28 text-right">
                        {new Date(run.timestamp).toLocaleString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          {personas.map((p) => (
            <Card key={p.persona}>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: p.color }}
                  />
                  <span className="font-medium capitalize">{p.persona}</span>
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>{p.total_runs} runs total</p>
                  <p>
                    {p.hook_clips} hook / {p.reaction_clips} reaction clips
                  </p>
                  {p.last_run && (
                    <p>
                      Last:{" "}
                      {new Date(p.last_run).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground">{title}</span>
          <span className="text-muted-foreground">{icon}</span>
        </div>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}
