"""X/Twitter research endpoints — wraps the bird CLI."""

from fastapi import APIRouter

from models import ResearchRequest, SaveInsightRequest
from services.bird_runner import check_bird_available, search_posts, get_user_tweets, get_trending, save_insight

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/status")
def status():
    """Check if the bird CLI is available."""
    return check_bird_available()


@router.post("/search")
def search(req: ResearchRequest):
    """Search X posts by keyword."""
    return search_posts(req.query, req.count)


@router.post("/user-tweets")
def user_tweets(req: ResearchRequest):
    """Get posts from a specific account."""
    return get_user_tweets(req.handle, req.count)


@router.get("/trending")
def trending():
    """Get current trending topics."""
    return get_trending()


@router.post("/save-insight")
def save(req: SaveInsightRequest):
    """Save a post or trend to memory/x-trends.md."""
    return save_insight(req)
