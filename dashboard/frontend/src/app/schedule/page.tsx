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
  { value: "weekdays", label: "Mon\u2013Fri" },
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

  function handleFrequencyChange(value: string) {
    if (!state) return;
    setState({ ...state, frequency: value });
    doUpdate({ frequency: value });
  }

  function handleDayToggle(day: number) {
    if (!state) return;
    const current = state.days_of_week;
    const next = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day].sort();
    setState({ ...state, days_of_week: next });
    doUpdate({ days_of_week: next });
  }

  function handleAccountTimeChange(account: string, value: string) {
    if (!state) return;
    setState({
      ...state,
      slots: state.slots.map((s) =>
        s.account === account
          ? { ...s, time_utc: value, time_ist: utcToIst(value) }
          : s
      ),
    });
    debouncedUpdate(`time_${account}`, {
      accounts: { [account]: { time_utc: value } },
    });
  }

  async function toggleAccount(slot: ScheduleSlot) {
    await doUpdate({
      accounts: { [slot.account]: { enabled: !slot.enabled } },
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

  const enabledCount = state.slots.filter((s) => s.enabled).length;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Schedule</h2>

      {/* Content Pipeline card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Content Pipeline</CardTitle>
          <span className="text-xs text-muted-foreground">
            {enabledCount} / {state.slots.length} accounts active
          </span>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Frequency</span>
            <select
              value={state.frequency}
              onChange={(e) => handleFrequencyChange(e.target.value)}
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
          {state.frequency === "custom" && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Days</span>
              <div className="flex gap-1">
                {DAY_LABELS.map((label, i) => (
                  <button
                    key={i}
                    onClick={() => handleDayToggle(i)}
                    disabled={updating}
                    className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                      state.days_of_week.includes(i)
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
        </CardContent>
      </Card>

      {/* Accounts table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Account</th>
                  <th className="pb-2 pr-4 font-medium">Time (UTC)</th>
                  <th className="pb-2 pr-4 font-medium">Time (IST)</th>
                  <th className="pb-2 pr-4 font-medium">Enabled</th>
                  <th className="pb-2 pr-4 font-medium">Last Run</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {state.slots.map((slot) => {
                  const persona = slot.account.includes(".")
                    ? slot.account.split(".")[0]
                    : slot.account === "sanyahealing"
                      ? "sanya"
                      : slot.account === "emillywilks"
                        ? "emilly"
                        : slot.account;
                  const color = PERSONA_COLORS[persona];
                  return (
                    <tr key={slot.account} className="border-b last:border-0">
                      <td className="py-3 pr-4">
                        <span
                          className="font-medium"
                          style={color ? { color } : undefined}
                        >
                          {slot.account}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          type="time"
                          value={slot.time_utc}
                          onChange={(e) =>
                            handleAccountTimeChange(slot.account, e.target.value)
                          }
                          disabled={updating}
                          className="rounded border border-input bg-background px-2 py-0.5 text-sm"
                        />
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {slot.time_ist}
                      </td>
                      <td className="py-3 pr-4">
                        <Button
                          variant={slot.enabled ? "default" : "outline"}
                          size="sm"
                          disabled={updating}
                          onClick={() => toggleAccount(slot)}
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
