"""Email a short alert when a critical GitHub workflow fails on main."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText


def main() -> int:
    name = os.getenv("WORKFLOW_NAME", "unknown")
    conclusion = os.getenv("WORKFLOW_CONCLUSION", "failure")
    url = os.getenv("WORKFLOW_URL", "")
    branch = os.getenv("WORKFLOW_BRANCH", "")
    sha = (os.getenv("WORKFLOW_SHA") or "")[:12]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    subject = f"SanMitra CI [URGENT] {name} {conclusion} - {now}"
    body = (
        f"SanMitra CI red alert ({now})\n"
        f"{'=' * 60}\n\n"
        f"Workflow:   {name}\n"
        f"Conclusion: {conclusion}\n"
        f"Branch:     {branch}\n"
        f"SHA:        {sha}\n"
        f"URL:        {url}\n\n"
        "This alert is event-driven (not the daily digest).\n"
        "Inspect the failed run before promoting / deploying.\n"
    )

    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USERNAME")
    pwd = os.getenv("SMTP_PASSWORD")
    to = os.getenv("ALERT_RECIPIENT_EMAIL")
    if not all([host, user, pwd, to]):
        print("[SMTP not configured - printing alert instead]\n")
        print(subject + "\n\n" + body)
        return 0

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_FROM_EMAIL") or user
    msg["To"] = to
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
    print(f"CI red alert sent to {to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
