"""Independent daily watchdog for the private `ko-royale` repo's automation.

Why this exists (2026-08-27): a GitHub-side "Disruption with GitHub Billing" incident
caused ko-royale's scheduled cron triggers to silently not fire for at least two retry
slots in one day. Because the trigger never fired, no workflow run was ever created --
which means none of ko-royale's own alerting (Telegram/email, sent from *inside* a run)
ever had a chance to fire either. The owner is unreachable (no laptop) for most of
2026-08-30 -> 09-15, so a silent "the scheduler itself never woke up" failure with zero
alert is the one failure mode that could go completely unnoticed for the whole trip.

This script runs from a SEPARATE PUBLIC repo specifically so its own schedule isn't
subject to the same private-repo Actions billing/quota gate implicated in that incident
(public repos get unlimited included Actions minutes, no billing check). It does exactly
one thing: check whether ko-royale's daily_video.yml had ANY run (scheduled or manual)
today. If it had at least one, ko-royale's own alerting is trusted to handle whatever
that run did (rolled a video, correctly no-op'd on no new followers, or failed with its
own alert) -- this script stays silent. Only "zero attempts at all" triggers an alert
here, so this can never nag on a normal day where nothing changed.
"""
import datetime as dt
import os
import sys
import urllib.request
import json

TARGET_REPO = "gilday9426/ko-royale"
WORKFLOW_FILE = "daily_video.yml"
# How far back "today" reaches, generously covering the whole 15:23-18:23 UTC retry
# window plus buffer -- this script itself is scheduled to run at 19:15 UTC, after all
# five real retry slots would have had a chance to fire.
LOOKBACK_HOURS = 8


def _github_api(path, token):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _telegram_alert(text, bot_token, chat_id):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def main():
    gh_token = os.environ["WATCHDOG_GH_TOKEN"]
    tg_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    tg_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=LOOKBACK_HOURS)

    data = _github_api(
        f"/repos/{TARGET_REPO}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=20",
        gh_token,
    )
    runs = data.get("workflow_runs", [])
    recent = [
        r for r in runs
        if dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= cutoff
    ]

    print(f"checked {len(runs)} recent runs; {len(recent)} within the last "
          f"{LOOKBACK_HOURS}h (cutoff {cutoff.isoformat()})")

    if recent:
        print("at least one run was attempted -- ko-royale's own alerting owns the "
              "rest. Nothing to do.")
        return

    message = (
        "⚠️ KO Royale watchdog: no automation run was attempted today at "
        f"all (checked the last {LOOKBACK_HOURS}h, found zero). This usually means "
        "GitHub's scheduler itself didn't fire -- not a pipeline failure, since a "
        "pipeline failure would have sent its own alert.\n\n"
        "Please manually trigger a run from a browser:\n"
        "https://github.com/gilday9426/ko-royale/actions/workflows/daily_video.yml "
        "-> \"Run workflow\" -> leave both fields blank -> Run workflow."
    )
    print("ALERT: sending Telegram notification")
    status = _telegram_alert(message, tg_bot_token, tg_chat_id)
    print(f"telegram send status: {status}")
    if status != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
