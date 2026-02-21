"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  getResearchStatus,
  searchPosts,
  getUserTweets,
  getTrending,
  saveInsight,
  type XPost,
  type XTrend,
  type ResearchResult,
  type SaveInsightRequest,
} from "@/lib/api";
import {
  Search,
  TrendingUp,
  User,
  ExternalLink,
  Heart,
  Repeat2,
  MessageCircle,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Bookmark,
  Check,
  RefreshCw,
  Flame,
} from "lucide-react";

function PostCard({
  post,
  onSave,
  minFaves,
}: {
  post: XPost;
  onSave: (post: XPost, section: SaveInsightRequest["section"]) => void;
  minFaves?: number;
}) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async (section: SaveInsightRequest["section"]) => {
    setSaving(true);
    await onSave(post, section);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <Card>
      <CardContent className="pt-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-medium text-sm">
            {post.handle ? `@${post.handle.replace(/^@/, "")}` : "Unknown"}
          </span>
          <div className="flex items-center gap-1">
            {saved ? (
              <Badge variant="secondary" className="gap-1 text-xs">
                <Check className="h-3 w-3" /> Saved
              </Badge>
            ) : (
              <div className="flex items-center">
                <Button
                  variant="ghost"
                  size="icon-xs"
                  title="Save as post reference"
                  disabled={saving}
                  onClick={() => handleSave("saved_posts")}
                >
                  {saving ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Bookmark className="h-3 w-3" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  title="Save as copy pattern"
                  disabled={saving}
                  onClick={() => handleSave("copy_patterns")}
                >
                  <TrendingUp className="h-3 w-3" />
                </Button>
              </div>
            )}
            {post.url && (
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </div>
        <p className="text-sm whitespace-pre-wrap">{post.text}</p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-1">
          {post.likes + post.retweets + post.replies > 0 ? (
            <>
              <span className="flex items-center gap-1">
                <Heart className="h-3 w-3" /> {post.likes}
              </span>
              <span className="flex items-center gap-1">
                <Repeat2 className="h-3 w-3" /> {post.retweets}
              </span>
              <span className="flex items-center gap-1">
                <MessageCircle className="h-3 w-3" /> {post.replies}
              </span>
            </>
          ) : minFaves && minFaves > 0 ? (
            <span className="flex items-center gap-1">
              <Heart className="h-3 w-3" /> {minFaves}+
            </span>
          ) : null}
          {post.created_at && (
            <span className="ml-auto">{post.created_at}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

const COUNT_OPTIONS = [5, 10, 20, 50];
const MIN_FAVES_OPTIONS = [0, 50, 100, 500, 1000, 5000];

export default function ResearchPage() {
  const [birdAvailable, setBirdAvailable] = useState<boolean | null>(null);

  // Discover tab
  const [searchQuery, setSearchQuery] = useState("");
  const [searchCount, setSearchCount] = useState(10);
  const [minFaves, setMinFaves] = useState(0);
  const [searchResult, setSearchResult] = useState<ResearchResult | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [trends, setTrends] = useState<XTrend[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(false);

  // Account tab
  const [userHandle, setUserHandle] = useState("");
  const [userCount, setUserCount] = useState(10);
  const [userResult, setUserResult] = useState<ResearchResult | null>(null);
  const [userLoading, setUserLoading] = useState(false);

  // Raw output toggle
  const [showRaw, setShowRaw] = useState(false);

  // Active tab
  const [activeTab, setActiveTab] = useState("discover");

  // Ref to track if we need to auto-search after setting query from trend click
  const pendingSearchRef = useRef(false);

  useEffect(() => {
    getResearchStatus().then((s) => setBirdAvailable(s.available)).catch(() => setBirdAvailable(false));
  }, []);

  // Fetch trending on mount
  const fetchTrending = useCallback(async () => {
    setTrendsLoading(true);
    try {
      const res = await getTrending();
      setTrends(res.trends || []);
    } catch {
      setTrends([]);
    } finally {
      setTrendsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrending();
  }, [fetchTrending]);

  const handleSavePost = useCallback(
    async (post: XPost, section: SaveInsightRequest["section"]) => {
      try {
        await saveInsight({
          section,
          handle: post.handle,
          text: post.text,
          likes: post.likes,
          retweets: post.retweets,
        });
      } catch {
        // silently fail — the saved badge just won't show
      }
    },
    []
  );

  const handleSearch = useCallback(async (query?: string) => {
    const q = (query ?? searchQuery).trim();
    if (!q) return;
    setSearchLoading(true);
    try {
      const res = await searchPosts(q, searchCount, minFaves);
      setSearchResult(res);
    } catch {
      setSearchResult({ posts: [], trends: [], raw_output: "", error: "Request failed", min_faves: 0 });
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, searchCount, minFaves]);

  // When pendingSearchRef is set and searchQuery updates, trigger search
  useEffect(() => {
    if (pendingSearchRef.current && searchQuery) {
      pendingSearchRef.current = false;
      handleSearch(searchQuery);
    }
  }, [searchQuery, handleSearch]);

  const handleTrendClick = (trend: XTrend) => {
    pendingSearchRef.current = true;
    setSearchQuery(trend.name);
    setActiveTab("discover");
  };

  const handleUserLookup = useCallback(async () => {
    if (!userHandle.trim()) return;
    setUserLoading(true);
    try {
      const res = await getUserTweets(userHandle.trim(), userCount);
      setUserResult(res);
    } catch {
      setUserResult({ posts: [], trends: [], raw_output: "", error: "Request failed", min_faves: 0 });
    } finally {
      setUserLoading(false);
    }
  }, [userHandle, userCount]);

  const renderPosts = (posts: XPost[], resultMinFaves?: number) => (
    <div className="space-y-3">
      {posts.map((post, i) => (
        <PostCard key={i} post={post} onSave={handleSavePost} minFaves={resultMinFaves} />
      ))}
    </div>
  );

  const renderResult = (result: ResearchResult | null, loading: boolean) => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          Loading...
        </div>
      );
    }
    if (!result) return null;
    if (result.error) {
      return (
        <div className="flex items-center gap-2 text-destructive text-sm py-4">
          <AlertTriangle className="h-4 w-4" />
          {result.error}
        </div>
      );
    }
    if (result.posts.length === 0) {
      return (
        <p className="text-sm text-muted-foreground py-4">No results found.</p>
      );
    }
    return (
      <div className="space-y-4">
        {renderPosts(result.posts, result.min_faves)}
        {showRaw && result.raw_output && (
          <Card>
            <CardHeader>
              <CardTitle className="text-xs font-medium">Raw Output</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-y-auto bg-muted p-3 rounded">
                {result.raw_output}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const currentResult =
    activeTab === "discover" ? searchResult : userResult;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">X Research</h2>
        <div className="flex items-center gap-2">
          {birdAvailable === false && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              bird CLI not found
            </Badge>
          )}
          {currentResult?.raw_output && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRaw(!showRaw)}
              className="text-xs gap-1"
            >
              {showRaw ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              Raw output
            </Button>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="discover" className="gap-1.5">
            <Search className="h-3.5 w-3.5" />
            Discover
          </TabsTrigger>
          <TabsTrigger value="account" className="gap-1.5">
            <User className="h-3.5 w-3.5" />
            Account Lookup
          </TabsTrigger>
        </TabsList>

        <TabsContent value="discover" className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Search trending posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1"
            />
            <select
              value={searchCount}
              onChange={(e) => setSearchCount(Number(e.target.value))}
              className="h-9 rounded-md border bg-background px-3 text-sm"
            >
              {COUNT_OPTIONS.map((n) => (
                <option key={n} value={n}>{n} results</option>
              ))}
            </select>
            <select
              value={minFaves}
              onChange={(e) => setMinFaves(Number(e.target.value))}
              className="h-9 rounded-md border bg-background px-3 text-sm"
            >
              {MIN_FAVES_OPTIONS.map((n) => (
                <option key={n} value={n}>{n === 0 ? "Any likes" : `${n}+ likes`}</option>
              ))}
            </select>
            <Button onClick={() => handleSearch()} disabled={searchLoading || !searchQuery.trim()}>
              {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </Button>
          </div>

          {/* Trending badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <Flame className="h-4 w-4 text-orange-500 shrink-0" />
            {trendsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : trends.length > 0 ? (
              trends.map((trend, i) => (
                <Badge
                  key={i}
                  variant="secondary"
                  className="cursor-pointer hover:bg-accent transition-colors text-xs"
                  onClick={() => handleTrendClick(trend)}
                >
                  {trend.name}
                  {trend.tweet_count && (
                    <span className="ml-1 text-muted-foreground">{trend.tweet_count}</span>
                  )}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">No trends loaded</span>
            )}
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={fetchTrending}
              disabled={trendsLoading}
              title="Refresh trends"
              className="ml-auto"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${trendsLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>

          {renderResult(searchResult, searchLoading)}
        </TabsContent>

        <TabsContent value="account" className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="@handle"
              value={userHandle}
              onChange={(e) => setUserHandle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleUserLookup()}
              className="flex-1"
            />
            <select
              value={userCount}
              onChange={(e) => setUserCount(Number(e.target.value))}
              className="h-9 rounded-md border bg-background px-3 text-sm"
            >
              {COUNT_OPTIONS.map((n) => (
                <option key={n} value={n}>{n} results</option>
              ))}
            </select>
            <Button onClick={handleUserLookup} disabled={userLoading || !userHandle.trim()}>
              {userLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <User className="h-4 w-4" />}
              Lookup
            </Button>
          </div>
          {renderResult(userResult, userLoading)}
        </TabsContent>
      </Tabs>
    </div>
  );
}
