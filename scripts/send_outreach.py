#!/usr/bin/env python3
"""CLI for mass outreach email sending.

Usage:
  python3 send_outreach.py emails.md                    # interactive account pick
  python3 send_outreach.py emails.md --account arkanav  # specify account
  python3 send_outreach.py emails.json --json           # JSON input
  python3 send_outreach.py emails.md --dry-run          # parse only
  python3 send_outreach.py emails.md --delay 60         # custom delay
  python3 send_outreach.py emails.md --from-name Pranav # From header name
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add backend to path so we can reuse the service
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard" / "backend"))

from services.email_sender import (
    parse_outreach_markdown,
    send_one_email,
    get_account,
    list_accounts,
    save_batch_result,
)
from config import OUTREACH_OUTPUT_DIR

import uuid
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails from markdown or JSON")
    parser.add_argument("file", help="Path to markdown (.md) or JSON (.json) file")
    parser.add_argument("--account", "-a", help="Sender account label")
    parser.add_argument("--json", dest="json_input", action="store_true", help="Input is JSON instead of markdown")
    parser.add_argument("--dry-run", action="store_true", help="Parse and preview only, don't send")
    parser.add_argument("--delay", type=int, default=45, help="Seconds between sends (default: 45)")
    parser.add_argument("--from-name", help="Display name for From header")
    args = parser.parse_args()

    # Read input file
    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    content = input_path.read_text()

    # Parse emails
    if args.json_input:
        try:
            emails = json.loads(content)
            if isinstance(emails, dict):
                emails = emails.get("emails", [])
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            sys.exit(1)
    else:
        emails = parse_outreach_markdown(content)

    if not emails:
        print("No emails found in input file.")
        sys.exit(1)

    # Show parsed emails
    sendable = [e for e in emails if not e.get("skip")]
    skipped = [e for e in emails if e.get("skip")]

    print(f"\nParsed {len(emails)} emails: {len(sendable)} sendable, {len(skipped)} skipped\n")

    for e in emails:
        status = "[SKIP]" if e.get("skip") else "[SEND]"
        reason = f" ({e.get('skip_reason', '')})" if e.get("skip") else ""
        print(f"  #{e['index']:2d} {status}{reason} {e['to']}")
        print(f"       Subject: {e['subject']}")
        print()

    if args.dry_run:
        print("Dry run complete.")
        return

    if not sendable:
        print("No sendable emails.")
        return

    # Pick account
    accounts = list_accounts()
    if not accounts:
        print("Error: No outreach accounts configured. Set OUTREACH_ACCOUNTS in .env")
        sys.exit(1)

    if args.account:
        account = get_account(args.account)
        if not account:
            print(f"Error: Unknown account '{args.account}'. Available: {', '.join(a['label'] for a in accounts)}")
            sys.exit(1)
    else:
        print("Available accounts:")
        for i, a in enumerate(accounts):
            print(f"  [{i + 1}] {a['label']} ({a['email']})")
        while True:
            try:
                choice = input(f"\nPick account [1-{len(accounts)}]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(accounts):
                    account = get_account(accounts[idx]["label"])
                    break
            except (ValueError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(0)

    # Confirm
    print(f"\nReady to send {len(sendable)} emails from {account['email']}")
    print(f"Delay: {args.delay}s between sends")
    if args.from_name:
        print(f"From name: {args.from_name}")
    confirm = input("\nProceed? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    # Send
    batch_id = f"outreach-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    results = []

    for i, email in enumerate(sendable):
        print(f"\n[{i + 1}/{len(sendable)}] Sending to {email['to']}...", end=" ", flush=True)
        try:
            send_one_email(
                account,
                email["to"],
                email["subject"],
                email["body"],
                args.from_name,
            )
            results.append({**email, "status": "sent"})
            print("SENT")
        except Exception as e:
            results.append({**email, "status": "failed", "error": str(e)})
            print(f"FAILED: {e}")

        if i < len(sendable) - 1:
            print(f"  Waiting {args.delay}s...", end=" ", flush=True)
            time.sleep(args.delay)
            print("ok")

    # Save results
    save_batch_result(batch_id, account["label"], results)

    sent = sum(1 for r in results if r["status"] == "sent")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\nBatch complete: {sent} sent, {failed} failed")
    print(f"Saved to: output/outreach/{batch_id}.json")


if __name__ == "__main__":
    main()
