"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getSchedule,
  updateSchedule,
  type ScheduleState,
  type ScheduleSlot,
  type CronHistoryEntry,
} from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
  sanya: "#ef4444",
  sophie: "#3b82f6",
  aliyah: "#8b5cf6",
};

const VIDEO_TYPE_OPTIONS = ["auto", "original", "ugc_lighting", "outdoor"];

export default function SchedulePage() {
  const [state, setState] = useState<ScheduleState | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  const fetchSchedule = useCallback(async () => {
    try {
      const data = await getSchedule();
      setState(data);
    } catch (err) {
      console.error("Failed to fetch schedule:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedule();
    const interval = setInterval(fetchSchedule, 60_000);
    return () => clearInterval(interval);
  }, [fetchSchedule]);

  async function togglePipeline(pipeline: "video" | "text") {
    if (!state) return;
    setUpdating(true);
    try {
      const data =
        pipeline === "video"
          ? { video_pipeline_enabled: !state.video_pipeline_enabled }
          : { text_pipeline_enabled: !state.text_pipeline_enabled };
      const updated = await updateSchedule(data);
      setState(updated);
    } finally {
      setUpdating(false);
    }
  }

  async function toggleSlot(slot: ScheduleSlot) {
    setUpdating(true);
    try {
      const data =
        slot.type === "video"
          ? {
              video_personas: {
                [slot.persona!]: { enabled: !slot.enabled },
              },
            }
          : {
              text_accounts: {
                [slot.account!]: { enabled: !slot.enabled },
              },
            };
      const updated = await updateSchedule(data);
      setState(updated);
    } finally {
      setUpdating(false);
    }
  }

  async function changeVideoType(persona: string, videoType: string) {
    setUpdating(true);
    try {
      const updated = await updateSchedule({
        video_personas: { [persona]: { video_type: videoType } },
      });
      setState(updated);
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Schedule</h2>
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Schedule</h2>
        <p className="text-muted-foreground">
          Failed to load schedule. Is the backend running?
        </p>
      </div>
    );
  }

  const videoSlots = state.slots.filter((s) => s.type === "video");
  const textSlots = state.slots.filter((s) => s.type === "text");

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Schedule</h2>

      {/* Pipeline status cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Video Pipeline
            </CardTitle>
            <Badge
              variant={state.video_pipeline_enabled ? "default" : "secondary"}
              className="cursor-pointer"
              onClick={() => togglePipeline("video")}
            >
              {state.video_pipeline_enabled ? "Enabled" : "Disabled"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Time</span>
                <span>{state.video_time_ist}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  Today&apos;s video type
                </span>
                <Badge variant="outline">{state.today_video_type}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active personas</span>
                <span>{videoSlots.filter((s) => s.enabled).length} / {videoSlots.length}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Text Pipeline
            </CardTitle>
            <Badge
              variant={state.text_pipeline_enabled ? "default" : "secondary"}
              className="cursor-pointer"
              onClick={() => togglePipeline("text")}
            >
              {state.text_pipeline_enabled ? "Enabled" : "Disabled"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Time range</span>
                <span>7:00 &ndash; 7:30 AM IST</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active accounts</span>
                <span>{textSlots.filter((s) => s.enabled).length} / {textSlots.length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Schedule table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Schedule Slots</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Type</th>
                  <th className="pb-2 pr-4 font-medium">Persona / Account</th>
                  <th className="pb-2 pr-4 font-medium">Time (IST)</th>
                  <th className="pb-2 pr-4 font-medium">Video Type</th>
                  <th className="pb-2 pr-4 font-medium">Enabled</th>
                  <th className="pb-2 pr-4 font-medium">Last Run</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {state.slots.map((slot, i) => {
                  const name = slot.persona || slot.account || "—";
                  const color =
                    slot.persona && PERSONA_COLORS[slot.persona]
                      ? PERSONA_COLORS[slot.persona]
                      : undefined;
                  return (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-3 pr-4">
                        <Badge variant="outline">
                          {slot.type === "video" ? "Video" : "Text"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className="font-medium"
                          style={color ? { color } : undefined}
                        >
                          {name}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {slot.time_ist}
                      </td>
                      <td className="py-3 pr-4">
                        {slot.type === "video" ? (
                          <select
                            className="bg-transparent border rounded px-2 py-1 text-sm"
                            value={slot.video_type || "auto"}
                            disabled={updating}
                            onChange={(e) =>
                              changeVideoType(slot.persona!, e.target.value)
                            }
                          >
                            {VIDEO_TYPE_OPTIONS.map((vt) => (
                              <option key={vt} value={vt}>
                                {vt}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        <Button
                          variant={slot.enabled ? "default" : "outline"}
                          size="sm"
                          disabled={updating}
                          onClick={() => toggleSlot(slot)}
                        >
                          {slot.enabled ? "On" : "Off"}
                        </Button>
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground text-xs">
                        {slot.last_run
                          ? new Date(slot.last_run).toLocaleString()
                          : "—"}
                      </td>
                      <td className="py-3">
                        {slot.last_status ? (
                          <Badge
                            variant={
                              slot.last_status === "ok"
                                ? "default"
                                : "secondary"
                            }
                          >
                            {slot.last_status}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Cron history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Recent Cron Runs ({state.cron_history.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {state.cron_history.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No cron history found (logs/cron.log)
            </p>
          ) : (
            <div className="space-y-1">
              {state.cron_history.map((entry: CronHistoryEntry, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2 border-b last:border-0 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        entry.status === "ok"
                          ? "default"
                          : entry.status === "failed"
                            ? "destructive"
                            : "secondary"
                      }
                    >
                      {entry.status}
                    </Badge>
                    <span className="text-muted-foreground">
                      {entry.message}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {entry.timestamp}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
