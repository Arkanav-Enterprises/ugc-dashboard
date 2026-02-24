"""Mass outreach email service — parse markdown, send batch via SMTP."""

import asyncio
import json
import re
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import AsyncGenerator

from config import (
    OUTREACH_ACCOUNTS,
    OUTREACH_DEFAULT_HOST,
    OUTREACH_DEFAULT_PORT,
    OUTREACH_OUTPUT_DIR,
)


# ─── Account helpers ──────────────────────────────


def list_accounts() -> list[dict]:
    """Return accounts with passwords redacted."""
    return [
        {"label": a["label"], "email": a["email"]}
        for a in OUTREACH_ACCOUNTS
    ]


def get_account(label: str) -> dict | None:
    """Lookup a full account (with app_password) by label."""
    for a in OUTREACH_ACCOUNTS:
        if a["label"] == label:
            return a
    return None


# ─── Markdown parser ─────────────────────────────


def parse_outreach_markdown(md: str) -> list[dict]:
    """Parse the outreach markdown format into structured emails.

    Expected format per entry (separated by ---):
        ### #N — email@domain.com (optional flags)
        **Subject:** The subject line
        Body text here...
    """
    entries = re.split(r"\n---+\n", md.strip())
    emails = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Match header: ### #N — email@domain
        header_match = re.search(
            r"###\s*#?(\d+)\s*[—–-]\s*(\S+@\S+)", entry
        )
        if not header_match:
            continue

        index = int(header_match.group(1))
        to_email = header_match.group(2).strip().rstrip(")")

        # Check for skip flags
        skip = False
        skip_reason = None
        header_line = entry.split("\n")[0]
        if "(CONTACT FORM)" in header_line.upper():
            skip = True
            skip_reason = "contact form"
        elif "(ADAPTED FOR DM)" in header_line.upper():
            skip = True
            skip_reason = "adapted for DM"

        # Extract subject
        subject_match = re.search(
            r"\*\*Subject:\*\*\s*(.+?)(?:\n|$)", entry
        )
        subject = subject_match.group(1).strip() if subject_match else ""

        # Extract body — everything after the subject line
        body = ""
        if subject_match:
            after_subject = entry[subject_match.end():]
            body = after_subject.strip()
        else:
            # Fallback: everything after the header line
            lines = entry.split("\n", 1)
            if len(lines) > 1:
                body = lines[1].strip()

        emails.append({
            "index": index,
            "to": to_email,
            "subject": subject,
            "body": body,
            "skip": skip,
            "skip_reason": skip_reason,
        })

    return emails


# ─── Single email send ───────────────────────────


def send_one_email(
    account: dict,
    to: str,
    subject: str,
    body: str,
    from_name: str | None = None,
) -> None:
    """Send a single email via SMTP + STARTTLS."""
    msg = MIMEMultipart("alternative")
    from_addr = account["email"]
    if from_name:
        msg["From"] = f"{from_name} <{from_addr}>"
    else:
        msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject

    # Send as plain text
    msg.attach(MIMEText(body, "plain"))

    # Per-account host/port override, falls back to global defaults
    host = account.get("smtp_host", OUTREACH_DEFAULT_HOST)
    port = int(account.get("smtp_port", OUTREACH_DEFAULT_PORT))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(from_addr, account["app_password"])
        server.sendmail(from_addr, to, msg.as_string())


# ─── Batch send (SSE generator) ──────────────────


async def send_batch(
    emails: list[dict],
    account_label: str,
    delay_seconds: int = 45,
    from_name: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE events for batch email sending."""
    account = get_account(account_label)
    if not account:
        yield {"type": "error", "content": f"Unknown account: {account_label}"}
        return

    sendable = [e for e in emails if not e.get("skip")]
    total = len(sendable)

    batch_id = f"outreach-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    yield {
        "type": "batch_start",
        "batch_id": batch_id,
        "total": total,
        "account": account["email"],
    }

    results = []

    for i, email in enumerate(sendable):
        yield {
            "type": "sending",
            "index": email["index"],
            "to": email["to"],
            "subject": email["subject"],
            "current": i + 1,
            "total": total,
        }

        try:
            await asyncio.to_thread(
                send_one_email,
                account,
                email["to"],
                email["subject"],
                email["body"],
                from_name,
            )
            results.append({**email, "status": "sent"})
            yield {
                "type": "email_sent",
                "index": email["index"],
                "to": email["to"],
                "current": i + 1,
                "total": total,
            }
        except Exception as e:
            results.append({**email, "status": "failed", "error": str(e)})
            yield {
                "type": "email_failed",
                "index": email["index"],
                "to": email["to"],
                "error": str(e),
                "current": i + 1,
                "total": total,
            }

        # Delay between sends (skip after last)
        if i < total - 1:
            yield {
                "type": "waiting",
                "seconds": delay_seconds,
                "current": i + 1,
                "total": total,
            }
            await asyncio.sleep(delay_seconds)

    sent_count = sum(1 for r in results if r["status"] == "sent")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    save_batch_result(batch_id, account_label, results)

    yield {
        "type": "batch_complete",
        "batch_id": batch_id,
        "sent": sent_count,
        "failed": failed_count,
        "total": total,
    }


# ─── Persistence ──────────────────────────────────


def save_batch_result(batch_id: str, account_label: str, results: list[dict]) -> None:
    """Save batch results to output/outreach/."""
    OUTREACH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "id": batch_id,
        "account": account_label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "sent": sum(1 for r in results if r["status"] == "sent"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
    }
    path = OUTREACH_OUTPUT_DIR / f"{batch_id}.json"
    path.write_text(json.dumps(data, indent=2))


def list_batch_results() -> list[dict]:
    """List past batch results (newest first)."""
    if not OUTREACH_OUTPUT_DIR.exists():
        return []
    items = []
    for f in sorted(OUTREACH_OUTPUT_DIR.glob("outreach-*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            items.append({
                "id": data["id"],
                "account": data["account"],
                "created_at": data["created_at"],
                "sent": data["sent"],
                "failed": data["failed"],
                "total": data["sent"] + data["failed"],
            })
        except Exception:
            continue
    return items


def load_batch_result(batch_id: str) -> dict | None:
    """Load a specific batch result."""
    path = OUTREACH_OUTPUT_DIR / f"{batch_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None
