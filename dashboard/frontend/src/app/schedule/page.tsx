"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getSchedule,
  updateSchedule,
  type ScheduleState,
  type ScheduleSlot,
  type CronHistoryEntry,
  type ScheduleUpdateRequest,
} from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
  aliyah: "#8b5cf6",
  riley: "#10b981",
  sanya: "#ef4444",
  emilly: "#3b82f6",
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const FREQUENCY_OPTIONS: { value: string; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekdays", label: "Mon–Fri" },
  { value: "every_2_days", label: "Every 2 days" },
  { value: "custom", label: "Custom" },
];

function utcToIst(utc: string): string {
  const [h, m] = utc.split(":").map(Number);
  const totalMin = h * 60 + m + 330; // +5:30
  const istH = Math.floor(totalMin / 60) % 24;
  const istM = totalMin % 60;
  const ampm = istH >= 12 ? "PM" : "AM";
  const h12 = istH % 12 || 12;
  return `${h12}:${String(istM).padStart(2, "0")} ${ampm} IST`;
}

export default function SchedulePage() {
  const [state, setState] = useState<ScheduleState | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

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

  async function doUpdate(data: ScheduleUpdateRequest) {
    setUpdating(true);
    try {
      const updated = await updateSchedule(data);
      setState(updated);
    } finally {
      setUpdating(false);
    }
  }

  function debouncedUpdate(key: string, data: ScheduleUpdateRequest, ms = 800) {
    if (debounceTimers.current[key]) clearTimeout(debounceTimers.current[key]);
    debounceTimers.current[key] = setTimeout(() => doUpdate(data), ms);
  }

  async function togglePipeline(pipeline: "video" | "text") {
    if (!state) return;
    const data =
      pipeline === "video"
        ? { video_pipeline_enabled: !state.video_pipeline_enabled }
        : { text_pipeline_enabled: !state.text_pipeline_enabled };
    await doUpdate(data);
  }

  async function toggleSlot(slot: ScheduleSlot) {
    const data =
      slot.type === "video"
        ? {
            video_personas: {
              [slot.account!]: { enabled: !slot.enabled },
            },
          }
        : {
            text_accounts: {
              [slot.account!]: { enabled: !slot.enabled },
            },
          };
    await doUpdate(data);
  }

  function handleVideoTimeChange(value: string) {
    if (!state) return;
    setState({ ...state, video_time_utc: value, video_time_ist: utcToIst(value) });
    debouncedUpdate("video_time", { video_time_utc: value });
  }

  function handleFrequencyChange(pipeline: "video" | "text", value: string) {
    if (!state) return;
    if (pipeline === "video") {
      setState({ ...state, video_frequency: value });
      doUpdate({ video_frequency: value });
    } else {
      setState({ ...state, text_frequency: value });
      doUpdate({ text_frequency: value });
    }
  }

  function handleDayToggle(pipeline: "video" | "text", day: number) {
    if (!state) return;
    const key = pipeline === "video" ? "video_days_of_week" : "text_days_of_week";
    const current = state[key];
    const next = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day].sort();
    if (pipeline === "video") {
      setState({ ...state, video_days_of_week: next });
      doUpdate({ video_days_of_week: next });
    } else {
      setState({ ...state, text_days_of_week: next });
      doUpdate({ text_days_of_week: next });
    }
  }

  function handleTextAccountTimeChange(account: string, value: string) {
    if (!state) return;
    // Optimistic update on slots
    setState({
      ...state,
      slots: state.slots.map((s) =>
        s.account === account && s.type === "text"
          ? { ...s, time_utc: value, time_ist: utcToIst(value) }
          : s
      ),
    });
    debouncedUpdate(`text_time_${account}`, {
      text_accounts: { [account]: { time_utc: value } },
    });
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

      {/* Pipeline control cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Video Pipeline Card */}
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
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Time (UTC)</span>
              <div className="flex items-center gap-2">
                <input
                  type="time"
                  value={state.video_time_utc}
                  onChange={(e) => handleVideoTimeChange(e.target.value)}
                  disabled={updating}
                  className="rounded border border-input bg-background px-2 py-1 text-sm"
                />
                <span className="text-xs text-muted-foreground">
                  {state.video_time_ist}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Frequency</span>
              <select
                value={state.video_frequency}
                onChange={(e) =>
                  handleFrequencyChange("video", e.target.value)
                }
                disabled={updating}
                className="rounded border border-input bg-background px-2 py-1 text-sm"
              >
                {FREQUENCY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            {state.video_frequency === "custom" && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Days</span>
                <div className="flex gap-1">
                  {DAY_LABELS.map((label, i) => (
                    <button
                      key={i}
                      onClick={() => handleDayToggle("video", i)}
                      disabled={updating}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                        state.video_days_of_week.includes(i)
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active accounts</span>
              <span>
                {videoSlots.filter((s) => s.enabled).length} /{" "}
                {videoSlots.length}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Text Pipeline Card */}
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
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Frequency</span>
              <select
                value={state.text_frequency}
                onChange={(e) =>
                  handleFrequencyChange("text", e.target.value)
                }
                disabled={updating}
                className="rounded border border-input bg-background px-2 py-1 text-sm"
              >
                {FREQUENCY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            {state.text_frequency === "custom" && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Days</span>
                <div className="flex gap-1">
                  {DAY_LABELS.map((label, i) => (
                    <button
                      key={i}
                      onClick={() => handleDayToggle("text", i)}
                      disabled={updating}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                        state.text_days_of_week.includes(i)
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active accounts</span>
              <span>
                {textSlots.filter((s) => s.enabled).length} /{" "}
                {textSlots.length}
              </span>
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
                  <th className="pb-2 pr-4 font-medium">Account</th>
                  <th className="pb-2 pr-4 font-medium">Time (UTC)</th>
                  <th className="pb-2 pr-4 font-medium">Time (IST)</th>
                  <th className="pb-2 pr-4 font-medium">Enabled</th>
                  <th className="pb-2 pr-4 font-medium">Last Run</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {state.slots.map((slot, i) => {
                  const name = slot.account || slot.persona || "\u2014";
                  const persona =
                    slot.persona ||
                    (slot.account ? slot.account.split(".")[0] : null);
                  const color =
                    persona && PERSONA_COLORS[persona]
                      ? PERSONA_COLORS[persona]
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
                      <td className="py-3 pr-4">
                        {slot.type === "text" ? (
                          <input
                            type="time"
                            value={slot.time_utc}
                            onChange={(e) =>
                              handleTextAccountTimeChange(
                                slot.account!,
                                e.target.value
                              )
                            }
                            disabled={updating}
                            className="rounded border border-input bg-background px-2 py-0.5 text-sm"
                          />
                        ) : (
                          <span className="text-muted-foreground">
                            {slot.time_utc}
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {slot.time_ist}
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
                          : "\u2014"}
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
                          <span className="text-muted-foreground">{"\u2014"}</span>
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
              {state.cron_history.map(
                (entry: CronHistoryEntry, i: number) => (
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
                )
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
