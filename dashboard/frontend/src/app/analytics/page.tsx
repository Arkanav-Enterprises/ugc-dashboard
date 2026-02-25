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
  type FunnelResult,
  type FunnelStep,
  type TrendSeries,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Send,
  Loader2,
  TrendingDown,
  Users,
  Percent,
  BarChart3,
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

  // AI Chat
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [f, t] = await Promise.all([
        getAnalyticsFunnel(app, dateRange),
        getAnalyticsTrends(app, dateRange),
      ]);
      setFunnel(f);
      setTrends(t);
    } catch {
      setFunnel({ steps: [], overall_conversion: 0, error: "Failed to load" });
      setTrends([]);
    }
    setLoading(false);
  };

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

  // Funnel bar chart data
  const funnelChartData = (funnel?.steps ?? []).map((s) => ({
    name: formatStepName(s.name),
    count: s.count,
    conversion_rate: s.conversion_rate,
    drop_off_rate: s.drop_off_rate,
  }));

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

          <div className="grid grid-cols-3 gap-4">
            {/* Funnel chart — 2 cols */}
            <Card className="col-span-2">
              <CardHeader>
                <CardTitle className="text-sm font-medium">Onboarding Funnel</CardTitle>
              </CardHeader>
              <CardContent>
                {funnelChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={funnelChartData} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis type="number" tick={{ fontSize: 12 }} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={140} />
                      <Tooltip
                        formatter={(value, _name, props) => {
                          const v = Number(value ?? 0);
                          const p = props?.payload as { conversion_rate?: number; drop_off_rate?: number } | undefined;
                          return [
                            `${v.toLocaleString()} users (${p?.conversion_rate ?? 0}% conv, ${p?.drop_off_rate ?? 0}% drop)`,
                            "Count",
                          ];
                        }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {funnelChartData.map((_entry, i) => (
                          <Cell key={i} fill={stepColor(i, funnelChartData.length)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-muted-foreground">No funnel data</p>
                )}
              </CardContent>
            </Card>

            {/* DAU trend — 1 col */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">DAU Trend</CardTitle>
              </CardHeader>
              <CardContent>
                {dauChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
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
          </div>

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
