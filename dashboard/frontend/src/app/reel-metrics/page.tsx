"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Eye,
  TrendingUp,
  BarChart3,
  Hash,
  Play,
  ArrowUpDown,
} from "lucide-react";

// ---------------------------------------------------------------------------
// API types & fetchers (inline — will move to api.ts later)
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface AccountSummary {
  account: string;
  handle: string;
  persona: string;
  app: string;
  reels_posted: number;
  total_views: number;
  avg_views: number;
}

interface MetricsSummary {
  accounts: AccountSummary[];
  total_reels: number;
  total_views: number;
  avg_views: number;
  last_scraped: string;
}

interface ReelData {
  id: string;
  url: string;
  views: number;
  likes: number;
  caption: string;
  hashtags: string[];
  timestamp: string;
  audio: string;
  account: string;
  persona: string;
}

interface PatternData {
  pattern: string;
  count: number;
  avg_views: number;
  best_hook: string;
  best_views: number;
  worst_views: number;
}

async function fetchMetricsSummary(): Promise<MetricsSummary> {
  const res = await fetch(API_BASE + "/api/reel-metrics/summary");
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

async function fetchTopReels(n: number = 15): Promise<ReelData[]> {
  const res = await fetch(API_BASE + "/api/reel-metrics/top?n=" + n);
  if (!res.ok) throw new Error("Failed to fetch top reels");
  return res.json();
}

async function fetchReels(account?: string): Promise<ReelData[]> {
  const url = account
    ? API_BASE + "/api/reel-metrics/reels?account=" + account + "&sort=views"
    : API_BASE + "/api/reel-metrics/reels?sort=views";
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch reels");
  return res.json();
}

async function fetchPatterns(): Promise<PatternData[]> {
  const res = await fetch(API_BASE + "/api/reel-metrics/patterns");
  if (!res.ok) throw new Error("Failed to fetch patterns");
  return res.json();
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
};

function personaColor(persona: string): string {
  return PERSONA_COLORS[persona.toLowerCase()] || "#6b7280";
}

function hookFromCaption(caption: string, maxLen = 80): string {
  const firstLine = caption.split("\n")[0] || caption;
  if (firstLine.length <= maxLen) return firstLine;
  return firstLine.slice(0, maxLen) + "\u2026";
}

function performanceTier(avgViews: number): { label: string; color: string } {
  if (avgViews >= 1000) return { label: "Top", color: "text-green-400" };
  if (avgViews >= 500) return { label: "Good", color: "text-emerald-400" };
  if (avgViews >= 200) return { label: "Mid", color: "text-yellow-400" };
  return { label: "Low", color: "text-red-400" };
}

type SortField = "views" | "date";

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ReelMetricsPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [topReels, setTopReels] = useState<ReelData[]>([]);
  const [allReels, setAllReels] = useState<ReelData[]>([]);
  const [patterns, setPatterns] = useState<PatternData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [accountFilter, setAccountFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortField>("views");
  const [expandedReel, setExpandedReel] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchMetricsSummary(),
      fetchTopReels(15),
      fetchReels(),
      fetchPatterns(),
    ])
      .then(([s, top, reels, pats]) => {
        setSummary(s);
        setTopReels(top);
        setAllReels(reels);
        setPatterns(pats);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Refetch reels when account filter changes
  useEffect(() => {
    if (loading) return;
    const acct = accountFilter === "all" ? undefined : accountFilter;
    fetchReels(acct)
      .then(setAllReels)
      .catch(() => {});
  }, [accountFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading reel metrics...
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Reel Performance</h2>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>{error || "No reel data available."}</p>
            <p className="text-sm mt-2">
              Make sure the reel-metrics API endpoints are running on the VPS.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Derived: sorted accounts
  const sortedAccounts = [...summary.accounts].sort(
    (a, b) => b.avg_views - a.avg_views
  );

  // Derive unique account names for filter
  const accountNames = summary.accounts.map((a) => a.account);

  // Filtered top reels
  const filteredTopReels =
    accountFilter === "all"
      ? topReels
      : topReels.filter((r) => r.account === accountFilter);

  // Sort reels
  const sortedReels = [...filteredTopReels].sort((a, b) => {
    if (sortBy === "views") return b.views - a.views;
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  // Sorted patterns
  const sortedPatterns = [...patterns].sort(
    (a, b) => b.avg_views - a.avg_views
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Reel Performance</h2>
        <span className="text-xs text-muted-foreground">
          Last scraped: {summary.last_scraped}
        </span>
      </div>

      {/* ---- Stat Cards ---- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Reels"
          value={summary.total_reels.toLocaleString()}
          icon={<Play className="h-4 w-4" />}
        />
        <StatCard
          title="Total Views"
          value={summary.total_views.toLocaleString()}
          icon={<Eye className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Views / Reel"
          value={summary.avg_views.toLocaleString()}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="Last Scraped"
          value={summary.last_scraped}
          icon={<BarChart3 className="h-4 w-4" />}
          small
        />
      </div>

      {/* ---- Filter / Sort Controls ---- */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground">Account</label>
          <select
            className="h-8 text-sm border rounded px-2 bg-background text-foreground"
            value={accountFilter}
            onChange={(e) => setAccountFilter(e.target.value)}
          >
            <option value="all">All Accounts</option>
            {accountNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground">Sort</label>
          <button
            className={`h-8 px-3 text-sm border rounded flex items-center gap-1 ${
              sortBy === "views"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-foreground"
            }`}
            onClick={() => setSortBy("views")}
          >
            <Eye className="h-3 w-3" /> Views
          </button>
          <button
            className={`h-8 px-3 text-sm border rounded flex items-center gap-1 ${
              sortBy === "date"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-foreground"
            }`}
            onClick={() => setSortBy("date")}
          >
            <ArrowUpDown className="h-3 w-3" /> Date
          </button>
        </div>
      </div>

      {/* ---- Account Performance Table ---- */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Hash className="h-4 w-4" />
            Account Performance
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left pl-4 py-2 font-medium">Account</th>
                  <th className="text-left py-2 font-medium">Persona</th>
                  <th className="text-left py-2 font-medium">App</th>
                  <th className="text-right py-2 font-medium pr-3">Reels</th>
                  <th className="text-right py-2 font-medium pr-3">
                    Total Views
                  </th>
                  <th className="text-right py-2 font-medium pr-4">
                    Avg Views
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedAccounts.map((acct) => {
                  const color = personaColor(acct.persona);
                  return (
                    <tr
                      key={acct.account}
                      className="border-b last:border-0 hover:bg-muted/50"
                    >
                      <td className="pl-4 py-2 flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full inline-block flex-shrink-0"
                          style={{ backgroundColor: color }}
                        />
                        <span className="font-medium">{acct.handle || acct.account}</span>
                      </td>
                      <td className="py-2">
                        <span
                          className="text-xs font-medium"
                          style={{ color }}
                        >
                          {acct.persona}
                        </span>
                      </td>
                      <td className="py-2 text-muted-foreground text-xs">
                        {acct.app}
                      </td>
                      <td className="py-2 text-right font-mono pr-3">
                        {acct.reels_posted.toLocaleString()}
                      </td>
                      <td className="py-2 text-right font-mono pr-3">
                        {acct.total_views.toLocaleString()}
                      </td>
                      <td
                        className={`py-2 text-right font-mono font-semibold pr-4 ${
                          acct.avg_views >= 500
                            ? "text-green-400"
                            : acct.avg_views >= 200
                            ? "text-yellow-400"
                            : "text-red-400"
                        }`}
                      >
                        {acct.avg_views.toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ---- Hook Pattern Analysis ---- */}
      {sortedPatterns.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Hook Pattern Analysis
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedPatterns.map((pat) => {
              const tier = performanceTier(pat.avg_views);
              return (
                <Card key={pat.pattern}>
                  <CardContent className="pt-4 pb-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold">
                        {pat.pattern}
                      </span>
                      <Badge
                        variant="secondary"
                        className={`text-xs ${tier.color}`}
                      >
                        {tier.label}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                      <div>
                        <p className="text-muted-foreground">Count</p>
                        <p className="font-mono font-medium">
                          {pat.count}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Avg Views</p>
                        <p className="font-mono font-medium">
                          {pat.avg_views.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Best</p>
                        <p className="font-mono font-medium text-green-400">
                          {pat.best_views.toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {/* Performance bar */}
                    <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            (pat.avg_views /
                              (sortedPatterns[0]?.avg_views || 1)) *
                              100
                          )}%`,
                          backgroundColor:
                            pat.avg_views >= 1000
                              ? "#22c55e"
                              : pat.avg_views >= 500
                              ? "#10b981"
                              : pat.avg_views >= 200
                              ? "#eab308"
                              : "#ef4444",
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {pat.best_hook}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Top Reels Leaderboard ---- */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Play className="h-4 w-4" />
            Top Reels
            {accountFilter !== "all" && (
              <Badge variant="secondary" className="text-xs">
                {accountFilter}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-center py-2 font-medium w-10 pl-4">
                    #
                  </th>
                  <th className="text-left py-2 font-medium">Hook</th>
                  <th className="text-left py-2 font-medium">Account</th>
                  <th className="text-right py-2 font-medium pr-3">Views</th>
                  <th className="text-right py-2 font-medium pr-3">Likes</th>
                  <th className="text-right py-2 font-medium pr-4">Date</th>
                </tr>
              </thead>
              <tbody>
                {sortedReels.map((reel, idx) => {
                  const isExpanded = expandedReel === reel.id;
                  const color = personaColor(reel.persona);
                  return (
                    <tr
                      key={reel.id}
                      className="border-b last:border-0 hover:bg-muted/50 cursor-pointer"
                      onClick={() =>
                        setExpandedReel(isExpanded ? null : reel.id)
                      }
                    >
                      <td className="text-center py-2 font-mono text-muted-foreground pl-4">
                        {idx + 1}
                      </td>
                      <td className="py-2 max-w-md">
                        <div className="text-sm">
                          {isExpanded
                            ? reel.caption
                            : hookFromCaption(reel.caption)}
                        </div>
                        {isExpanded && reel.hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {reel.hashtags.map((tag) => (
                              <span
                                key={tag}
                                className="text-xs text-muted-foreground"
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="py-2">
                        <span
                          className="text-xs font-medium"
                          style={{ color }}
                        >
                          {reel.account}
                        </span>
                      </td>
                      <td
                        className={`py-2 text-right font-mono pr-3 ${
                          reel.views >= 1000
                            ? "text-green-400 font-semibold"
                            : ""
                        }`}
                      >
                        {reel.views.toLocaleString()}
                      </td>
                      <td className="py-2 text-right font-mono pr-3">
                        {reel.likes.toLocaleString()}
                      </td>
                      <td className="py-2 text-right text-muted-foreground text-xs pr-4 whitespace-nowrap">
                        {new Date(reel.timestamp).toLocaleDateString()}
                      </td>
                    </tr>
                  );
                })}
                {sortedReels.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="py-8 text-center text-muted-foreground"
                    >
                      No reels found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatCard component
// ---------------------------------------------------------------------------

function StatCard({
  title,
  value,
  icon,
  small,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  small?: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground">{title}</span>
          <span className="text-muted-foreground">{icon}</span>
        </div>
        <div className={small ? "text-sm font-semibold" : "text-2xl font-bold"}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
