"use client";

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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./theme-toggle";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/content", label: "Content Gallery", icon: Film },
  { href: "/pipeline", label: "Pipeline Monitor", icon: Activity },
  { href: "/generate", label: "Generate Content", icon: Video },
  { href: "/schedule", label: "Schedule", icon: Calendar },
  { href: "/research", label: "Trend Research", icon: TrendingUp },
  { href: "/scout", label: "Opportunity Scout", icon: Search },
  { href: "/outreach", label: "Outreach", icon: Mail },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/chat", label: "Agent Chat", icon: MessageSquare },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/assets", label: "Asset Manager", icon: Image },
  { href: "/logs", label: "Logs", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r bg-card flex flex-col shrink-0">
      <div className="p-4 border-b">
        <h1 className="font-bold text-lg tracking-tight font-[family-name:var(--font-display)]">OpenClaw</h1>
        <p className="text-xs text-muted-foreground">Dashboard</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t text-xs text-muted-foreground flex items-center justify-between">
        <span>7 accounts &middot; local</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
