"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Film,
  Activity,
  Video,
  Calendar,
  MessageSquare,
  BookOpen,
  Image,
  FileText,
  TrendingUp,
  Search,
  Mail,
  BarChart3,
  DollarSign,
  Scissors,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./theme-toggle";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/content", label: "Content Gallery", icon: Film },
  { href: "/pipeline", label: "Pipeline Monitor", icon: Activity },
  { href: "/generate", label: "Generate Content", icon: Video },
  { href: "/stitcher", label: "Video Stitcher", icon: Scissors },
  { href: "/schedule", label: "Schedule", icon: Calendar },
  { href: "/research", label: "Trend Research", icon: TrendingUp },
  { href: "/scout", label: "Opportunity Scout", icon: Search },
  { href: "/outreach", label: "Outreach", icon: Mail },
  { href: "/revenue", label: "Revenue", icon: DollarSign },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/chat", label: "Agent Chat", icon: MessageSquare },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/assets", label: "Asset Manager", icon: Image },
  { href: "/logs", label: "Logs", icon: FileText },
];

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      <div className="px-4 pt-6 pb-4">
        <h1 className="font-bold text-lg tracking-tight font-[family-name:var(--font-display)]">OpenClaw</h1>
        <p className="text-xs text-muted-foreground mt-0.5">Dashboard</p>
      </div>
      <nav className="flex-1 px-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                active
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-4 text-xs text-muted-foreground flex items-center justify-between">
        <span>7 accounts</span>
        <ThemeToggle />
      </div>
    </>
  );
}

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setOpen(true)}
        className="fixed top-4 left-4 z-50 p-2 rounded-md bg-background border md:hidden"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-56 flex flex-col bg-background border-r transition-transform duration-200 md:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <button
          onClick={() => setOpen(false)}
          className="absolute top-4 right-3 p-1 text-muted-foreground hover:text-foreground"
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
        <NavContent onNavigate={() => setOpen(false)} />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 flex-col shrink-0">
        <NavContent />
      </aside>
    </>
  );
}
