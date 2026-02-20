"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  getContextFiles,
  triggerPipelineRun,
  getPipelineRunStatus,
  streamChat,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Loader2, Play, Eye, FileText, Zap, AlertTriangle, CheckCircle2 } from "lucide-react";

type Action = "generate" | "dry-run" | "caption-only" | "run-all";

const ACTION_META: Record<Action, {
  label: string;
  cost: string | null;
  description: string;
  needsConfirm: boolean;
}> = {
  generate: {
    label: "Generate Reel",
    cost: "~$0.61",
    description: "This will generate a video clip via Replicate (Veo 3.1) for Sanya and assemble a full reel.",
    needsConfirm: true,
  },
  "run-all": {
    label: "Run All Personas",
    cost: "~$1.83",
    description: "This will generate video clips for all 3 personas (Sanya, Sophie, Aliyah) — 3 Replicate calls.",
    needsConfirm: true,
  },
  "dry-run": {
    label: "Dry Run",
    cost: null,
    description: "Text generation only, no video.",
    needsConfirm: false,
  },
  "caption-only": {
    label: "Caption Only",
    cost: null,
    description: "Generate caption text only.",
    needsConfirm: false,
  },
};

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [skillFiles, setSkillFiles] = useState<string[]>([]);
  const [memoryFiles, setMemoryFiles] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([
    "content-strategy.md",
    "manifest-lock-knowledge.md",
    "tiktok-slideshows.md",
  ]);
  const [selectedMemory, setSelectedMemory] = useState<string[]>([
    "post-performance.md",
    "failure-log.md",
  ]);
  const [confirmAction, setConfirmAction] = useState<Action | null>(null);
  const [runningAction, setRunningAction] = useState<Action | null>(null);
  const [lastResult, setLastResult] = useState<{ action: Action; success: boolean } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getContextFiles().then((f) => {
      setSkillFiles(f.skills);
      setMemoryFiles(f.memory);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Clear success indicator after 3 seconds
  useEffect(() => {
    if (!lastResult) return;
    const t = setTimeout(() => setLastResult(null), 3000);
    return () => clearTimeout(t);
  }, [lastResult]);

  const sendMessage = async () => {
    if (!input.trim() || streaming) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    await streamChat(
      userMsg.content,
      history,
      selectedSkills,
      selectedMemory,
      (chunk) => {
        assistantContent += chunk;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: assistantContent,
          };
          return next;
        });
      },
      () => setStreaming(false),
      (err) => {
        assistantContent += `\n\nError: ${err}`;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: assistantContent,
          };
          return next;
        });
        setStreaming(false);
      }
    );
  };

  const executeAction = async (action: Action) => {
    const configs: Record<Action, { persona: string; dry_run?: boolean; skip_gen?: boolean }> = {
      generate: { persona: "sanya" },
      "dry-run": { persona: "sanya", dry_run: true },
      "caption-only": { persona: "sanya", dry_run: true, skip_gen: true },
      "run-all": { persona: "all" },
    };

    setRunningAction(action);
    setConfirmAction(null);

    // Add a placeholder message that we'll update with progress
    const msgIndex = messages.length;
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `Running **${ACTION_META[action].label}**...`,
      },
    ]);

    try {
      const req = configs[action];
      const result = await triggerPipelineRun({ ...req, no_upload: true });
      const runId = result.id;

      // Poll for completion
      let attempts = 0;
      const maxAttempts = 120; // 2 minutes max
      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 2000));
        attempts++;

        try {
          const status = await getPipelineRunStatus(runId);

          if (status.status === "completed" || status.status === "failed") {
            const output = status.output?.trim();
            const success = status.status === "completed";

            setMessages((prev) => {
              const next = [...prev];
              next[msgIndex] = {
                role: "assistant",
                content: success
                  ? `**${ACTION_META[action].label}** completed:\n\n\`\`\`\n${output || "No output"}\n\`\`\``
                  : `**${ACTION_META[action].label}** failed:\n\n\`\`\`\n${output || "No output"}\n\`\`\``,
              };
              return next;
            });
            setLastResult({ action, success });
            setRunningAction(null);
            return;
          }

          // Update with latest output while still running
          if (status.output) {
            setMessages((prev) => {
              const next = [...prev];
              next[msgIndex] = {
                role: "assistant",
                content: `Running **${ACTION_META[action].label}**...\n\n\`\`\`\n${status.output.slice(-500)}\n\`\`\``,
              };
              return next;
            });
          }
        } catch {
          // Polling error — keep trying
        }
      }

      // Timed out
      setMessages((prev) => {
        const next = [...prev];
        next[msgIndex] = {
          role: "assistant",
          content: `**${ACTION_META[action].label}** is still running (run ID: ${runId}). Check the Pipeline Monitor for results.`,
        };
        return next;
      });
      setLastResult({ action, success: true });
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[msgIndex] = {
          role: "assistant",
          content: `Failed to start **${ACTION_META[action].label}**. Check that the backend is running.`,
        };
        return next;
      });
      setLastResult({ action, success: false });
    } finally {
      setRunningAction(null);
    }
  };

  const handleAction = (action: Action) => {
    if (runningAction) return;
    if (ACTION_META[action].needsConfirm) {
      setConfirmAction(action);
    } else {
      executeAction(action);
    }
  };

  const toggleFile = (
    file: string,
    list: string[],
    setter: (v: string[]) => void
  ) => {
    setter(
      list.includes(file) ? list.filter((f) => f !== file) : [...list, file]
    );
  };

  const actionButton = (action: Action, icon: React.ReactNode, variant: "default" | "outline" = "outline") => {
    const meta = ACTION_META[action];
    const isRunning = runningAction === action;
    const justSucceeded = lastResult?.action === action && lastResult.success;

    return (
      <Button
        size="sm"
        variant={variant}
        className="w-full justify-start"
        disabled={!!runningAction}
        onClick={() => handleAction(action)}
      >
        {isRunning ? (
          <Loader2 className="h-3 w-3 mr-2 animate-spin" />
        ) : justSucceeded ? (
          <CheckCircle2 className="h-3 w-3 mr-2 text-green-500" />
        ) : (
          <span className="mr-2">{icon}</span>
        )}
        {isRunning ? "Running..." : meta.label}
        {meta.cost && (
          <span className="ml-auto text-xs text-muted-foreground">{meta.cost}</span>
        )}
      </Button>
    );
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-4rem)]">
      {/* Confirmation dialog for costly actions */}
      <Dialog open={!!confirmAction} onOpenChange={(open) => !open && setConfirmAction(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Confirm: {confirmAction && ACTION_META[confirmAction].label}
            </DialogTitle>
            <DialogDescription>
              {confirmAction && ACTION_META[confirmAction].description}
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-3">
            <p className="text-sm font-medium">
              Estimated cost: {confirmAction && ACTION_META[confirmAction].cost}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              This will use Replicate API credits. The cost is charged immediately.
            </p>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              variant="destructive"
              onClick={() => confirmAction && executeAction(confirmAction)}
            >
              Yes, run it
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Left panel — actions + context */}
      <div className="w-64 shrink-0 space-y-4 overflow-auto">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {actionButton("generate", <Play className="h-3 w-3" />, "default")}
            {actionButton("dry-run", <Eye className="h-3 w-3" />)}
            {actionButton("caption-only", <FileText className="h-3 w-3" />)}
            {actionButton("run-all", <Zap className="h-3 w-3" />)}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Skill Context
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {skillFiles.map((f) => (
              <label key={f} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={selectedSkills.includes(f)}
                  onChange={() =>
                    toggleFile(f, selectedSkills, setSelectedSkills)
                  }
                  className="rounded"
                />
                <span className="truncate">{f}</span>
              </label>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Memory</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {memoryFiles.map((f) => (
              <label key={f} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={selectedMemory.includes(f)}
                  onChange={() =>
                    toggleFile(f, selectedMemory, setSelectedMemory)
                  }
                  className="rounded"
                />
                <span className="truncate">{f}</span>
              </label>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Right panel — chat */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-2 border-b">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            Agent Chat
            <Badge variant="secondary" className="text-xs">
              {selectedSkills.length + selectedMemory.length} files loaded
            </Badge>
          </CardTitle>
        </CardHeader>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                Start a conversation with the OpenClaw agent. It has access to
                your skill files and memory for context-aware responses.
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
                        p: ({ children }) => (
                          <p className="mb-2 last:mb-0">{children}</p>
                        ),
                        code: ({ children }) => (
                          <code className="bg-background/50 px-1 rounded text-xs">
                            {children}
                          </code>
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
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ask about content strategy, generate hooks, or analyze performance..."
            className="min-h-[44px] max-h-32 resize-none"
            rows={1}
          />
          <Button
            onClick={sendMessage}
            disabled={streaming || !input.trim()}
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
    </div>
  );
}
