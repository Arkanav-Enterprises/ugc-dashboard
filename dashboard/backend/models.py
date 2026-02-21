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


class PipelineRunRequest(BaseModel):
    persona: str = "sanya"
    video_type: Optional[str] = None
    dry_run: bool = False
    no_upload: bool = False
    skip_gen: bool = False


class PipelineRunStatus(BaseModel):
    id: str
    status: str  # running, completed, failed
    persona: str
    started_at: str
    output: str = ""


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
    today_video_type: str
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
