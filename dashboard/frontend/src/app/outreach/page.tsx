"use client";

import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getOutreachAccounts,
  parseOutreachMarkdown,
  streamOutreachSend,
  getOutreachHistory,
  getOutreachBatch,
  OutreachAccount,
  OutreachEmail,
  OutreachBatchListItem,
  OutreachBatchResult,
} from "@/lib/api";
import {
  Mail,
  Loader2,
  Check,
  X,
  Clock,
  ChevronDown,
  ChevronRight,
  Send,
  AlertTriangle,
} from "lucide-react";

type Phase = "input" | "preview" | "sending" | "results";

export default function OutreachPage() {
  const [phase, setPhase] = useState<Phase>("input");

  // Input
  const [markdown, setMarkdown] = useState("");
  const [parseError, setParseError] = useState("");

  // Preview
  const [emails, setEmails] = useState<OutreachEmail[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [accounts, setAccounts] = useState<OutreachAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [delay, setDelay] = useState(45);
  const [fromName, setFromName] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);

  // Sending
  const [sending, setSending] = useState(false);
  const [currentEmail, setCurrentEmail] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [emailStatuses, setEmailStatuses] = useState<
    Record<number, "sending" | "sent" | "failed">
  >({});
  const [waitCountdown, setWaitCountdown] = useState(0);
  const [batchId, setBatchId] = useState("");
  const [error, setError] = useState("");
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Results
  const [sentCount, setSentCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  // History
  const [history, setHistory] = useState<OutreachBatchListItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [viewingBatch, setViewingBatch] = useState<OutreachBatchResult | null>(null);

  useEffect(() => {
    getOutreachAccounts().then((accs) => {
      setAccounts(accs);
      if (accs.length > 0) setSelectedAccount(accs[0].label);
    }).catch(() => {});
    getOutreachHistory().then(setHistory).catch(() => {});
  }, []);

  const handleParse = async () => {
    setParseError("");
    try {
      const res = await parseOutreachMarkdown(markdown);
      if (res.emails.length === 0) {
        setParseError("No emails found. Check your markdown format.");
        return;
      }
      setEmails(res.emails);
      const sendable = new Set(
        res.emails.filter((e) => !e.skip).map((e) => e.index)
      );
      setSelectedIndices(sendable);
      setPhase("preview");
    } catch (e) {
      setParseError(e instanceof Error ? e.message : "Parse failed");
    }
  };

  const sendableEmails = emails.filter(
    (e) => !e.skip && selectedIndices.has(e.index)
  );

  const handleSend = async () => {
    setShowConfirm(false);
    setPhase("sending");
    setSending(true);
    setError("");
    setProgress(0);
    setTotal(sendableEmails.length);
    setEmailStatuses({});
    setSentCount(0);
    setFailedCount(0);
    setBatchId("");

    await streamOutreachSend(
      sendableEmails,
      selectedAccount,
      delay,
      fromName || null,
      (event) => {
        switch (event.type) {
          case "batch_start":
            setTotal(event.total as number);
            setBatchId(event.batch_id as string);
            break;
          case "sending":
            setCurrentEmail(event.to as string);
            setEmailStatuses((prev) => ({
              ...prev,
              [event.index as number]: "sending",
            }));
            break;
          case "email_sent":
            setProgress(event.current as number);
            setEmailStatuses((prev) => ({
              ...prev,
              [event.index as number]: "sent",
            }));
            break;
          case "email_failed":
            setProgress(event.current as number);
            setEmailStatuses((prev) => ({
              ...prev,
              [event.index as number]: "failed",
            }));
            break;
          case "waiting": {
            const secs = event.seconds as number;
            setWaitCountdown(secs);
            if (countdownRef.current) clearInterval(countdownRef.current);
            let remaining = secs;
            countdownRef.current = setInterval(() => {
              remaining--;
              setWaitCountdown(remaining);
              if (remaining <= 0 && countdownRef.current) {
                clearInterval(countdownRef.current);
                countdownRef.current = null;
              }
            }, 1000);
            break;
          }
          case "batch_complete":
            setSentCount(event.sent as number);
            setFailedCount(event.failed as number);
            break;
        }
      },
      () => {
        setSending(false);
        setCurrentEmail(null);
        setWaitCountdown(0);
        if (countdownRef.current) clearInterval(countdownRef.current);
        setPhase("results");
        getOutreachHistory().then(setHistory).catch(() => {});
      },
      (err) => {
        setError(err);
        setSending(false);
        if (countdownRef.current) clearInterval(countdownRef.current);
      }
    );
  };

  const toggleEmail = (index: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIndices(
      new Set(emails.filter((e) => !e.skip).map((e) => e.index))
    );
  };

  const selectNone = () => setSelectedIndices(new Set());

  const reset = () => {
    setPhase("input");
    setMarkdown("");
    setEmails([]);
    setSelectedIndices(new Set());
    setError("");
    setParseError("");
    setEmailStatuses({});
    setViewingBatch(null);
  };

  const loadBatch = async (id: string) => {
    try {
      const batch = await getOutreachBatch(id);
      setViewingBatch(batch);
    } catch {
      // ignore
    }
  };

  const progressPct = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Mass Outreach</h2>
          <p className="text-sm text-muted-foreground">
            Parse outreach emails from markdown and send in batch
          </p>
        </div>
        {phase !== "input" && (
          <Button variant="outline" size="sm" onClick={reset}>
            New Batch
          </Button>
        )}
      </div>

      {/* History */}
      {history.length > 0 && phase === "input" && (
        <Card>
          <CardHeader
            className="pb-2 cursor-pointer"
            onClick={() => setShowHistory(!showHistory)}
          >
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {showHistory ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Past Batches ({history.length})
            </CardTitle>
          </CardHeader>
          {showHistory && (
            <CardContent className="space-y-2">
              {history.map((b) => (
                <button
                  key={b.id}
                  onClick={() => loadBatch(b.id)}
                  className="w-full text-left px-3 py-2 rounded-md hover:bg-accent text-sm flex items-center justify-between"
                >
                  <span className="font-medium">{b.id}</span>
                  <span className="text-xs text-muted-foreground">
                    {b.sent} sent, {b.failed} failed &middot;{" "}
                    {new Date(b.created_at).toLocaleDateString()}
                  </span>
                </button>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* Viewing a past batch */}
      {viewingBatch && phase === "input" && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>Batch: {viewingBatch.id}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setViewingBatch(null)}
              >
                Close
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex gap-4 text-sm">
              <span>Account: {viewingBatch.account}</span>
              <Badge variant="default">{viewingBatch.sent} sent</Badge>
              {viewingBatch.failed > 0 && (
                <Badge variant="destructive">{viewingBatch.failed} failed</Badge>
              )}
            </div>
            <div className="space-y-1 mt-2">
              {viewingBatch.results.map((r) => (
                <div
                  key={r.index}
                  className="flex items-center gap-2 text-xs px-2 py-1 bg-muted/50 rounded"
                >
                  {r.status === "sent" ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <X className="h-3 w-3 text-red-500" />
                  )}
                  <span className="font-medium">{r.to}</span>
                  <span className="text-muted-foreground truncate flex-1">
                    {r.subject}
                  </span>
                  {r.error && (
                    <span className="text-red-500 truncate max-w-[200px]">
                      {r.error}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Phase: Input */}
      {phase === "input" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Outreach Markdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              placeholder={`Paste your outreach markdown here...\n\nExpected format:\n### #1 — email@example.com\n\n**Subject:** Your subject line\n\nEmail body here...\n\n---\n\n### #2 — next@example.com\n...`}
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
              className="w-full min-h-[250px] rounded-md border bg-background px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            />
            {parseError && (
              <p className="text-sm text-destructive">{parseError}</p>
            )}
            <Button
              onClick={handleParse}
              disabled={!markdown.trim()}
              className="w-full"
            >
              <Mail className="h-4 w-4 mr-2" />
              Parse Emails
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Phase: Preview */}
      {phase === "preview" && (
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold">{emails.length}</p>
                <p className="text-xs text-muted-foreground">Total Parsed</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold text-green-600">
                  {sendableEmails.length}
                </p>
                <p className="text-xs text-muted-foreground">Selected</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold text-muted-foreground">
                  {emails.filter((e) => e.skip).length}
                </p>
                <p className="text-xs text-muted-foreground">Skipped</p>
              </CardContent>
            </Card>
          </div>

          {/* Email list */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">
                  Emails ({emails.length})
                </CardTitle>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={selectAll}>
                    Select All
                  </Button>
                  <Button variant="ghost" size="sm" onClick={selectNone}>
                    Select None
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {emails.map((email) => (
                <div
                  key={email.index}
                  className={`flex items-start gap-3 p-3 rounded-md border ${
                    email.skip
                      ? "opacity-50 bg-muted/30"
                      : selectedIndices.has(email.index)
                      ? "bg-primary/5 border-primary/20"
                      : "bg-muted/20"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={
                      !email.skip && selectedIndices.has(email.index)
                    }
                    disabled={email.skip}
                    onChange={() => toggleEmail(email.index)}
                    className="mt-1 rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        #{email.index}
                      </span>
                      <span className="text-sm font-medium truncate">
                        {email.to}
                      </span>
                      {email.skip && (
                        <Badge variant="secondary" className="text-[10px]">
                          {email.skip_reason || "skip"}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Subject: {email.subject}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                      {email.body.slice(0, 150)}
                      {email.body.length > 150 ? "..." : ""}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Send controls */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Send Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    Sender Account
                  </label>
                  <select
                    value={selectedAccount}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  >
                    {accounts.map((a) => (
                      <option key={a.label} value={a.label}>
                        {a.label} ({a.email})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    Delay: {delay}s
                  </label>
                  <input
                    type="range"
                    min={10}
                    max={120}
                    step={5}
                    value={delay}
                    onChange={(e) => setDelay(Number(e.target.value))}
                    className="w-full mt-2"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    From Name (optional)
                  </label>
                  <input
                    type="text"
                    value={fromName}
                    onChange={(e) => setFromName(e.target.value)}
                    placeholder="e.g. Pranav"
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {!showConfirm ? (
                <Button
                  onClick={() => setShowConfirm(true)}
                  disabled={sendableEmails.length === 0}
                  className="w-full"
                >
                  <Send className="h-4 w-4 mr-2" />
                  Send {sendableEmails.length} Email
                  {sendableEmails.length !== 1 ? "s" : ""}
                </Button>
              ) : (
                <div className="flex items-center gap-3 p-3 rounded-md bg-amber-500/10 border border-amber-500/30">
                  <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      Send {sendableEmails.length} emails from{" "}
                      {accounts.find((a) => a.label === selectedAccount)?.email}?
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {delay}s delay between sends. This cannot be undone.
                    </p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowConfirm(false)}
                    >
                      Cancel
                    </Button>
                    <Button size="sm" onClick={handleSend}>
                      Confirm Send
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Phase: Sending */}
      {phase === "sending" && (
        <div className="space-y-4">
          {/* Progress bar */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">
                  Sending {progress}/{total}
                </span>
                <span className="text-sm text-muted-foreground">
                  {progressPct}%
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
                {sending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {currentEmail && <span>Sending to {currentEmail}...</span>}
                {waitCountdown > 0 && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    Waiting {waitCountdown}s before next send
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Email statuses */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Email Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {sendableEmails.map((email) => {
                const status = emailStatuses[email.index];
                return (
                  <div
                    key={email.index}
                    className="flex items-center gap-2 text-xs px-2 py-1.5 rounded bg-muted/30"
                  >
                    {status === "sending" && (
                      <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    )}
                    {status === "sent" && (
                      <Check className="h-3 w-3 text-green-500" />
                    )}
                    {status === "failed" && (
                      <X className="h-3 w-3 text-red-500" />
                    )}
                    {!status && (
                      <div className="h-3 w-3 rounded-full border border-muted-foreground/30" />
                    )}
                    <span className="font-medium">{email.to}</span>
                    <span className="text-muted-foreground truncate flex-1">
                      {email.subject}
                    </span>
                    {status && (
                      <Badge
                        variant={
                          status === "sent"
                            ? "default"
                            : status === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                        className="text-[10px]"
                      >
                        {status}
                      </Badge>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Phase: Results */}
      {phase === "results" && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold text-green-600">
                  {sentCount}
                </p>
                <p className="text-xs text-muted-foreground">Sent</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold text-red-600">
                  {failedCount}
                </p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-3 px-4">
                <p className="text-2xl font-semibold">{total}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </CardContent>
            </Card>
          </div>

          {batchId && (
            <p className="text-xs text-muted-foreground">
              Batch ID: {batchId}
            </p>
          )}

          {/* Full email list with statuses */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {sendableEmails.map((email) => {
                const status = emailStatuses[email.index];
                return (
                  <div
                    key={email.index}
                    className="flex items-center gap-2 text-xs px-2 py-1.5 rounded bg-muted/30"
                  >
                    {status === "sent" ? (
                      <Check className="h-3 w-3 text-green-500" />
                    ) : (
                      <X className="h-3 w-3 text-red-500" />
                    )}
                    <span className="font-medium">{email.to}</span>
                    <span className="text-muted-foreground truncate flex-1">
                      {email.subject}
                    </span>
                    <Badge
                      variant={status === "sent" ? "default" : "destructive"}
                      className="text-[10px]"
                    >
                      {status || "pending"}
                    </Badge>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
