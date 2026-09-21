#!/usr/bin/env python3
"""
Send email via Firebase Trigger Email extension.

Writes to Firestore 'mail' collection — the Trigger Email extension
picks it up and sends it using its configured SMTP provider.

Requires:
  - FIREBASE_SERVICE_ACCOUNT env var (base64-encoded service account JSON)
  - FIRESTORE_PROJECT env var (default: happy-hunter-systems)

Usage:
  python scripts/send_firestore_email.py \
    --to motsumitl@happyhunterdigital.com \
    --subject "Morning Briefing" \
    --html output/morning-brief-2026-09-22.html \
    --text output/morning-brief-2026-09-22.md
"""
import os
import sys
import json
import base64
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Send email via Firebase Trigger Email")
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--html", help="Path to HTML body file")
    parser.add_argument("--text", help="Path to plain text body file")
    parser.add_argument("--from", dest="from_addr", default=None, help="Sender address (optional)")
    args = parser.parse_args()

    # Load service account from env
    sa_b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not sa_b64:
        print("ERROR: FIREBASE_SERVICE_ACCOUNT env var not set", file=sys.stderr)
        print("Set it in GitHub Secrets as base64-encoded service account JSON:", file=sys.stderr)
        print("  cat service-account.json | base64 -w 0", file=sys.stderr)
        sys.exit(1)

    try:
        sa_json = json.loads(base64.b64decode(sa_b64))
    except Exception as e:
        print(f"ERROR: Failed to decode FIREBASE_SERVICE_ACCOUNT: {e}", file=sys.stderr)
        sys.exit(1)

    project_id = os.environ.get("FIRESTORE_PROJECT", sa_json.get("project_id", "happy-hunter-systems"))

    # Read body content
    html_body = Path(args.html).read_text(encoding="utf-8") if args.html and Path(args.html).exists() else None
    text_body = Path(args.text).read_text(encoding="utf-8") if args.text and Path(args.text).exists() else None

    if not html_body and not text_body:
        print("ERROR: No --html or --text file found", file=sys.stderr)
        sys.exit(1)

    # Initialize firebase-admin
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("ERROR: firebase-admin not installed. Run: pip install firebase-admin", file=sys.stderr)
        sys.exit(1)

    if not firebase_admin._apps:
        cred = credentials.Certificate(sa_json)
        firebase_admin.initialize_app(cred, {"projectId": project_id})

    db = firestore.client()

    # Build mail document
    message = {"subject": args.subject}
    if html_body:
        message["html"] = html_body
    if text_body:
        message["text"] = text_body

    mail_doc = {"to": [args.to], "message": message}
    if args.from_addr:
        mail_doc["from"] = args.from_addr

    # Write to 'mail' collection — Trigger Email extension picks it up
    db.collection("mail").add(mail_doc)

    print(f"OK: Queued email to {args.to} via Firestore 'mail' collection (project: {project_id})")

if __name__ == "__main__":
    main()
