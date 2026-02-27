"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getRevenueCurrent,
  getRevenueHistory,
  type RevenueCurrentResponse,
  type RevenueSnapshot,
} from "@/lib/api";

const METRIC_CONFIG: {
  key: string;
  label: string;
  isMoney: boolean;
}[] = [
  { key: "mrr", label: "MRR", isMoney: true },
  { key: "revenue", label: "Revenue (28d)", isMoney: true },
  { key: "new_customers", label: "New Customers (28d)", isMoney: false },
  { key: "active_users", label: "Active Users", isMoney: false },
  { key: "active_subscriptions", label: "Active Subscriptions", isMoney: false },
  { key: "active_trials", label: "Active Trials", isMoney: false },
];

const PROJECT_LABELS: Record<string, string> = {
  manifest_lock: "Manifest Lock",
  journal_lock: "Journal Lock",
};

const PROJECT_COLORS: Record<string, string> = {
  manifest_lock: "#8b5cf6",
  journal_lock: "#10b981",
};

function formatValue(value: number, isMoney: boolean): string {
  if (isMoney) return `$${value.toFixed(2)}`;
  return value.toLocaleString();
}

function TrendBadge({ current, previous, isMoney }: { current: number; previous: number | undefined; isMoney: boolean }) {
  if (previous === undefined) return <span className="text-xs text-muted-foreground">--</span>;
  const delta = current - previous;
  if (delta === 0) return <Badge variant="secondary" className="text-xs font-normal">-&gt; 0</Badge>;

  const isUp = delta > 0;
  const label = isMoney ? `${isUp ? "+" : ""}$${delta.toFixed(2)}` : `${isUp ? "+" : ""}${delta}`;

  return (
    <Badge variant={isUp ? "default" : "destructive"} className="text-xs font-normal">
      {isUp ? "^" : "v"} {label}
    </Badge>
  );
}

export default function RevenuePage() {
  const [data, setData] = useState<RevenueCurrentResponse | null>(null);
  const [history, setHistory] = useState<RevenueSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getRevenueCurrent().catch((e) => { setError(e.message); return null; }),
      getRevenueHistory().catch(() => []),
    ]).then(([current, hist]) => {
      if (current) setData(current);
      setHistory(hist);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading revenue data...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Revenue</h2>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>{error || "No revenue data yet."}</p>
            <p className="text-sm mt-2">Run <code className="bg-muted px-1 rounded">python3 scripts/fetch_revenue_metrics.py</code> on the VPS first.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { current, previous } = data;
  const projects = Object.keys(current.projects);

  // Combined totals
  const totalMRR = projects.reduce((sum, p) => sum + (current.projects[p]?.mrr || 0), 0);
  const totalSubs = projects.reduce((sum, p) => sum + (current.projects[p]?.active_subscriptions || 0), 0);
  const totalTrials = projects.reduce((sum, p) => sum + (current.projects[p]?.active_trials || 0), 0);
  const totalRevenue = projects.reduce((sum, p) => sum + (current.projects[p]?.revenue || 0), 0);

  const prevMRR = previous ? projects.reduce((sum, p) => sum + (previous.projects[p]?.mrr || 0), 0) : undefined;
  const prevSubs = previous ? projects.reduce((sum, p) => sum + (previous.projects[p]?.active_subscriptions || 0), 0) : undefined;
  const prevTrials = previous ? projects.reduce((sum, p) => sum + (previous.projects[p]?.active_trials || 0), 0) : undefined;
  const prevRevenue = previous ? projects.reduce((sum, p) => sum + (previous.projects[p]?.revenue || 0), 0) : undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Revenue</h2>
        <span className="text-xs text-muted-foreground">Updated: {current.timestamp}</span>
      </div>

      {/* Combined stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total MRR", value: totalMRR, prev: prevMRR, money: true },
          { label: "Revenue (28d)", value: totalRevenue, prev: prevRevenue, money: true },
          { label: "Active Subscriptions", value: totalSubs, prev: prevSubs, money: false },
          { label: "Active Trials", value: totalTrials, prev: prevTrials, money: false },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold">{formatValue(stat.value, stat.money)}</span>
                <TrendBadge current={stat.value} previous={stat.prev} isMoney={stat.money} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Per-project tables */}
      {projects.map((projectKey) => {
        const metrics = current.projects[projectKey];
        const prevMetrics = previous?.projects[projectKey];
        const label = PROJECT_LABELS[projectKey] || projectKey;
        const color = PROJECT_COLORS[projectKey] || "#6b7280";

        return (
          <Card key={projectKey}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left py-2 font-medium">Metric</th>
                      <th className="text-right py-2 font-medium">Value</th>
                      <th className="text-right py-2 font-medium">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {METRIC_CONFIG.map(({ key, label: metricLabel, isMoney }) => {
                      const val = (metrics as Record<string, number>)[key] || 0;
                      const prevVal = prevMetrics ? (prevMetrics as Record<string, number>)[key] : undefined;
                      return (
                        <tr key={key} className="border-b last:border-0">
                          <td className="py-2">{metricLabel}</td>
                          <td className="py-2 text-right font-mono">{formatValue(val, isMoney)}</td>
                          <td className="py-2 text-right">
                            <TrendBadge current={val} previous={prevVal} isMoney={isMoney} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        );
      })}

      {/* History */}
      {history.length > 1 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">History ({history.length} snapshots)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="text-left py-2 font-medium">Date</th>
                    {projects.map((p) => (
                      <th key={p} className="text-right py-2 font-medium" colSpan={2}>
                        {PROJECT_LABELS[p] || p}
                      </th>
                    ))}
                  </tr>
                  <tr className="border-b text-muted-foreground text-xs">
                    <th />
                    {projects.map((p) => (
                      <><th key={`${p}-mrr`} className="text-right py-1">MRR</th><th key={`${p}-trials`} className="text-right py-1">Trials</th></>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...history].reverse().slice(0, 30).map((entry, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2 text-muted-foreground">{entry.timestamp}</td>
                      {projects.map((p) => {
                        const m = entry.projects[p];
                        return (
                          <>
                            <td key={`${p}-mrr-${i}`} className="py-2 text-right font-mono">${(m?.mrr || 0).toFixed(2)}</td>
                            <td key={`${p}-trials-${i}`} className="py-2 text-right font-mono">{m?.active_trials || 0}</td>
                          </>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
