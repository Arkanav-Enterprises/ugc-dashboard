"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getAnalyticsFunnel,
  getAnalyticsTrends,
  streamAnalyticsAsk,
  getFunnelSnapshots,
  saveFunnelSnapshot,
  type FunnelResult,
  type FunnelSnapshot,
  type TrendSeries,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Send,
  Loader2,
  TrendingDown,
  Users,
  Percent,
  BarChart3,
  Save,
} from "lucide-react";

const APPS = [
  { key: "manifest-lock", label: "Manifest Lock" },
  { key: "journal-lock", label: "Journal Lock" },
];

const DATE_RANGES = [
  { key: "-7d", label: "7d" },
  { key: "-30d", label: "30d" },
  { key: "-90d", label: "90d" },
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

function stepColor(index: number, total: number): string {
  // green → amber → red gradient
  const ratio = total > 1 ? index / (total - 1) : 0;
  if (ratio < 0.5) {
    return `hsl(${120 - ratio * 120}, 70%, 45%)`;
  }
  return `hsl(${60 - (ratio - 0.5) * 120}, 70%, 45%)`;
}

function formatStepName(name: string): string {
  return name
    .replace(/^onboarding_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AnalyticsPage() {
  const [app, setApp] = useState(APPS[0].key);
  const [dateRange, setDateRange] = useState("-30d");
  const [funnel, setFunnel] = useState<FunnelResult | null>(null);
  const [trends, setTrends] = useState<TrendSeries[]>([]);
  const [loading, setLoading] = useState(true);

  // Snapshots
  const [snapshots, setSnapshots] = useState<FunnelSnapshot[]>([]);
  const [compareIdx, setCompareIdx] = useState<number>(-1);
  const [saving, setSaving] = useState(false);
  const [saveNotes, setSaveNotes] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);

  // AI Chat
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [f, t, s] = await Promise.all([
        getAnalyticsFunnel(app, dateRange),
        getAnalyticsTrends(app, dateRange),
        getFunnelSnapshots(app),
      ]);
      setFunnel(f);
      setTrends(t);
      setSnapshots(s);
      setCompareIdx(-1);
    } catch {
      setFunnel({ steps: [], overall_conversion: 0, error: "Failed to load" });
      setTrends([]);
      setSnapshots([]);
    }
    setLoading(false);
  };

  const handleSaveSnapshot = async () => {
    setSaving(true);
    try {
      await saveFunnelSnapshot(app, dateRange, saveNotes || undefined);
      const s = await getFunnelSnapshots(app);
      setSnapshots(s);
      setShowSaveInput(false);
      setSaveNotes("");
    } catch {
      // ignore
    }
    setSaving(false);
  };

  // Build a map of snapshot step conversion rates for comparison
  const compareSnapshot = compareIdx >= 0 ? snapshots[compareIdx] : null;
  const snapshotConvMap: Record<string, number> = {};
  if (compareSnapshot) {
    const ss = compareSnapshot.steps;
    if (Array.isArray(ss)) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const items = ss as any[];
      const firstCount = items[0]?.count ?? 1;
      for (const s of items) {
        if (s && typeof s === "object" && s.name) {
          if (typeof s.conversion_rate === "number") {
            snapshotConvMap[s.name] = s.conversion_rate;
          } else if (typeof s.count === "number" && firstCount > 0) {
            snapshotConvMap[s.name] = (s.count / firstCount) * 100;
          }
        }
      }
    }
  }

  useEffect(() => {
    loadData();
  }, [app, dateRange]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!chatInput.trim() || streaming) return;

    const userMsg: ChatMessage = { role: "user", content: chatInput.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setStreaming(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    await streamAnalyticsAsk(
      userMsg.content,
      history,
      (chunk) => {
        assistantContent += chunk;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: assistantContent };
          return next;
        });
      },
      () => setStreaming(false),
      (err) => {
        assistantContent += `\n\nError: ${err}`;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: assistantContent };
          return next;
        });
        setStreaming(false);
      }
    );
  };

  // Derived stats
  const overallConversion = funnel?.overall_conversion ?? 0;
  const funnelEntries = funnel?.steps?.[0]?.count ?? 0;
  const biggestDropOff = funnel?.steps?.length
    ? funnel.steps.reduce((max, s) => (s.drop_off_rate > max.drop_off_rate ? s : max), funnel.steps[0])
    : null;

  // Compute avg DAU from first trend series
  const dauSeries = trends.find((t) => t.data.length > 0);
  const avgDau = dauSeries
    ? Math.round(dauSeries.data.reduce((a, b) => a + b, 0) / dauSeries.data.length)
    : 0;

  // Chart data for DAU line
  const dauChartData = dauSeries
    ? dauSeries.labels.map((label, i) => ({ date: label, dau: dauSeries.data[i] ?? 0 }))
    : [];

  // Funnel rows with optional delta from snapshot comparison
  const funnelRows = (funnel?.steps ?? []).map((s) => {
    let delta = "";
    const prevConv = snapshotConvMap[s.name];
    if (prevConv !== undefined) {
      const diff = s.conversion_rate - prevConv;
      if (Math.abs(diff) < 0.1) delta = "=";
      else delta = diff > 0 ? `↑+${diff.toFixed(1)}%` : `↓${diff.toFixed(1)}%`;
    }
    let flag = "";
    if (s.drop_off_rate >= 25) flag = "CLIFF";
    else if (s.name === "onboarding_completed" && s.count === 0) flag = "BUG";
    return { ...s, delta, flag };
  });
  const maxCount = funnelRows[0]?.count || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Analytics</h2>
        <div className="flex items-center gap-2">
          {APPS.map((a) => (
            <Button
              key={a.key}
              variant={app === a.key ? "default" : "outline"}
              size="sm"
              onClick={() => setApp(a.key)}
            >
              {a.label}
            </Button>
          ))}
          <div className="w-px h-6 bg-border mx-1" />
          {DATE_RANGES.map((d) => (
            <Button
              key={d.key}
              variant={dateRange === d.key ? "default" : "outline"}
              size="sm"
              onClick={() => setDateRange(d.key)}
            >
              {d.label}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading analytics...
        </div>
      ) : funnel?.error ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            {funnel.error}. Make sure POSTHOG_API_KEY is set on the VPS.
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-4 gap-4">
            <StatCard
              title="Overall Conversion"
              value={`${overallConversion}%`}
              icon={<Percent className="h-4 w-4" />}
            />
            <StatCard
              title="Avg DAU"
              value={avgDau}
              icon={<Users className="h-4 w-4" />}
            />
            <StatCard
              title="Biggest Drop-off"
              value={biggestDropOff ? `${formatStepName(biggestDropOff.name)} (${biggestDropOff.drop_off_rate}%)` : "—"}
              icon={<TrendingDown className="h-4 w-4" />}
              small
            />
            <StatCard
              title="Funnel Entries"
              value={funnelEntries.toLocaleString()}
              icon={<BarChart3 className="h-4 w-4" />}
            />
          </div>

          {/* Funnel table — full width */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Onboarding Funnel — {funnelEntries} started, {funnel?.steps?.[funnel.steps.length - 1]?.count ?? 0} completed ({overallConversion}%)
              </CardTitle>
              <div className="flex items-center gap-2">
                {showSaveInput ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      placeholder="Change notes (optional)"
                      value={saveNotes}
                      onChange={(e) => setSaveNotes(e.target.value)}
                      className="h-7 text-xs border rounded px-2 w-48 bg-background"
                      onKeyDown={(e) => e.key === "Enter" && handleSaveSnapshot()}
                    />
                    <Button size="sm" variant="default" onClick={handleSaveSnapshot} disabled={saving} className="h-7 text-xs">
                      {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : "Save"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setShowSaveInput(false)} className="h-7 text-xs">
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => setShowSaveInput(true)} className="h-7 text-xs gap-1">
                    <Save className="h-3 w-3" /> Save Snapshot
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {funnelRows.length > 0 ? (
                <div className="bg-zinc-950 rounded-b-lg overflow-x-auto">
                  <table className="w-full font-mono text-[13px] leading-6">
                    <thead>
                      <tr className="text-zinc-400 border-b border-zinc-800">
                        <th className="text-left pl-4 pr-2 py-2 font-normal">Step</th>
                        <th className="text-right px-2 py-2 font-normal w-16">Count</th>
                        <th className="text-left px-2 py-2 font-normal w-40">Funnel</th>
                        <th className="text-right px-2 py-2 font-normal w-14">Conv</th>
                        <th className="text-right px-2 py-2 font-normal w-20">Drop-off</th>
                        {compareSnapshot && <th className="text-right px-2 py-2 font-normal w-20">vs prev</th>}
                        <th className="pr-4 py-2 w-24"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {funnelRows.map((row, i) => {
                        const barPct = maxCount > 0 ? (row.count / maxCount) * 100 : 0;
                        return (
                          <tr key={i} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                            <td className="text-zinc-200 pl-4 pr-2 py-1 whitespace-nowrap">
                              {row.name.replace(/^onboarding_/, "")}
                            </td>
                            <td className="text-zinc-300 text-right px-2 py-1 tabular-nums">{row.count}</td>
                            <td className="px-2 py-1">
                              <div className="h-4 w-full bg-zinc-800 rounded-sm overflow-hidden">
                                <div
                                  className="h-full rounded-sm"
                                  style={{
                                    width: `${barPct}%`,
                                    backgroundColor: stepColor(i, funnelRows.length),
                                    opacity: 0.8,
                                  }}
                                />
                              </div>
                            </td>
                            <td className="text-zinc-300 text-right px-2 py-1 tabular-nums">{row.conversion_rate}%</td>
                            <td className={`text-right px-2 py-1 tabular-nums ${row.drop_off_rate > 0 ? "text-red-400" : "text-zinc-600"}`}>
                              {row.drop_off_rate > 0 ? `-${row.drop_off_rate}%` : ""}
                            </td>
                            {compareSnapshot && (
                              <td className={`text-right px-2 py-1 tabular-nums text-xs ${
                                row.delta.startsWith("↑") ? "text-green-400" : row.delta.startsWith("↓") ? "text-red-400" : "text-zinc-600"
                              }`}>
                                {row.delta}
                              </td>
                            )}
                            <td className="pr-4 py-1 text-xs font-bold">
                              {row.flag === "CLIFF" && <span className="text-amber-400">&lt;&lt; CLIFF</span>}
                              {row.flag === "BUG" && <span className="text-red-500">&lt;&lt; BUG</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  <div className="px-4 py-3 text-zinc-400 text-xs font-mono border-t border-zinc-800 flex items-center justify-between">
                    <span>
                      Overall: {overallConversion}% &nbsp;|&nbsp; Started: {funnelEntries} &nbsp;|&nbsp; Completed: {funnel?.steps?.[funnel.steps.length - 1]?.count ?? 0}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-500">Compare:</span>
                      <select
                        className="h-6 text-xs border border-zinc-700 rounded px-1 bg-zinc-900 text-zinc-300"
                        value={compareIdx}
                        onChange={(e) => setCompareIdx(Number(e.target.value))}
                      >
                        <option value={-1}>None</option>
                        {snapshots.map((s, i) => (
                          <option key={i} value={i}>
                            {s.date} ({s.overall_conversion}%){s.changes_pending?.length ? ` — ${s.changes_pending[0]}` : ""}
                          </option>
                        ))}
                      </select>
                      {compareSnapshot && (() => {
                        const diff = overallConversion - compareSnapshot.overall_conversion;
                        if (Math.abs(diff) < 0.1) return <span className="text-zinc-500">=</span>;
                        return diff > 0
                          ? <span className="text-green-400 font-bold">↑+{diff.toFixed(1)}%</span>
                          : <span className="text-red-400 font-bold">↓{diff.toFixed(1)}%</span>;
                      })()}
                    </div>
                  </div>
                  {compareSnapshot?.changes_pending?.length ? (
                    <div className="px-4 pb-3 text-zinc-500 text-xs font-mono">
                      Notes: {compareSnapshot.changes_pending.join(", ")}
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground p-4">No funnel data</p>
              )}
            </CardContent>
          </Card>

          {/* DAU trend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">DAU Trend</CardTitle>
            </CardHeader>
            <CardContent>
              {dauChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={dauChartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="dau"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground">No trend data</p>
              )}
            </CardContent>
          </Card>

          {/* AI Chat panel */}
          <Card className="flex flex-col" style={{ height: 400 }}>
            <CardHeader className="pb-2 border-b">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                Ask about analytics
                <Badge variant="secondary" className="text-xs">AI</Badge>
              </CardTitle>
            </CardHeader>
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Ask questions about your funnel data, retention, or feature usage.
                  </p>
                )}
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {msg.role === "assistant" ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            code: ({ children }) => (
                              <code className="bg-background/50 px-1 rounded text-xs">{children}</code>
                            ),
                          }}
                        >
                          {msg.content || "..."}
                        </ReactMarkdown>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}
                <div ref={scrollRef} />
              </div>
            </ScrollArea>
            <div className="p-4 border-t flex gap-2">
              <Textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="What's the biggest conversion bottleneck?"
                className="min-h-[44px] max-h-32 resize-none"
                rows={1}
              />
              <Button
                onClick={sendMessage}
                disabled={streaming || !chatInput.trim()}
                size="icon"
              >
                {streaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

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
        <div className={small ? "text-sm font-semibold" : "text-2xl font-bold"}>{value}</div>
      </CardContent>
    </Card>
  );
}
