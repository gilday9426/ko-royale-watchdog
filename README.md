# ko-royale-watchdog

Independent daily check for the private [`ko-royale`](https://github.com/gilday9426/ko-royale)
repo's unattended pipeline (see that repo's `docs/daily_automation_plan.md` and
`docs/progress_log.md` Task 47+ for the full pipeline design).

## Why this exists

On 2026-08-27, a GitHub-side "Disruption with GitHub Billing" incident caused
`ko-royale`'s scheduled cron triggers to silently not fire for at least two of the day's
five retry slots. Because the trigger itself never fired, no workflow run was ever
created — which means none of `ko-royale`'s own alerting (sent from *inside* a run) had
any chance to fire either. With the owner unreachable (no laptop) for most of
2026-08-30 → 09-15, a silent "the scheduler itself never woke up" failure with zero alert
was the one failure mode that could go completely unnoticed for the whole trip.

## What it does

Once a day (19:41 UTC — after `ko-royale`'s own five retry slots), `check.py` asks
GitHub's API whether `daily_video.yml` had *any* run in the last 8 hours. If yes,
`ko-royale`'s own alerting is trusted to own whatever that run did — this stays silent.
If genuinely zero runs were attempted, it sends a Telegram alert with a direct link to
manually trigger the real pipeline from a browser (the same fallback already documented
for `ko-royale`).

This repo is deliberately public and separate from `ko-royale` so its own schedule isn't
subject to the same private-repo Actions billing/quota gate implicated in the 2026-08-27
incident.

## Secrets required (repo Settings → Secrets and variables → Actions)

- `WATCHDOG_GH_TOKEN` — a token with read access to `ko-royale`'s Actions runs.
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — same bot already used by `ko-royale`'s own
  alerting.

## No real data here

This repo contains no follower data, no video output, no application code from
`ko-royale` — just this check.
