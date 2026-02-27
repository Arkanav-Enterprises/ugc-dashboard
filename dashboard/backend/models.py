"""Pydantic models for API responses."""

from pydantic import BaseModel
from typing import Optional


class PipelineRun(BaseModel):
    timestamp: str
    persona: str
    video_type: Optional[str] = None
    hook_text: str
    reaction_text: str
    caption: str = ""
    content_angle: str = ""
    reel_path: Optional[str] = None
    cost_usd: Optional[float] = None


class OverviewStats(BaseModel):
    today_runs: int
    today_cost: float
    daily_cap: float
    total_reels: int
    total_spend: float


class DailySpend(BaseModel):
    date: str
    amount: float


class PersonaStats(BaseModel):
    persona: str
    color: str
    last_run: Optional[str] = None
    total_runs: int
    hook_clips: int
    reaction_clips: int


class SkillFile(BaseModel):
    path: str
    name: str
    is_dir: bool
    children: Optional[list["SkillFile"]] = None


class FileContent(BaseModel):
    path: str
    content: str


class AssetInfo(BaseModel):
    name: str
    path: str
    persona: Optional[str] = None
    type: Optional[str] = None


class PersonaAppInfo(BaseModel):
    name: str
    slug: str


class PersonaConfig(BaseModel):
    persona: str
    color: str
    apps: list[PersonaAppInfo]
    video_types: list[str]


class PipelineRunRequest(BaseModel):
    account: str = "aliyah.manifests"
    dry_run: bool = False
    no_upload: bool = False
    no_reaction: bool = False
    idea_only: bool = False


class PipelineRunStatus(BaseModel):
    id: str
    status: str  # running, completed, failed
    persona: str
    app: Optional[str] = None
    started_at: str
    output: str = ""


class LifestyleReelRequest(BaseModel):
    dry_run: bool = False
    no_upload: bool = False
    scene_1_text: Optional[str] = None
    scene_2_text: Optional[str] = None
    scene_3_text: Optional[str] = None
    scene_1_image: Optional[str] = None
    scene_2_image: Optional[str] = None


class AutoJournalReelRequest(BaseModel):
    dry_run: bool = False
    no_upload: bool = False
    style: Optional[str] = None
    category: Optional[str] = None
    hook_text: Optional[str] = None
    payoff_text: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


# ─── Schedule models ─────────────────────────────────

class ScheduleSlot(BaseModel):
    type: str  # "video" or "text"
    persona: Optional[str] = None
    account: Optional[str] = None
    time_utc: str
    time_ist: str
    video_type: Optional[str] = None
    enabled: bool
    last_run: Optional[str] = None
    last_status: Optional[str] = None


class CronHistoryEntry(BaseModel):
    timestamp: str
    status: str  # "ok" or "failed"
    message: str


class ScheduleState(BaseModel):
    video_pipeline_enabled: bool
    text_pipeline_enabled: bool
    video_time_utc: str
    video_time_ist: str
    slots: list[ScheduleSlot]
    cron_history: list[CronHistoryEntry]


class ScheduleUpdateRequest(BaseModel):
    video_pipeline_enabled: Optional[bool] = None
    text_pipeline_enabled: Optional[bool] = None
    video_personas: Optional[dict[str, dict]] = None
    text_accounts: Optional[dict[str, dict]] = None


# ─── YouTube Research models ────────────────────────

class YTChannelScanRequest(BaseModel):
    channel_url: str
    max_videos: int = 20


class YTVideoInfo(BaseModel):
    video_id: str
    title: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None


class YTChannelScanResult(BaseModel):
    channel_name: str
    channel_url: str
    videos: list[YTVideoInfo]


class YTAnalyzeRequest(BaseModel):
    channel_name: str
    channel_url: str
    video_ids: list[str]
    video_titles: dict[str, str] = {}


class YTVideoSummary(BaseModel):
    video_id: str
    title: str
    has_transcript: bool
    summary: Optional[str] = None
    key_points: list[str] = []
    error: Optional[str] = None


class YTResearchResult(BaseModel):
    id: str
    channel_name: str
    channel_url: str
    created_at: str
    video_summaries: list[YTVideoSummary]
    cross_analysis: str = ""


class YTResearchListItem(BaseModel):
    id: str
    channel_name: str
    created_at: str
    video_count: int
    source: str = "youtube"


# ─── Reddit Research models ────────────────────────

class RedditSearchRequest(BaseModel):
    query: str
    subreddits: list[str] = []
    time_filter: str = "week"
    limit: int = 25


class RedditThread(BaseModel):
    thread_id: str
    title: str
    subreddit: str
    score: int
    num_comments: int
    permalink: str
    created_utc: float
    selftext_preview: str = ""
    url: str = ""


class RedditSearchResult(BaseModel):
    query: str
    threads: list[RedditThread]


class RedditAnalyzeRequest(BaseModel):
    query: str
    threads: list[dict]


class RedditThreadSummary(BaseModel):
    thread_id: str
    title: str
    subreddit: str
    summary: Optional[str] = None
    key_points: list[str] = []
    sentiment: Optional[str] = None
    error: Optional[str] = None


# ─── Opportunity Scout models ─────────────────────

class ScoutRunRequest(BaseModel):
    seeds: list[str]
    skip_reviews: bool = False
    skip_reddit: bool = False


class ScoutExpandSeedsRequest(BaseModel):
    seeds: list[str]


class ScoutApp(BaseModel):
    track_id: int
    name: str
    developer: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    genre: str = ""
    icon_url: str = ""


class ScoutResultListItem(BaseModel):
    id: str
    seeds: list[str]
    app_count: int
    created_at: str


# ─── Outreach models ──────────────────────────────

class OutreachEmail(BaseModel):
    index: int
    to: str
    subject: str
    body: str
    skip: bool = False
    skip_reason: Optional[str] = None

class OutreachParseRequest(BaseModel):
    markdown: str


# ─── Analytics models ────────────────────────────────

class FunnelStep(BaseModel):
    name: str
    count: int
    conversion_rate: float
    drop_off_rate: float


class FunnelResult(BaseModel):
    steps: list[FunnelStep]
    overall_conversion: float


class TrendSeries(BaseModel):
    event: str
    labels: list[str]
    data: list[float]
    count: int


class AnalyticsSummary(BaseModel):
    app: str
    funnel: FunnelResult
    trends: list[TrendSeries]


class AnalyticsAskRequest(BaseModel):
    message: str
    history: list[dict] = []
    app: Optional[str] = None

class OutreachSendRequest(BaseModel):
    emails: list[OutreachEmail]
    account_label: str
    delay_seconds: int = 45
    from_name: Optional[str] = None
