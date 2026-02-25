"""PostHog analytics client — funnel + trend queries."""

import httpx

from config import POSTHOG_HOST, POSTHOG_PROJECTS

# Per-app default funnel steps from ANALYTICS.md
DEFAULT_FUNNELS: dict[str, list[str]] = {
    "manifest-lock": [
        "onboarding_started",
        "onboarding_name_entered",
        "onboarding_goal_selected",
        "onboarding_manifestation_created",
        "onboarding_read_aloud_completed",
        "onboarding_completed",
    ],
    "journal-lock": [
        "onboarding_started",
        "onboarding_journaling_reasons_selected",
        "onboarding_manifestation_created",
        "onboarding_apps_selected",
        "onboarding_trial_started",
        "onboarding_completed",
    ],
}

# Retention events (shared)
RETENTION_EVENTS = ["day_1_retained", "day_7_retained", "day_14_retained", "day_30_retained"]

# Core feature events per app
FEATURE_EVENTS: dict[str, list[str]] = {
    "manifest-lock": ["practice_completed", "manifestation_created"],
    "journal-lock": ["journal_practice_completed", "journal_entry_created"],
}


def _project_config(app: str) -> dict:
    if app not in POSTHOG_PROJECTS:
        raise ValueError(f"Unknown app: {app}. Valid: {list(POSTHOG_PROJECTS.keys())}")
    return POSTHOG_PROJECTS[app]


def _headers(app: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_project_config(app)['api_key']}"}


def _has_key(app: str) -> bool:
    return bool(_project_config(app).get("api_key"))


async def get_funnel(app: str, steps: list[str] | None = None, date_from: str = "-30d") -> dict:
    """Query PostHog funnel insight for an app."""
    if not _has_key(app):
        return {"error": f"POSTHOG_API_KEY_{app.split('-')[0].upper()} not configured", "steps": [], "overall_conversion": 0}

    pid = _project_config(app)["id"]
    funnel_steps = steps or DEFAULT_FUNNELS.get(app, [])
    if not funnel_steps:
        return {"steps": [], "overall_conversion": 0}

    events = [{"id": name, "type": "events", "order": i} for i, name in enumerate(funnel_steps)]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{POSTHOG_HOST}/api/projects/{pid}/insights/funnel/",
            headers=_headers(app),
            json={
                "events": events,
                "date_from": date_from,
                "funnel_viz_type": "steps",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Parse PostHog funnel response
    results = data.get("result", [])
    if not results:
        return {"steps": [{"name": s, "count": 0, "conversion_rate": 0, "drop_off_rate": 0} for s in funnel_steps], "overall_conversion": 0}

    parsed_steps = []
    first_count = 0
    last_count = 0
    for i, step_data in enumerate(results):
        count = step_data.get("count", 0)
        if i == 0:
            first_count = count
            conv_rate = 100.0
        else:
            conv_rate = (count / first_count * 100) if first_count > 0 else 0

        prev_count = results[i - 1].get("count", 0) if i > 0 else count
        drop_off = ((prev_count - count) / prev_count * 100) if prev_count > 0 else 0

        parsed_steps.append({
            "name": funnel_steps[i] if i < len(funnel_steps) else step_data.get("name", f"Step {i+1}"),
            "count": count,
            "conversion_rate": round(conv_rate, 1),
            "drop_off_rate": round(drop_off, 1),
        })
        last_count = count

    overall = (last_count / first_count * 100) if first_count > 0 else 0

    return {
        "steps": parsed_steps,
        "overall_conversion": round(overall, 1),
    }


async def get_trend(app: str, events: list[str] | None = None, date_from: str = "-30d", interval: str = "day") -> list[dict]:
    """Query PostHog trend insight for an app."""
    if not _has_key(app):
        return []

    pid = _project_config(app)["id"]
    event_list = events or FEATURE_EVENTS.get(app, []) + RETENTION_EVENTS

    trend_events = [{"id": name, "type": "events", "math": "dau"} for name in event_list]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{POSTHOG_HOST}/api/projects/{pid}/insights/trend/",
            headers=_headers(app),
            json={
                "events": trend_events,
                "date_from": date_from,
                "interval": interval,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    series = []
    for result in data.get("result", []):
        series.append({
            "event": result.get("label", result.get("action", {}).get("id", "unknown")),
            "labels": result.get("labels", []),
            "data": result.get("data", []),
            "count": result.get("count", 0),
        })

    return series


async def get_analytics_summary(app: str) -> dict:
    """Get combined funnel + trend summary for one app."""
    funnel = await get_funnel(app)
    trends = await get_trend(app)
    return {"app": app, "funnel": funnel, "trends": trends}


async def get_combined_summary() -> dict:
    """Get analytics summary for both apps."""
    ml = await get_analytics_summary("manifest-lock")
    jl = await get_analytics_summary("journal-lock")
    return {"manifest_lock": ml, "journal_lock": jl}


async def format_metrics_for_ai() -> str:
    """Format PostHog data as text block for Claude system prompt."""
    if not any(_has_key(app) for app in POSTHOG_PROJECTS):
        return "[PostHog analytics unavailable — no API keys configured]"

    try:
        combined = await get_combined_summary()
    except Exception as e:
        return f"[PostHog analytics error: {e}]"

    lines = ["## Live PostHog Analytics (last 30 days)\n"]

    for key, label in [("manifest_lock", "ManifestLock"), ("journal_lock", "JournalLock")]:
        app_data = combined[key]
        funnel = app_data["funnel"]

        if funnel.get("error"):
            lines.append(f"### {label}\n{funnel['error']}\n")
            continue

        lines.append(f"### {label}")
        lines.append(f"Overall onboarding conversion: {funnel.get('overall_conversion', 0)}%")

        if funnel.get("steps"):
            lines.append("Funnel steps:")
            for step in funnel["steps"]:
                lines.append(f"  - {step['name']}: {step['count']} users ({step['conversion_rate']}% of start, {step['drop_off_rate']}% drop-off)")

            # Find biggest drop-off
            max_drop = max(funnel["steps"], key=lambda s: s["drop_off_rate"])
            if max_drop["drop_off_rate"] > 0:
                lines.append(f"Biggest drop-off: {max_drop['name']} ({max_drop['drop_off_rate']}%)")

        trends = app_data.get("trends", [])
        if trends:
            lines.append("Trends (DAU):")
            for t in trends:
                avg = sum(t["data"]) / len(t["data"]) if t["data"] else 0
                lines.append(f"  - {t['event']}: avg {avg:.1f}/day, total {t['count']}")

        lines.append("")

    return "\n".join(lines)
