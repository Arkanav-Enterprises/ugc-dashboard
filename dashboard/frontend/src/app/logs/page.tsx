"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getRuns, getSpend, type PipelineRun, type DailySpend } from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
  sanya: "#ef4444",
  emilly: "#3b82f6",
  aliyah: "#8b5cf6",
  olivia: "#f59e0b",
  riley: "#10b981",
};

export default function LogsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [spend, setSpend] = useState<DailySpend[]>([]);

  useEffect(() => {
    getRuns().then(setRuns);
    getSpend().then(setSpend);
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Logs</h2>

      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline">Pipeline Logs</TabsTrigger>
          <TabsTrigger value="spend">Daily Spend</TabsTrigger>
          <TabsTrigger value="raw">Raw JSONL</TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                All Pipeline Runs ({runs.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 pr-3 font-medium">Time</th>
                      <th className="pb-2 pr-3 font-medium">Persona</th>
                      <th className="pb-2 pr-3 font-medium">Type</th>
                      <th className="pb-2 pr-3 font-medium">Hook</th>
                      <th className="pb-2 pr-3 font-medium">Angle</th>
                      <th className="pb-2 pr-3 font-medium">Video</th>
                      <th className="pb-2 font-medium">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...runs].reverse().map((run, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2 pr-3 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(run.timestamp).toLocaleString()}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge
                            variant="outline"
                            style={{
                              borderColor: PERSONA_COLORS[run.persona],
                              color: PERSONA_COLORS[run.persona],
                            }}
                          >
                            {run.persona}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3 text-xs">
                          {run.video_type || "—"}
                        </td>
                        <td className="py-2 pr-3 max-w-xs truncate">
                          {run.hook_text}
                        </td>
                        <td className="py-2 pr-3 text-xs">
                          {run.content_angle || "—"}
                        </td>
                        <td className="py-2 pr-3">
                          {run.reel_path ? (
                            <Badge variant="secondary" className="text-xs">
                              yes
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              no
                            </span>
                          )}
                        </td>
                        <td className="py-2 text-xs">
                          {run.cost_usd != null
                            ? `$${run.cost_usd.toFixed(2)}`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="spend" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Daily Spend Ledger
              </CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 pr-4 font-medium">Date</th>
                    <th className="pb-2 font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {spend.map((s) => (
                    <tr key={s.date} className="border-b last:border-0">
                      <td className="py-2 pr-4">{s.date}</td>
                      <td className="py-2 font-mono">
                        ${s.amount.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                  {spend.length > 0 && (
                    <tr className="font-medium">
                      <td className="py-2 pr-4">Total</td>
                      <td className="py-2 font-mono">
                        ${spend.reduce((a, s) => a + s.amount, 0).toFixed(2)}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="raw" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Raw JSONL (video_autopilot.jsonl)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <pre className="text-xs font-mono whitespace-pre-wrap bg-muted p-4 rounded-md">
                  {runs.map((r) => JSON.stringify(r, null, 0)).join("\n")}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
