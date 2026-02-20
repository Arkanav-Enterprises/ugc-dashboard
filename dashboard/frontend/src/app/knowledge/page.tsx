"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getKnowledgeTree,
  getKnowledgeFile,
  saveKnowledgeFile,
  type FileNode,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  FolderOpen,
  FileText,
  ChevronRight,
  ChevronDown,
  Save,
  Pencil,
  X,
} from "lucide-react";

export default function KnowledgeBasePage() {
  const [tree, setTree] = useState<{
    skills: FileNode[];
    memory: FileNode[];
  } | null>(null);
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [selectedPath, setSelectedPath] = useState<string>("");
  const [content, setContent] = useState<string>("");
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getKnowledgeTree().then(setTree);
  }, []);

  const openFile = async (section: string, path: string) => {
    const data = await getKnowledgeFile(section, path);
    setSelectedSection(section);
    setSelectedPath(path);
    setContent(data.content);
    setEditing(false);
  };

  const handleSave = async () => {
    setSaving(true);
    await saveKnowledgeFile(selectedSection, selectedPath, editContent);
    setContent(editContent);
    setEditing(false);
    setSaving(false);
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-4rem)]">
      {/* File tree */}
      <Card className="w-64 shrink-0 flex flex-col">
        <CardHeader className="pb-2 border-b">
          <CardTitle className="text-sm font-medium">Files</CardTitle>
        </CardHeader>
        <ScrollArea className="flex-1 p-2">
          {tree && (
            <div className="space-y-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground px-2 mb-1">
                  SKILLS
                </p>
                <TreeView
                  nodes={tree.skills}
                  section="skills"
                  onSelect={openFile}
                  selectedPath={selectedSection === "skills" ? selectedPath : ""}
                />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground px-2 mb-1">
                  MEMORY
                </p>
                <TreeView
                  nodes={tree.memory}
                  section="memory"
                  onSelect={openFile}
                  selectedPath={selectedSection === "memory" ? selectedPath : ""}
                />
              </div>
            </div>
          )}
        </ScrollArea>
      </Card>

      {/* Content viewer/editor */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-2 border-b flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium">
            {selectedPath || "Select a file"}
          </CardTitle>
          {selectedPath && (
            <div className="flex gap-1">
              {editing ? (
                <>
                  <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                    <X className="h-3 w-3 mr-1" /> Cancel
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={saving}>
                    <Save className="h-3 w-3 mr-1" /> {saving ? "Saving..." : "Save"}
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditContent(content);
                    setEditing(true);
                  }}
                >
                  <Pencil className="h-3 w-3 mr-1" /> Edit
                </Button>
              )}
            </div>
          )}
        </CardHeader>
        <ScrollArea className="flex-1 p-4">
          {!selectedPath ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              Select a file from the tree to view its contents
            </p>
          ) : editing ? (
            <Textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="min-h-[500px] font-mono text-sm resize-none"
            />
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </ScrollArea>
      </Card>
    </div>
  );
}

function TreeView({
  nodes,
  section,
  onSelect,
  selectedPath,
}: {
  nodes: FileNode[];
  section: string;
  onSelect: (section: string, path: string) => void;
  selectedPath: string;
}) {
  return (
    <div className="space-y-0.5">
      {nodes.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          section={section}
          onSelect={onSelect}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
}

function TreeNode({
  node,
  section,
  onSelect,
  selectedPath,
  depth = 0,
}: {
  node: FileNode;
  section: string;
  onSelect: (section: string, path: string) => void;
  selectedPath: string;
  depth?: number;
}) {
  const [open, setOpen] = useState(true);
  const isSelected = node.path === selectedPath;

  if (node.is_dir) {
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1 px-2 py-1 text-xs w-full hover:bg-muted rounded text-left"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {open ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <FolderOpen className="h-3 w-3 text-muted-foreground" />
          <span>{node.name}</span>
        </button>
        {open &&
          node.children?.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              section={section}
              onSelect={onSelect}
              selectedPath={selectedPath}
              depth={depth + 1}
            />
          ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(section, node.path)}
      className={`flex items-center gap-1 px-2 py-1 text-xs w-full rounded text-left ${
        isSelected ? "bg-primary text-primary-foreground" : "hover:bg-muted"
      }`}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <FileText className="h-3 w-3 shrink-0" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}
