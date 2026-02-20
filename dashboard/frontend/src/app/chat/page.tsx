"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getContextFiles,
  triggerPipelineRun,
  WS_URL,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Loader2, Play, Eye, FileText, Zap } from "lucide-react";

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
  const wsRef = useRef<WebSocket | null>(null);
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

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return wsRef.current;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    return ws;
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || streaming) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const ws = connectWs();
    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const onOpen = () => {
      ws.send(
        JSON.stringify({
          message: userMsg.content,
          history,
          skill_files: selectedSkills,
          memory_files: selectedMemory,
        })
      );
    };

    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const onMessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      if (data.type === "chunk") {
        assistantContent += data.content;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: assistantContent,
          };
          return next;
        });
      } else if (data.type === "done" || data.type === "error") {
        setStreaming(false);
        ws.removeEventListener("message", onMessage);
      }
    };

    ws.addEventListener("message", onMessage);

    if (ws.readyState === WebSocket.OPEN) {
      onOpen();
    } else {
      ws.addEventListener("open", onOpen, { once: true });
    }
  };

  const handleAction = async (
    action: "generate" | "dry-run" | "caption-only" | "run-all"
  ) => {
    const configs: Record<string, { persona: string; dry_run?: boolean; skip_gen?: boolean }> = {
      generate: { persona: "sanya" },
      "dry-run": { persona: "sanya", dry_run: true },
      "caption-only": { persona: "sanya", dry_run: true, skip_gen: true },
      "run-all": { persona: "all" },
    };
    const req = configs[action];
    const result = await triggerPipelineRun({
      ...req,
      no_upload: true,
    });
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `Pipeline run started: **${result.id}** (${result.persona}, ${result.status})`,
      },
    ]);
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

  return (
    <div className="flex gap-4 h-[calc(100vh-4rem)]">
      {/* Left panel — actions + context */}
      <div className="w-64 shrink-0 space-y-4 overflow-auto">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              size="sm"
              className="w-full justify-start"
              onClick={() => handleAction("generate")}
            >
              <Play className="h-3 w-3 mr-2" /> Generate Reel
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleAction("dry-run")}
            >
              <Eye className="h-3 w-3 mr-2" /> Dry Run
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleAction("caption-only")}
            >
              <FileText className="h-3 w-3 mr-2" /> Caption Only
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="w-full justify-start"
              onClick={() => handleAction("run-all")}
            >
              <Zap className="h-3 w-3 mr-2" /> Run All
            </Button>
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
